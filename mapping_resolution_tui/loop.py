"""
Main event loop and console entry point.

The loop is a blocking Redux-style dispatcher:

    read keypress -> normalise readline aliases -> build action -> reduce -> render

Input arrives as *semantic key tokens* (e.g. ``"a"``, ``"left"``, ``"tab"``,
``"esc"``, ``"ctrl+b"``). The live terminal reader (:func:`_terminal_keys`)
drives ``blessed`` — the project's declared terminal dependency — and translates
its keystrokes into these tokens; tests inject a token sequence directly through
the loop's ``keys`` seam. :func:`normalise_key` collapses readline-style aliases
onto the canonical TUI events (FR29) before an action is constructed. Tokens
that map to no action are ignored and leave both state and rendered output
unchanged (FR30).
"""

import sys
from typing import Callable, Iterable, Optional

import blessed

from mapping_resolution_tui.actions import (
    Action,
    ClearFilter,
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# Readline-style aliases normalised onto canonical BROWSING events before an
# action is built (spec 5.1). Tokens absent from this map pass through unchanged.
_READLINE_ALIASES = {
    "ctrl+b": "left",   # backward-char
    "ctrl+f": "right",  # forward-char
    "ctrl+i": "tab",    # complete -> collision metafilter toggle
    "ctrl+h": "backspace",
}

# blessed Keystroke.name values for the multi-byte escape sequences and named
# keys the BROWSING filter cares about, mapped to canonical semantic tokens.
_BLESSED_KEY_NAMES = {
    "KEY_LEFT": "left",
    "KEY_RIGHT": "right",
    "KEY_UP": "up",
    "KEY_DOWN": "down",
    "KEY_TAB": "tab",
    "KEY_ESCAPE": "esc",
    "KEY_BACKSPACE": "backspace",
    "KEY_ENTER": "enter",
}


def normalise_key(key: str) -> str:
    """Collapse a readline alias onto its canonical TUI key token (FR29)."""
    return _READLINE_ALIASES.get(key, key)


def key_to_action(key: str) -> Optional[Action]:
    """Map a normalised BROWSING key token to an action, or ``None`` for a no-op.

    ``None`` covers every key not handled by the Epic-2 filter foundation —
    including recognised-but-not-yet-wired keys such as Backspace — so the loop
    leaves state and output unchanged (FR30).
    """
    if key in ("tab", "!"):
        return ToggleCollisionOnly()
    if key == "left":
        return MoveCursorLeft()
    if key == "right":
        return MoveCursorRight()
    if key == "esc":
        return ClearFilter()
    if len(key) == 1 and key.isprintable():
        return InsertChar(key)
    return None


def run(
    config: AppConfig,
    mappings: list[Mapping],
    *,
    keys: Optional[Iterable[str]] = None,
    render: Optional[Callable[[list[str]], None]] = None,
) -> list[Mapping] | None:
    """Drive the blocking event loop until the quit key or end of input.

    ``keys`` supplies semantic key tokens (defaulting to the live ``blessed``
    terminal reader); ``render`` receives each rendered frame (defaulting to an
    inline in-place repaint). Both are injectable so the loop is exercisable
    without a real TTY.

    Returns the resolved mappings on a clean end-of-input exit, or ``None`` when
    the user quits with the configured quit key (cancellation).
    """
    if keys is None:
        keys = _terminal_keys()
    if render is None:
        render = _InlineRenderer()

    state = make_initial_state(config, mappings)
    render(render_lines(state))

    for raw_key in keys:
        key = normalise_key(raw_key)
        if key == QUIT_KEY:
            return None

        action = key_to_action(key)
        if action is None:
            # FR30: unsupported keys mutate nothing and trigger no redraw.
            continue

        state = reduce(state, action)
        render(render_lines(state))

    return state.mappings


class _InlineRenderer:
    """Repaint the frame in place within the terminal scroll buffer.

    Unlike a full-screen clear, this rewrites only the lines the previous frame
    occupied (no alternate screen, scrollback preserved): the cursor is moved
    back to the top of the prior frame, each line is cleared and rewritten, and
    any leftover lines from a taller previous frame are cleared below.
    """

    def __init__(self) -> None:
        self._term = blessed.Terminal()
        self._prev_line_count = 0

    def __call__(self, lines: list[str]) -> None:
        term = self._term
        if self._prev_line_count:
            sys.stdout.write(term.move_up * self._prev_line_count)
        body = (term.clear_eol + "\r\n").join(lines)
        sys.stdout.write("\r" + body + term.clear_eol + term.clear_eos + "\r\n")
        sys.stdout.flush()
        self._prev_line_count = len(lines)


def _terminal_keys() -> Iterable[str]:
    """Yield semantic key tokens from a live ``blessed`` terminal until EOF.

    ``blessed`` owns escape-sequence decoding; ``term.raw()`` delivers control
    chords (including ctrl+c as the quit key) as keystrokes rather than signals,
    and avoids the alternate screen buffer. Keystrokes that decode to no known
    token are swallowed so the caller treats them as no-ops.
    """
    term = blessed.Terminal()
    if not term.is_a_tty:  # nothing interactive to read from
        return

    with term.raw(), term.hidden_cursor():
        while True:
            key = term.inkey()
            if not key:  # timeout / empty read
                continue
            token = _blessed_to_token(key)
            if token is not None:
                yield token


def _blessed_to_token(key) -> Optional[str]:
    """Translate a blessed ``Keystroke`` into a semantic key token.

    Named escape sequences (arrows, Tab, Esc, Backspace, Enter) resolve via
    ``Keystroke.name``; control chords collapse to ``ctrl+<letter>`` tokens so
    readline aliases such as ctrl+b/ctrl+f/ctrl+h reach :func:`normalise_key`;
    remaining single printable characters pass through unchanged.
    """
    if key.name in _BLESSED_KEY_NAMES:
        return _BLESSED_KEY_NAMES[key.name]

    if len(key) == 1:
        code = ord(key)
        if code == 127:  # DEL -> backspace
            return "backspace"
        if 1 <= code <= 26:  # ctrl+a .. ctrl+z (e.g. \t -> ctrl+i, ^C -> ctrl+c)
            return f"ctrl+{chr(code + 96)}"
        if key.isprintable():
            return str(key)
    return None
