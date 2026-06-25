"""
Main event loop and console entry point.

The loop is a blocking Redux-style dispatcher:

    read keypress -> normalise readline aliases -> build action -> reduce -> render

Input arrives as *semantic key tokens* (e.g. ``"a"``, ``"left"``, ``"tab"``,
``"esc"``, ``"ctrl+b"``). The terminal reader (:func:`_terminal_keys`) decodes
raw bytes and escape sequences into these tokens; tests inject a token sequence
directly. :func:`normalise_key` collapses readline-style aliases onto the
canonical TUI events (FR29) before an action is constructed. Tokens that map to
no action are ignored and leave both state and rendered output unchanged (FR30).
"""

import sys
from typing import Callable, Iterable, Optional

from mapping_resolution_tui.actions import (
    Action,
    ClearFilter,
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# Key tokens that terminate the loop. ctrl+c is the interim quit key until the
# exit-confirmation flow (a later epic) takes over the cancellation contract.
QUIT_KEYS = frozenset({"ctrl+c"})

# Readline-style aliases normalised onto canonical BROWSING events before an
# action is built (spec 5.1). Tokens absent from this map pass through unchanged.
_READLINE_ALIASES = {
    "ctrl+b": "left",   # backward-char
    "ctrl+f": "right",  # forward-char
    "ctrl+i": "tab",    # complete -> collision metafilter toggle
    "ctrl+h": "backspace",
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
    """Drive the blocking event loop until a quit key or end of input.

    ``keys`` supplies semantic key tokens (defaulting to the live terminal
    reader); ``render`` receives each rendered frame (defaulting to stdout).
    Both are injectable so the loop is exercisable without a real TTY.

    Returns the resolved mappings on a clean end-of-input exit, or ``None`` when
    the user quits with a quit key (cancellation).
    """
    if keys is None:
        keys = _terminal_keys()
    if render is None:
        render = _default_render

    state = make_initial_state(config, mappings)
    render(render_lines(state))

    for raw_key in keys:
        key = normalise_key(raw_key)
        if key in QUIT_KEYS:
            return None

        action = key_to_action(key)
        if action is None:
            # FR30: unsupported keys mutate nothing and trigger no redraw.
            continue

        state = reduce(state, action)
        render(render_lines(state))

    return state.mappings


def _default_render(lines: list[str]) -> None:
    """Clear the screen and draw the frame in place."""
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.write("\n".join(lines))
    sys.stdout.flush()


def _terminal_keys() -> Iterable[str]:
    """Yield semantic key tokens from stdin in cbreak mode until EOF/ctrl+c.

    Decodes the escape sequences and control bytes used by the BROWSING filter:
    arrow keys, Tab, Esc, Backspace and ctrl-letter chords. Unknown sequences
    are swallowed so the caller treats them as no-ops.
    """
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "":  # EOF
                return
            token = _decode_key(ch)
            if token is not None:
                yield token
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


def _decode_key(ch: str) -> Optional[str]:
    """Translate the leading byte(s) of a keypress into a semantic token."""
    code = ord(ch)

    if ch == "\x1b":  # ESC: lone Esc or the start of a CSI escape sequence.
        nxt = sys.stdin.read(1)
        if nxt != "[":
            return "esc"
        seq = sys.stdin.read(1)
        return {"D": "left", "C": "right", "A": "up", "B": "down"}.get(seq)

    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\t":
        return "tab"
    if ch in ("\x7f", "\x08"):
        return "backspace"
    if code == 3:
        return "ctrl+c"
    if 1 <= code <= 26:  # ctrl+a .. ctrl+z
        return f"ctrl+{chr(code + 96)}"
    if ch.isprintable():
        return ch
    return None
