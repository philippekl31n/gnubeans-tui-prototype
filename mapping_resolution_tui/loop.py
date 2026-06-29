"""
Main event loop and console entry point.

The loop is a blocking Redux-style dispatcher:

    read keypress -> key_to_action -> reduce -> render

Input is a ``blessed.Keystroke`` (or, in tests, any string / string-like object
carrying an optional ``.name``). A single, table-driven :func:`key_to_action`
normalises every keypress — named escape sequences via ``Keystroke.name`` and
readline-style control chords / meta sequences via the raw key text — directly
into an action, with no intermediate token vocabulary. Keys that map to no
action are ignored and leave state and rendered output unchanged (FR30). The
``keys`` and ``render`` seams on :func:`run` keep the loop drivable headless.
"""

import sys
from typing import Callable, Iterable, Optional

import blessed

from mapping_resolution_tui.actions import (
    Action,
    AutocompleteBang,
    Backspace,
    BackwardKillWord,
    ClearFilter,
    DeleteChar,
    InsertChar,
    KillLine,
    KillWord,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    Redraw,
    UnixLineDiscard,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# Raw ctrl+c byte. The configured QUIT_KEY is the readable token "ctrl+c"; a live
# blessed keystroke delivers it as this control byte under term.raw().
_CTRL_C = "\x03"

# blessed Keystroke.name → action (multi-byte named escape sequences). Tab
# (KEY_TAB) is handled separately below: it maps to AutocompleteBang, whose
# ghost-visibility gate is enforced by the reducer against application state.
_NAME_ACTIONS: dict[str, type] = {
    "KEY_LEFT": MoveCursorLeft,
    "KEY_RIGHT": MoveCursorRight,
    "KEY_HOME": MoveCursorHome,
    "KEY_END": MoveCursorEnd,
    "KEY_BACKSPACE": Backspace,
    "KEY_DELETE": DeleteChar,
    "KEY_ESCAPE": ClearFilter,
}

# ESC-prefixed meta sequences → action (checked before the lone ESC below).
_META_ACTIONS: dict[str, type] = {
    "\x1bd": KillWord,        # meta+d         -> kill-word (forward)
    "\x1b\x7f": BackwardKillWord,  # meta+backspace -> backward-kill-word
    "\x1b\x08": BackwardKillWord,  # meta+ctrl+h variant
}

# Single control characters / readline aliases → action.
_CTRL_ACTIONS: dict[str, type] = {
    "\x01": MoveCursorHome,    # ctrl+a  beginning-of-line
    "\x05": MoveCursorEnd,     # ctrl+e  end-of-line
    "\x02": MoveCursorLeft,    # ctrl+b  backward-char
    "\x06": MoveCursorRight,   # ctrl+f  forward-char
    "\x04": DeleteChar,        # ctrl+d  delete-char (forward)
    "\x08": Backspace,         # ctrl+h  backward-delete-char
    "\x7f": Backspace,         # DEL     backward-delete-char
    "\x0b": KillLine,          # ctrl+k  kill-line
    "\x15": UnixLineDiscard,   # ctrl+u  unix-line-discard
    "\x17": BackwardKillWord,  # ctrl+w  unix-word-rubout
    "\x0c": Redraw,            # ctrl+l  clear-screen / redraw only
    "\x1b": ClearFilter,       # ESC     clear filter
}

# Tab / ctrl+i: bang-autocomplete the collision metafilter (the reducer decides
# whether the ghost is visible; otherwise the action is a no-op). ctrl+i arrives
# as the same "\t" byte.
_TAB_TEXT = "\t"


def is_quit_key(key) -> bool:
    """Return True when ``key`` is the configured quit key.

    Accepts the live ctrl+c control byte as well as the readable ``"ctrl+c"``
    token, so both the terminal reader and headless tests can signal a quit.
    """
    text = str(key)
    return text == _CTRL_C or text == QUIT_KEY


def key_to_action(key) -> Optional[Action]:
    """Normalise a keypress into an action, or ``None`` for a no-op (FR30).

    ``key`` may be a ``blessed.Keystroke`` (whose ``.name`` identifies multi-byte
    escape sequences such as the arrow keys) or any string-like value, so the one
    function serves both the live loop and headless tests. Named keys resolve via
    ``.name``; control chords and meta sequences via the raw key text; a single
    printable character — including a literal ``!`` (spec §3.3) — inserts. Tab /
    ctrl+i maps to :class:`AutocompleteBang` (the reducer applies the ghost gate).
    The quit key, the no-op readline families, and anything unrecognised return
    ``None``.
    """
    name = getattr(key, "name", None)
    text = str(key)

    if name in _NAME_ACTIONS:
        return _NAME_ACTIONS[name]()

    # Tab / ctrl+i: autocomplete the leading ! (gated in the reducer, §3.3).
    if name == "KEY_TAB" or text == _TAB_TEXT:
        return AutocompleteBang()

    if text in _META_ACTIONS:
        return _META_ACTIONS[text]()
    if text in _CTRL_ACTIONS:
        return _CTRL_ACTIONS[text]()

    if len(text) == 1 and " " <= text <= "~":
        return InsertChar(text)

    return None


def run(
    config: AppConfig,
    mappings: list[Mapping],
    *,
    keys: Optional[Iterable] = None,
    render: Optional[Callable[[list[str]], None]] = None,
) -> list[Mapping] | None:
    """Drive the blocking event loop until the quit key or end of input.

    ``keys`` supplies keystrokes (defaulting to the live ``blessed`` terminal
    reader); ``render`` receives each rendered frame (defaulting to an inline
    in-place repaint). Both are injectable so the loop is exercisable without a
    real TTY.

    Returns the resolved mappings on a clean end-of-input exit, or ``None`` when
    the user quits with the configured quit key (cancellation).
    """
    if keys is None:
        keys = _terminal_keys()
    if render is None:
        render = _InlineRenderer()

    state = make_initial_state(config, mappings)
    render(render_lines(state))

    for key in keys:
        if is_quit_key(key):
            return None

        action = key_to_action(key)
        if action is None:
            # FR30: unsupported keys mutate nothing and trigger no redraw.
            continue

        if isinstance(action, Redraw):
            # ctrl+l re-renders the current state without mutating it; this is
            # the one repaint that is never skipped by the no-op check below.
            render(render_lines(state))
            continue

        new_state = reduce(state, action)
        if new_state is state:
            # A recognised action that changed nothing (the reducer returned the
            # same object) needs no repaint — state and output stay unchanged.
            continue
        state = new_state
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


def _terminal_keys() -> Iterable:
    """Yield live ``blessed`` keystrokes until EOF.

    ``blessed`` owns escape-sequence decoding; ``term.raw()`` delivers control
    chords (including ctrl+c as the quit key) as keystrokes rather than signals,
    and avoids the alternate screen buffer. Each keystroke is yielded straight to
    :func:`key_to_action`, which performs all normalisation.
    """
    term = blessed.Terminal()
    if not term.is_a_tty:  # nothing interactive to read from
        return

    with term.raw(), term.hidden_cursor():
        while True:
            key = term.inkey()
            if not key:  # timeout / empty read
                continue
            yield key
