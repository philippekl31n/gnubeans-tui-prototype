"""
Unit tests for the BROWSING-mode action dispatch reducer (TASK-001).

Exercises the four filter operations — character insertion, cursor movement,
collision-only toggle, and filter clear — plus immutability, raw sync, and
selection clamping. Uses the canonical 11-row storyboard dataset so the
ordinal/collision shape matches the golden frames:

    1 APPLE   2 AT-T(!)  3 AT-T(!)  4 C100-F  5 GOOGL  6 MSFT
    7 NVDA    8 QQQ      9 SPY      10 VTSAX  11 VWUSX
"""

import pytest

from mapping_resolution_tui.actions import (
    ClearFilter,
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_visible_rows
from tests.fixtures.storyboard import make_config, make_mappings


@pytest.fixture
def state():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def visible_ordinals(s):
    return [m.ordinal for m in select_visible_rows(s)]


# ── immutability ─────────────────────────────────────────────────────────────

def test_reduce_returns_new_state_without_mutating_input(state):
    before = state.filter
    after = reduce(state, InsertChar("a"))

    assert after is not state
    assert after.filter is not state.filter
    assert state.filter is before
    assert state.filter.text == ""  # original untouched


def test_unknown_action_is_a_noop(state):
    sentinel = object()
    assert reduce(state, sentinel) is state


# ── character insertion ──────────────────────────────────────────────────────

def test_insert_char_appends_and_advances_cursor(state):
    s = reduce(state, InsertChar("a"))
    assert s.filter.text == "a"
    assert s.filter.cursor == 1


def test_insert_char_inserts_at_cursor_position(state):
    s = state
    for ch in "ac":
        s = reduce(s, InsertChar(ch))
    s = reduce(s, MoveCursorLeft())  # cursor now between 'a' and 'c'
    s = reduce(s, InsertChar("b"))
    assert s.filter.text == "abc"
    assert s.filter.cursor == 2


def test_insert_char_keeps_raw_in_sync(state):
    s = reduce(state, ToggleCollisionOnly())
    s = reduce(s, InsertChar("3"))
    assert s.filter.raw == "!3"


# ── cursor movement ──────────────────────────────────────────────────────────

def test_move_cursor_left_clamps_at_zero(state):
    s = reduce(state, MoveCursorLeft())
    assert s.filter.cursor == 0


def test_move_cursor_right_clamps_at_text_length(state):
    s = reduce(state, InsertChar("x"))
    s = reduce(s, MoveCursorRight())
    s = reduce(s, MoveCursorRight())
    assert s.filter.cursor == 1


def test_cursor_movement_leaves_text_unchanged(state):
    s = reduce(state, InsertChar("a"))
    s = reduce(s, MoveCursorLeft())
    assert s.filter.text == "a"


# ── collision-only toggle ────────────────────────────────────────────────────

def test_toggle_collision_only_flips_and_syncs_raw(state):
    s = reduce(state, ToggleCollisionOnly())
    assert s.filter.collision_only is True
    assert s.filter.raw == "!"
    s2 = reduce(s, ToggleCollisionOnly())
    assert s2.filter.collision_only is False
    assert s2.filter.raw == ""


def test_toggle_collision_only_does_not_insert_text(state):
    s = reduce(state, ToggleCollisionOnly())
    assert s.filter.text == ""
    assert s.filter.cursor == 0


def test_collision_only_limits_visible_rows_to_collision_group(state):
    s = reduce(state, ToggleCollisionOnly())
    assert visible_ordinals(s) == [2, 3]


# ── filter clear ─────────────────────────────────────────────────────────────

def test_clear_filter_resets_text_metafilter_and_cursor(state):
    s = state
    for ch in "ab":
        s = reduce(s, InsertChar(ch))
    s = reduce(s, ToggleCollisionOnly())
    s = reduce(s, ClearFilter())

    assert s.filter.text == ""
    assert s.filter.collision_only is False
    assert s.filter.cursor == 0
    assert s.filter.raw == ""
    assert visible_ordinals(s) == list(range(1, 12))


# ── selection clamping (spec 3.4 foundation) ─────────────────────────────────

def test_collision_only_clamps_selection_to_first_collision_row(state):
    assert state.selection.selected_ordinal == 1
    s = reduce(state, ToggleCollisionOnly())
    assert s.selection.selected_ordinal == 2


def test_still_visible_selection_is_preserved(state):
    # Filter "1" keeps ordinal 1 visible (rows 1, 4, 10, 11).
    s = reduce(state, InsertChar("1"))
    assert visible_ordinals(s) == [1, 4, 10, 11]
    assert s.selection.selected_ordinal == 1


def test_empty_result_clears_selection(state):
    s = state
    for ch in "zzz":
        s = reduce(s, InsertChar(ch))
    assert visible_ordinals(s) == []
    assert s.selection.selected_ordinal is None
