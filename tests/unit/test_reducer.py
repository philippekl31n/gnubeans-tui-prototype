"""
Unit tests for the BROWSING-mode action dispatch reducer (TASK-001/TASK-002).

``filter.raw`` is the single editable buffer and source of truth; the reducer
re-derives ``collision_only`` (raw begins with ``!``) and ``text`` (raw minus a
single leading ``!``) after every mutation, clamps ``filter.cursor`` into
``[0, len(raw)]``, and never moves the selection (selection re-clamping is
TASK-004's concern). Uses the canonical 11-row storyboard dataset so the
ordinal/collision shape matches the golden frames:

    1 APPLE   2 AT-T(!)  3 AT-T(!)  4 C100-F  5 GOOGL  6 MSFT
    7 NVDA    8 QQQ      9 SPY      10 VTSAX  11 VWUSX
"""

import pytest

from mapping_resolution_tui.actions import (
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
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_visible_rows
from tests.fixtures.storyboard import make_config, make_mappings


@pytest.fixture
def state():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def visible_ordinals(s):
    return [m.ordinal for m in select_visible_rows(s)]


def type_text(s, text):
    for ch in text:
        s = reduce(s, InsertChar(ch))
    return s


# ── immutability ─────────────────────────────────────────────────────────────

def test_reduce_returns_new_state_without_mutating_input(state):
    before = state.filter
    after = reduce(state, InsertChar("a"))

    assert after is not state
    assert after.filter is not state.filter
    assert state.filter is before
    assert state.filter.raw == ""  # original untouched


def test_unknown_action_is_a_noop(state):
    sentinel = object()
    assert reduce(state, sentinel) is state


# ── character insertion ──────────────────────────────────────────────────────

def test_insert_char_appends_and_advances_cursor(state):
    s = reduce(state, InsertChar("a"))
    assert s.filter.raw == "a"
    assert s.filter.text == "a"
    assert s.filter.cursor == 1


def test_insert_char_inserts_at_cursor_position(state):
    s = type_text(state, "ac")
    s = reduce(s, MoveCursorLeft())  # cursor now between 'a' and 'c'
    s = reduce(s, InsertChar("b"))
    assert s.filter.raw == "abc"
    assert s.filter.cursor == 2


# ── raw as source of truth: collision_only / text are derived ────────────────

def test_leading_bang_is_derived_into_collision_only(state):
    s = reduce(state, InsertChar("!"))
    assert s.filter.raw == "!"
    assert s.filter.collision_only is True
    assert s.filter.text == ""
    assert s.filter.cursor == 1


def test_bang_then_text_derives_collision_only_and_text(state):
    s = type_text(state, "!3")
    assert s.filter.raw == "!3"
    assert s.filter.collision_only is True
    assert s.filter.text == "3"


def test_non_leading_bang_is_ordinary_search_text(state):
    s = type_text(state, "a!")
    assert s.filter.collision_only is False
    assert s.filter.text == "a!"


def test_collision_only_limits_visible_rows_to_collision_group(state):
    s = reduce(state, InsertChar("!"))
    assert visible_ordinals(s) == [2, 3]


def test_collision_only_does_not_move_selection(state):
    # The reducer narrows the visible rows but does not move the selection;
    # re-clamping selection onto a visible row is TASK-004's responsibility.
    assert state.selection.selected_ordinal == 1
    s = reduce(state, InsertChar("!"))
    assert visible_ordinals(s) == [2, 3]
    assert s.selection.selected_ordinal == 1


def test_text_filter_narrows_visible_rows(state):
    # Filter "1" keeps ordinals 1, 4, 10, 11 visible.
    s = reduce(state, InsertChar("1"))
    assert visible_ordinals(s) == [1, 4, 10, 11]


def test_text_filter_matches_case_insensitively_on_target_token(state):
    s = type_text(state, "appLE")
    assert visible_ordinals(s) == [1]


def test_non_matching_filter_yields_no_visible_rows(state):
    s = type_text(state, "zzz")
    assert visible_ordinals(s) == []


# ── cursor movement ──────────────────────────────────────────────────────────

def test_move_cursor_left_clamps_at_zero(state):
    s = reduce(state, MoveCursorLeft())
    assert s.filter.cursor == 0


def test_move_cursor_right_clamps_at_raw_length(state):
    s = reduce(state, InsertChar("x"))
    s = reduce(s, MoveCursorRight())
    s = reduce(s, MoveCursorRight())
    assert s.filter.cursor == 1


def test_cursor_movement_leaves_raw_unchanged(state):
    s = reduce(state, InsertChar("a"))
    s = reduce(s, MoveCursorLeft())
    assert s.filter.raw == "a"


def test_home_moves_cursor_to_zero(state):
    s = type_text(state, "abc")
    s = reduce(s, MoveCursorHome())
    assert s.filter.cursor == 0


def test_end_moves_cursor_to_raw_length(state):
    s = type_text(state, "abc")
    s = reduce(s, MoveCursorHome())
    s = reduce(s, MoveCursorEnd())
    assert s.filter.cursor == 3


# ── backspace / delete ───────────────────────────────────────────────────────

def test_backspace_removes_char_before_cursor(state):
    s = type_text(state, "abc")
    s = reduce(s, Backspace())
    assert s.filter.raw == "ab"
    assert s.filter.cursor == 2


def test_backspace_at_cursor_zero_is_a_noop(state):
    s = type_text(state, "abc")
    s = reduce(s, MoveCursorHome())
    same = reduce(s, Backspace())
    assert same is s  # untouched state object


def test_backspacing_a_leading_bang_clears_the_metafilter(state):
    s = type_text(state, "!3")
    s = reduce(s, MoveCursorHome())
    s = reduce(s, MoveCursorRight())  # cursor between ! and 3
    s = reduce(s, Backspace())
    assert s.filter.raw == "3"
    assert s.filter.collision_only is False
    assert s.filter.text == "3"


def test_delete_removes_char_at_cursor(state):
    s = type_text(state, "abc")
    s = reduce(s, MoveCursorHome())
    s = reduce(s, DeleteChar())
    assert s.filter.raw == "bc"
    assert s.filter.cursor == 0


def test_delete_at_end_is_a_noop(state):
    s = type_text(state, "abc")
    same = reduce(s, DeleteChar())
    assert same is s


# ── kill-line / unix-line-discard ────────────────────────────────────────────

def test_kill_line_deletes_through_end(state):
    s = type_text(state, "abcdef")
    s = reduce(s, MoveCursorHome())
    s = reduce(s, MoveCursorRight())
    s = reduce(s, MoveCursorRight())
    s = reduce(s, KillLine())
    assert s.filter.raw == "ab"
    assert s.filter.cursor == 2


def test_unix_line_discard_deletes_to_start_and_resets_cursor(state):
    s = type_text(state, "abcdef")
    s = reduce(s, MoveCursorHome())
    for _ in range(4):
        s = reduce(s, MoveCursorRight())
    s = reduce(s, UnixLineDiscard())
    assert s.filter.raw == "ef"
    assert s.filter.cursor == 0


# ── word kills (wordChar = [A-Za-z0-9_-]) ────────────────────────────────────

def test_backward_kill_word_deletes_previous_word(state):
    s = type_text(state, "foo bar")
    s = reduce(s, BackwardKillWord())
    assert s.filter.raw == "foo "
    assert s.filter.cursor == 4


def test_backward_kill_word_skips_trailing_separators(state):
    s = type_text(state, "foo   ")
    s = reduce(s, BackwardKillWord())
    assert s.filter.raw == ""
    assert s.filter.cursor == 0


def test_kill_word_deletes_next_word_from_cursor(state):
    s = type_text(state, "foo bar")
    s = reduce(s, MoveCursorHome())
    s = reduce(s, KillWord())
    assert s.filter.raw == " bar"
    assert s.filter.cursor == 0


def test_word_boundary_treats_hyphen_and_underscore_as_word_chars(state):
    s = type_text(state, "a-b_c")
    s = reduce(s, BackwardKillWord())
    assert s.filter.raw == ""  # the whole token is one word


# ── redraw / clear ───────────────────────────────────────────────────────────

def test_redraw_does_not_mutate_state(state):
    s = type_text(state, "ab")
    same = reduce(s, Redraw())
    assert same is s


def test_clear_filter_resets_raw_and_cursor(state):
    s = type_text(state, "ab")
    s = reduce(s, InsertChar("!"))  # raw now "ab!"
    s = reduce(s, ClearFilter())

    assert s.filter.raw == ""
    assert s.filter.collision_only is False
    assert s.filter.text == ""
    assert s.filter.cursor == 0
    assert visible_ordinals(s) == list(range(1, 12))


# ── identity-preserving no-ops (a true no-op returns the same state object) ───
# The loop uses object identity to decide whether a repaint is needed, so a
# mutation that changes nothing must return the input state unchanged.

def test_clear_filter_on_empty_is_a_noop(state):
    same = reduce(state, ClearFilter())
    assert same is state


def test_kill_line_at_end_is_a_noop(state):
    s = type_text(state, "ab")  # cursor at end
    same = reduce(s, KillLine())
    assert same is s


def test_unix_line_discard_at_start_is_a_noop(state):
    s = type_text(state, "ab")
    s = reduce(s, MoveCursorHome())  # cursor at 0
    same = reduce(s, UnixLineDiscard())
    assert same is s


def test_kill_word_with_no_word_ahead_is_a_noop(state):
    s = type_text(state, "ab")  # cursor at end; nothing to kill forward
    same = reduce(s, KillWord())
    assert same is s


def test_backward_kill_word_with_no_word_behind_is_a_noop(state):
    s = type_text(state, "ab")
    s = reduce(s, MoveCursorHome())  # cursor at 0; nothing to kill backward
    same = reduce(s, BackwardKillWord())
    assert same is s
