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
import time
from contextlib import ExitStack
from typing import Callable, Iterable, Optional

import blessed

from mapping_resolution_tui.actions import (
    AcceptLine,
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
    MoveSelectionDown,
    MoveSelectionUp,
    PageDown,
    PageUp,
    Redraw,
    UnixLineDiscard,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, AppState, Mapping

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
    "KEY_ENTER": AcceptLine,
    "KEY_UP": MoveSelectionUp,
    "KEY_DOWN": MoveSelectionDown,
    "KEY_SUP": PageUp,
    "KEY_PGUP": PageUp,
    "KEY_SDOWN": PageDown,
    "KEY_PGDOWN": PageDown,
}

# `Tab` / `ctrl+i` autocompletes a leading `!` collision metafilter; the reducer
# no-ops unless the `Tab to view collisions` ghost is visible (spec §3.3 / §5.1).
_TAB_NAMES = frozenset({"KEY_TAB"})

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
    "\x10": PageUp,            # ctrl+p  previous-history -> PageUp
    "\x0e": PageDown,          # ctrl+n  next-history -> PageDown
    "\x0c": Redraw,            # ctrl+l  clear-screen / redraw only
    "\x0d": AcceptLine,        # ctrl+m / Enter  accept-line
    "\x0a": AcceptLine,        # ctrl+j          accept-line
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

    if name in _TAB_NAMES:
        return AutocompleteBang()

    if text in _META_ACTIONS:
        return _META_ACTIONS[text]()
    if text in _CTRL_ACTIONS:
        return _CTRL_ACTIONS[text]()

    if text == _TAB_TEXT:
        return AutocompleteBang()

    if len(text) == 1 and " " <= text <= "~":
        return InsertChar(text)

    return None


# Sentinel returned by a key source at end of input, distinct from a re-render
# tick (signalled by ``None``) and from any real keystroke.
_EOF = object()


def _flash_timeout(state: AppState, now: float) -> Optional[float]:
    """Seconds until the max-length flash burst deadline, or ``None`` to block.

    While a burst is pending (``now < edit.max_length_flash_until``) the input
    read MUST wake at the deadline so the burst-to-held transition is visible
    without a keypress (spec §7.6 / §12.1). Once no burst is pending — no edit,
    no armed deadline, or the deadline already passed — this returns ``None`` so
    the read blocks and never polls.
    """
    edit = state.edit
    if edit is None or edit.max_length_flash_until is None:
        return None
    remaining = edit.max_length_flash_until - now
    return remaining if remaining > 0 else None


def run(
    config: AppConfig,
    mappings: list[Mapping],
    *,
    keys: Optional[Iterable] = None,
    read_key: Optional[Callable[[Optional[float]], object]] = None,
    render: Optional[Callable[[list[str]], None]] = None,
    clock: Callable[[], float] = time.time,
) -> list[Mapping] | None:
    """Drive the event loop until the quit key or end of input.

    The read is a plain blocking read except while a max-length flash burst is in
    flight, when it uses a bounded timeout and treats a timed-out read as a
    synthetic re-render tick (spec §7.6 / §12.1). ``render`` receives each frame
    (defaulting to an inline in-place repaint). Input is injectable two ways:
    ``read_key(timeout)`` (a callable returning a key, ``None`` for a tick, or
    :data:`_EOF`) or ``keys`` (a plain iterable of keystrokes, exhausted = EOF);
    both default to the live ``blessed`` terminal reader. ``clock`` injects the
    wall-clock used for the burst window.

    Returns the resolved mappings on a clean end-of-input exit, or ``None`` when
    the user quits with the configured quit key (cancellation).
    """
    if render is None:
        render = _InlineRenderer()

    state = make_initial_state(config, mappings)

    if read_key is not None:
        return _event_loop(state, read_key, render, clock)
    if keys is not None:
        return _event_loop(state, _iterable_reader(keys), render, clock)

    source = _TerminalKeySource()
    with source:
        return _event_loop(state, source.read, render, clock)


def _event_loop(
    state: AppState,
    read_key: Callable[[Optional[float]], object],
    render: Callable[[list[str]], None],
    clock: Callable[[], float],
) -> list[Mapping] | None:
    render(render_lines(state, now=clock()))

    while True:
        event = read_key(_flash_timeout(state, clock()))

        if event is _EOF:
            break
        if event is None:
            # A tick: the burst deadline was reached with no keypress. Re-render
            # the current state so the burst-to-held transition is visible; the
            # deadline is a render-time marker, so no reduce happens (spec §7.6).
            render(render_lines(state, now=clock()))
            continue

        if is_quit_key(event):
            return None

        action = key_to_action(event)
        if action is None:
            # FR30: unsupported keys mutate nothing and trigger no redraw.
            continue

        if isinstance(action, Redraw):
            # ctrl+l re-renders the current state without mutating it; this is
            # the one repaint that is never skipped by the no-op check below.
            render(render_lines(state, now=clock()))
            continue

        new_state = reduce(state, action, now=clock())
        if new_state is state:
            # A recognised action that changed nothing (the reducer returned the
            # same object) needs no repaint — state and output stay unchanged.
            continue
        state = new_state
        render(render_lines(state, now=clock()))

    return state.mappings


def _iterable_reader(keys: Iterable) -> Callable[[Optional[float]], object]:
    """Adapt a plain keystroke iterable to the ``read_key(timeout)`` seam.

    The timeout is ignored (a scripted iterable never blocks); a ``None`` item
    models a re-render tick and exhaustion returns :data:`_EOF`.
    """
    iterator = iter(keys)

    def read(timeout: Optional[float]) -> object:
        try:
            return next(iterator)
        except StopIteration:
            return _EOF

    return read


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


class _TerminalKeySource:
    """Live ``blessed`` key source with a bounded-timeout read (spec §12.1).

    ``blessed`` owns escape-sequence decoding; ``term.raw()`` delivers control
    chords (including ctrl+c as the quit key) as keystrokes rather than signals,
    and avoids the alternate screen buffer. :meth:`read` performs a plain
    blocking read when ``timeout is None`` (no burst pending — it never polls)
    and a bounded read otherwise, returning ``None`` on a timed-out read so the
    loop can re-render the burst-to-held transition without a keypress.
    """

    def __init__(self) -> None:
        self._term = blessed.Terminal()
        self._stack: Optional[ExitStack] = None

    def __enter__(self) -> "_TerminalKeySource":
        if self._term.is_a_tty:
            self._stack = ExitStack()
            self._stack.enter_context(self._term.raw())
            self._stack.enter_context(self._term.hidden_cursor())
        return self

    def __exit__(self, *exc) -> None:
        if self._stack is not None:
            self._stack.close()
            self._stack = None

    def read(self, timeout: Optional[float]) -> object:
        if not self._term.is_a_tty:  # nothing interactive to read from
            return _EOF
        key = self._term.inkey(timeout=timeout)
        if key:
            return key
        if timeout is None:
            # A spurious empty blocking read: keep waiting for a real key, matching
            # the prior generator's behavior (no burst is pending, so no tick).
            while True:
                key = self._term.inkey()
                if key:
                    return key
        return None  # bounded read timed out -> a re-render tick
