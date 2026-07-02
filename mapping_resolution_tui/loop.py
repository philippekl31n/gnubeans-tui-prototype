"""
Main event loop and console entry point.

The loop is a blocking Redux-style dispatcher:

    read keypress -> key_to_event -> reduce -> render

Input is a ``blessed.Keystroke`` (or, in tests, any string / string-like object
carrying an optional ``.name``). A single, table-driven :func:`key_to_event`
normalises every keypress — named escape sequences via ``Keystroke.name`` and
readline-style control chords / meta sequences via the raw key text — into a
mode-neutral :class:`~mapping_resolution_tui.events.KeyEvent` or a bare ``str``
for a printable character. Keys that map to no event are ignored and leave state
and rendered output unchanged (FR30). The ``keys`` and ``render`` seams on
:func:`run` keep the loop drivable headless.
"""

import os
import signal
import sys
from typing import Callable, Iterable, Optional

import blessed

from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.events import InputEvent, KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# blessed Keystroke.name → KeyEvent (multi-byte named escape sequences).
_NAME_EVENTS: dict[str, KeyEvent] = {
    "KEY_LEFT":      KeyEvent.CURSOR_LEFT,
    "KEY_RIGHT":     KeyEvent.CURSOR_RIGHT,
    "KEY_HOME":      KeyEvent.CURSOR_HOME,
    "KEY_END":       KeyEvent.CURSOR_END,
    "KEY_BACKSPACE": KeyEvent.BACKSPACE,
    "KEY_DELETE":    KeyEvent.DELETE_CHAR,
    "KEY_ESCAPE":    KeyEvent.ESCAPE,
    "KEY_ENTER":     KeyEvent.ENTER,
    "KEY_UP":        KeyEvent.SELECTION_UP,
    "KEY_DOWN":      KeyEvent.SELECTION_DOWN,
    "KEY_TAB":       KeyEvent.TAB,
    "KEY_SUP":       KeyEvent.PAGE_UP,
    "KEY_PGUP":      KeyEvent.PAGE_UP,
    "KEY_SDOWN":     KeyEvent.PAGE_DOWN,
    "KEY_PGDOWN":    KeyEvent.PAGE_DOWN,
}

# ESC-prefixed meta sequences → KeyEvent (checked before the lone ESC below).
_META_EVENTS: dict[str, KeyEvent] = {
    "\x1bd":    KeyEvent.KILL_WORD,          # meta+d         -> kill-word (forward)
    "\x1b\x7f": KeyEvent.BACKWARD_KILL_WORD, # meta+backspace -> backward-kill-word
    "\x1b\x08": KeyEvent.BACKWARD_KILL_WORD, # meta+ctrl+h variant
}

# Single control characters / readline aliases → KeyEvent.
_CTRL_EVENTS: dict[str, KeyEvent] = {
    "\x03": KeyEvent.QUIT,               # ctrl+c  raw byte under term.raw()
    "\x01": KeyEvent.CURSOR_HOME,        # ctrl+a  beginning-of-line
    "\x05": KeyEvent.CURSOR_END,         # ctrl+e  end-of-line
    "\x02": KeyEvent.CURSOR_LEFT,        # ctrl+b  backward-char
    "\x06": KeyEvent.CURSOR_RIGHT,       # ctrl+f  forward-char
    "\x04": KeyEvent.DELETE_CHAR,        # ctrl+d  delete-char (forward)
    "\x08": KeyEvent.BACKSPACE,          # ctrl+h  backward-delete-char
    "\x7f": KeyEvent.BACKSPACE,          # DEL     backward-delete-char
    "\x09": KeyEvent.TAB,                # ctrl+i  Tab / autocomplete
    "\x13": KeyEvent.SUBMIT,             # ctrl+s  open accept confirmation (may
                                         #         be swallowed by terminal XOFF
                                         #         flow control on a live TTY)
    "\x0b": KeyEvent.KILL_LINE,          # ctrl+k  kill-line
    "\x15": KeyEvent.UNIX_LINE_DISCARD,  # ctrl+u  unix-line-discard
    "\x17": KeyEvent.BACKWARD_KILL_WORD, # ctrl+w  unix-word-rubout
    "\x10": KeyEvent.PAGE_UP,            # ctrl+p  previous-history -> PageUp
    "\x0e": KeyEvent.PAGE_DOWN,          # ctrl+n  next-history -> PageDown
    "\x0c": KeyEvent.REDRAW,             # ctrl+l  clear-screen / redraw only
    "\x1b": KeyEvent.ESCAPE,             # ESC     clear filter / cancel edit
    "\r":   KeyEvent.ENTER,              # enter
    "\n":   KeyEvent.ENTER,              # enter
}


def key_to_event(key) -> Optional[InputEvent]:
    """Normalise a keypress into an :data:`~mapping_resolution_tui.events.InputEvent`, or ``None`` for a no-op (FR30).

    ``key`` may be a ``blessed.Keystroke`` (whose ``.name`` identifies multi-byte
    escape sequences such as the arrow keys) or any string-like value, so the one
    function serves both the live loop and headless tests. Named keys resolve via
    ``.name``; control chords and meta sequences via the raw key text; a single
    printable character — including a literal ``!`` (spec §3.3) — is returned as
    a bare ``str``. ctrl+c is :data:`KeyEvent.QUIT` like any other chord — the
    reducer's mode tables decide what it means (spec §4.2 has a ctrl+c row per
    mode) — accepted both as the raw control byte a live blessed keystroke
    delivers under ``term.raw()`` and as the readable ``QUIT_KEY`` token headless
    drivers pass. The no-op readline families and anything unrecognised return
    ``None``.
    """
    name = getattr(key, "name", None)
    text = str(key)

    if name in _NAME_EVENTS:
        return _NAME_EVENTS[name]

    if text in _META_EVENTS:
        return _META_EVENTS[text]
    if text in _CTRL_EVENTS:
        return _CTRL_EVENTS[text]
    if text == QUIT_KEY:
        return KeyEvent.QUIT

    if len(text) == 1 and " " <= text <= "~":
        return text

    return None


def run(
    config: AppConfig,
    mappings: list[Mapping],
    *,
    keys: Optional[Iterable] = None,
    render: Optional[Callable[[list[str]], None]] = None,
) -> list[Mapping] | None:
    """Drive the blocking event loop until the run ends or input is exhausted.

    ``keys`` supplies keystrokes (defaulting to the live ``blessed`` terminal
    reader); ``render`` receives each rendered frame (defaulting to an inline
    in-place repaint). Both are injectable so the loop is exercisable without a
    real TTY.

    The loop itself is mode-blind: every key goes through :func:`key_to_event`
    and the reducer's mode tables, and the run is over when the reducer marks
    ``result.status`` terminal: accept confirmation + YES → ACCEPTED (paint the
    §6.7 result frame, return the resolved mappings); exit confirmation + YES →
    SKIPPED (a clean skip that adds no commodities — no result frame, return
    ``None``); the second ctrl+c in the exit confirmation → SIGINT (re-raise the
    interrupt to force-exit). Returns the resolved mappings on a clean
    end-of-input exit or an ACCEPTED accept confirmation, or ``None`` when the
    reviewer skipped adding commodities.
    """
    if keys is None:
        keys = _terminal_keys()
    if render is None:
        render = _InlineRenderer()

    state = make_initial_state(config, mappings)
    render(render_lines(state))

    for key in keys:
        event = key_to_event(key)
        if event is None:
            # FR30: unsupported keys mutate nothing and trigger no redraw.
            continue

        if event is KeyEvent.REDRAW:
            # ctrl+l re-renders the current state without mutating it; this is
            # the one repaint that is never skipped by the no-op check below.
            render(render_lines(state))
            continue

        new_state = reduce(state, event)
        status = new_state.result.status
        if status == "ACCEPTED":
            # Accept confirmation with choice=YES committed every mapping: paint
            # the §6.7 terminal result frame, then exit returning the resolved
            # mappings (the corrected commodity import).
            render(render_lines(new_state))
            return new_state.mappings
        if status == "SIGINT":
            # The second ctrl+c in the exit confirmation force-exits: re-raise
            # the interrupt so the process terminates on the conventional 130
            # exit code (spec §4.2/§6.7), bypassing the y/N choice entirely. No
            # terminal frame is painted.
            os.kill(os.getpid(), signal.SIGINT)
            return None
        if status != "RUNNING":
            # SKIPPED: the reviewer confirmed the exit prompt on YES, a clean
            # skip that adds no commodities. The run ends with no mappings and
            # no §6.7 result frame (spec §6.7).
            return None

        if new_state is state:
            # A recognised event that changed nothing (the reducer returned the
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
    :func:`key_to_event`, which performs all normalisation.
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
