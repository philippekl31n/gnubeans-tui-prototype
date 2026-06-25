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
    ClearFilter,
    DeleteBackward,
    InsertCharacter,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.state import AppConfig, Mapping

# Readline-style control characters normalised in the input layer (FR29). App
# bindings take precedence over generic readline names where they overlap.
_CTRL_B = "\x02"  # backward-char        -> cursor left
_CTRL_F = "\x06"  # forward-char         -> cursor right
_CTRL_H = "\x08"  # backward-delete-char -> backspace
_TAB = "\t"       # complete / ctrl+i    -> collision-only toggle
_ESC = "\x1b"     # abort filter         -> clear filter
_DEL = "\x7f"     # DEL / ctrl+?         -> backspace

# Names reported by blessed for multi-byte escape sequences (arrows, named keys).
_CURSOR_LEFT_NAMES = frozenset({"KEY_LEFT"})
_CURSOR_RIGHT_NAMES = frozenset({"KEY_RIGHT"})
_BACKSPACE_NAMES = frozenset({"KEY_BACKSPACE"})
_CLEAR_NAMES = frozenset({"KEY_ESCAPE"})
_TOGGLE_NAMES = frozenset({"KEY_TAB"})


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
    if name in _BACKSPACE_NAMES:
        return DeleteBackward()
    if name in _CLEAR_NAMES:
        return ClearFilter()
    if name in _TOGGLE_NAMES:
        return ToggleCollisionOnly()

    # Single control characters and readline aliases (ctrl+b/f/h, Tab, Esc, DEL).
    if text == _CTRL_B:
        return MoveCursorLeft()
    if text == _CTRL_F:
        return MoveCursorRight()
    if text in (_CTRL_H, _DEL):
        return DeleteBackward()
    if text == _TAB:
        return ToggleCollisionOnly()
    if text == _ESC:
        return ClearFilter()

    # `!` toggles the metafilter in BROWSING and is never inserted literally.
    if text == "!":
        return ToggleCollisionOnly()

    # Any remaining single printable ASCII character inserts into the filter.
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
