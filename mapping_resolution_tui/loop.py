"""
Main event loop and console entry point.

The loop is the sole owner of side effects: it blocks on terminal input,
normalises each keypress (including readline-style aliases) into a typed action,
dispatches it through the reducer, re-derives the renderable frame via selectors,
and repaints the inline frame. Unsupported keys are ignored so that root state
and rendered output stay unchanged (FR30).
"""

import sys

import blessed

from mapping_resolution_tui.actions import (
    Action,
    AutocompleteBang,
    ClearFilter,
    DeleteBackward,
    DeleteForward,
    DeleteWordBackward,
    DeleteWordForward,
    InsertCharacter,
    KillToEnd,
    KillToStart,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    MoveSelectionDown,
    MoveSelectionUp,
    PageDown,
    PageUp,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# Readline-style control characters normalised in the input layer (FR29). App
# bindings take precedence over generic readline names where they overlap. The
# filter is one editable buffer (filter.raw); all of these edit it or move the
# caret within it (spec §5.1).
_CTRL_A = "\x01"  # beginning-of-line    -> cursor home
_CTRL_B = "\x02"  # backward-char        -> cursor left
_CTRL_D = "\x04"  # delete-char          -> forward delete
_CTRL_E = "\x05"  # end-of-line          -> cursor end
_CTRL_F = "\x06"  # forward-char         -> cursor right
_CTRL_H = "\x08"  # backward-delete-char -> backspace
_CTRL_K = "\x0b"  # kill-line            -> delete to end of line
_CTRL_N = "\x0e"  # next-history         -> move selection down
_CTRL_P = "\x10"  # previous-history     -> move selection up
_CTRL_U = "\x15"  # unix-line-discard    -> delete to start of line
_CTRL_W = "\x17"  # unix-word-rubout     -> delete word backward
_TAB = "\t"       # complete / ctrl+i    -> bang autocomplete (\x09)
_ESC = "\x1b"     # abort filter         -> clear filter
_DEL = "\x7f"     # DEL / ctrl+?         -> backspace
# Meta/Alt word operations arrive as an ESC prefix; matched before the lone ESC.
_META_D = "\x1bd"      # kill-word          -> delete word forward
_META_BS = "\x1b\x7f"  # backward-kill-word -> delete word backward
_META_BS_ALT = "\x1b\x08"

# Names reported by blessed for multi-byte escape sequences (arrows, named keys).
_CURSOR_LEFT_NAMES = frozenset({"KEY_LEFT"})
_CURSOR_RIGHT_NAMES = frozenset({"KEY_RIGHT"})
_HOME_NAMES = frozenset({"KEY_HOME"})
_END_NAMES = frozenset({"KEY_END"})
_BACKSPACE_NAMES = frozenset({"KEY_BACKSPACE"})
_DELETE_NAMES = frozenset({"KEY_DELETE"})
_CLEAR_NAMES = frozenset({"KEY_ESCAPE"})
# `Tab` / `ctrl+i` autocompletes a leading `!` collision metafilter; the reducer
# no-ops unless the `Tab to view collisions` ghost is visible (spec §3.3 / §5.1).
_TAB_NAMES = frozenset({"KEY_TAB"})
# Browsing navigation. Plain arrows move one row; the page keys move one body
# capacity. `Shift+↑/↓` (`KEY_SUP`/`KEY_SDOWN`) page like `PgUp`/`PgDn`, but when
# the terminal cannot distinguish a shifted arrow it reports a plain `KEY_UP`/
# `KEY_DOWN` and still moves exactly one row; `PgUp`/`PgDn` remain the reliable
# page-movement keys (spec §5 / §5.1 / §8.3 / §8.5).
_SELECT_UP_NAMES = frozenset({"KEY_UP"})
_SELECT_DOWN_NAMES = frozenset({"KEY_DOWN"})
_PAGE_UP_NAMES = frozenset({"KEY_PGUP", "KEY_SUP"})
_PAGE_DOWN_NAMES = frozenset({"KEY_PGDOWN", "KEY_SDOWN"})


def is_quit_key(key) -> bool:
    """Return True when ``key`` is the configured quit key."""
    return str(key) == QUIT_KEY


def key_to_action(key) -> Action | None:
    """Normalise a keypress into a typed action, or ``None`` when unsupported.

    Accepts either a blessed ``Keystroke`` (whose ``.name`` identifies multi-byte
    escape sequences such as the arrow keys) or a plain string, so the same
    normalisation serves both the live loop and headless tests. Unsupported keys
    and unrecognised control sequences return ``None`` (FR30).
    """
    name = getattr(key, "name", None)
    text = str(key)

    # Multi-byte escape sequences resolved by blessed (arrows, named keys).
    if name in _CURSOR_LEFT_NAMES:
        return MoveCursorLeft()
    if name in _CURSOR_RIGHT_NAMES:
        return MoveCursorRight()
    if name in _HOME_NAMES:
        return MoveCursorHome()
    if name in _END_NAMES:
        return MoveCursorEnd()
    if name in _BACKSPACE_NAMES:
        return DeleteBackward()
    if name in _DELETE_NAMES:
        return DeleteForward()
    if name in _CLEAR_NAMES:
        return ClearFilter()
    if name in _TAB_NAMES:
        return AutocompleteBang()
    if name in _SELECT_UP_NAMES:
        return MoveSelectionUp()
    if name in _SELECT_DOWN_NAMES:
        return MoveSelectionDown()
    if name in _PAGE_UP_NAMES:
        return PageUp()
    if name in _PAGE_DOWN_NAMES:
        return PageDown()

    # Meta/Alt word operations (ESC-prefixed); checked before the lone ESC below.
    if text == _META_D:
        return DeleteWordForward()
    if text in (_META_BS, _META_BS_ALT):
        return DeleteWordBackward()

    # Single control characters and readline aliases.
    if text == _CTRL_A:
        return MoveCursorHome()
    if text == _CTRL_E:
        return MoveCursorEnd()
    if text == _CTRL_B:
        return MoveCursorLeft()
    if text == _CTRL_F:
        return MoveCursorRight()
    if text in (_CTRL_H, _DEL):
        return DeleteBackward()
    if text == _CTRL_D:
        return DeleteForward()
    if text == _CTRL_K:
        return KillToEnd()
    if text == _CTRL_P:
        return MoveSelectionUp()
    if text == _CTRL_N:
        return MoveSelectionDown()
    if text == _CTRL_U:
        return KillToStart()
    if text == _CTRL_W:
        return DeleteWordBackward()
    if text == _TAB:
        return AutocompleteBang()
    if text == _ESC:
        return ClearFilter()

    # Any single printable ASCII character — including a literal `!`, which is
    # ordinary filter text (spec §3.3) — inserts into filter.raw at the cursor.
    if len(text) == 1 and " " <= text <= "~":
        return InsertCharacter(text)

    return None


def _draw(term: blessed.Terminal, lines: list[str], prev_line_count: int) -> int:
    """Repaint the inline frame in place and return the number of lines drawn.

    The frame is rendered into the terminal scroll buffer (no alternate screen):
    the cursor is moved back to the top of the previous frame, each line is
    cleared and rewritten, and any leftover lines from a taller previous frame
    are cleared.
    """
    if prev_line_count:
        sys.stdout.write(term.move_up * prev_line_count)
    rendered = (term.clear_eol + "\r\n").join(lines)
    sys.stdout.write("\r" + rendered + term.clear_eol + term.clear_eos + "\r\n")
    sys.stdout.flush()
    return len(lines)


def run(
    config: AppConfig,
    mappings: list[Mapping],
) -> list[Mapping] | None:
    # Initialize the core application state.
    state = make_initial_state(config, mappings)
    term = blessed.Terminal()

    # Without an interactive terminal there is nothing to read; render the
    # initial inline frame once and return, preserving non-tty demo behaviour.
    if not sys.stdin.isatty():
        print("\n".join(render_lines(state)))
        return state.mappings

    # raw() lets the loop receive ctrl+c as a key (the configured quit key)
    # instead of a SIGINT, and avoids the alternate screen buffer entirely.
    with term.raw(), term.hidden_cursor():
        prev_line_count = _draw(term, render_lines(state), 0)
        while True:
            key = term.inkey()
            if not key:
                continue
            if is_quit_key(key):
                break
            action = key_to_action(key)
            if action is None:
                continue  # FR30: unsupported key — state and output unchanged.
            new_state = reduce(state, action)
            if new_state is state:
                continue  # No-op transition — nothing to repaint.
            state = new_state
            prev_line_count = _draw(term, render_lines(state), prev_line_count)

    return state.mappings
