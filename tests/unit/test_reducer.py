"""
Unit tests for the Redux-style dispatch reducer (browsing-mode filter editing).

The filter is a single editable buffer ``filter.raw`` with a caret
``filter.cursor``; ``collision_only`` and ``text`` are derived from ``filter.raw``
after every mutation (spec §3.3). All edits and the caret operate on ``raw``.
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.actions import (
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
)
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import parse_filter
from mapping_resolution_tui.state import FilterState


@pytest.fixture
def state():
    from tests.fixtures.storyboard import make_config, make_mappings

    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def _raw(state, raw: str, cursor: int):
    """Return ``state`` with ``filter.raw`` set and derived fields recomputed."""
    collision_only, text = parse_filter(raw)
    return replace(
        state,
        filter=FilterState(raw=raw, collision_only=collision_only, text=text, cursor=cursor),
    )


# ── derivation: raw is the source of truth (spec §3.3) ──────────────────────────

def test_parse_filter_derives_collision_only_and_text():
    assert parse_filter("") == (False, "")
    assert parse_filter("3") == (False, "3")
    assert parse_filter("!") == (True, "")
    assert parse_filter("!3") == (True, "3")


# ── character insertion (FR9) ──────────────────────────────────────────────────

def test_insert_character_appends_and_advances_cursor(state):
    new_state = reduce(state, InsertCharacter("a"))
    assert new_state.filter.raw == "a"
    assert new_state.filter.text == "a"
    assert new_state.filter.cursor == 1


def test_insert_character_inserts_at_cursor_in_middle(state):
    state = _raw(state, "ac", 1)
    new_state = reduce(state, InsertCharacter("b"))
    assert new_state.filter.raw == "abc"
    assert new_state.filter.cursor == 2


def test_insert_bang_at_index_0_becomes_collision_metafilter(state):
    new_state = reduce(state, InsertCharacter("!"))
    assert new_state.filter.raw == "!"
    assert new_state.filter.collision_only is True
    assert new_state.filter.text == ""
    assert new_state.filter.cursor == 1


def test_insert_bang_after_text_is_ordinary_literal(state):
    state = _raw(state, "AT", 2)
    new_state = reduce(state, InsertCharacter("!"))
    assert new_state.filter.raw == "AT!"
    assert new_state.filter.collision_only is False
    assert new_state.filter.text == "AT!"


def test_typing_text_after_a_leading_bang_keeps_metafilter(state):
    state = reduce(state, InsertCharacter("!"))
    state = reduce(state, InsertCharacter("3"))
    assert state.filter.raw == "!3"
    assert state.filter.collision_only is True
    assert state.filter.text == "3"


# ── cursor movement (FR9) ───────────────────────────────────────────────────────

def test_move_cursor_left_decrements(state):
    state = _raw(state, "abc", 2)
    assert reduce(state, MoveCursorLeft()).filter.cursor == 1


def test_move_cursor_left_clamps_at_zero(state):
    state = _raw(state, "abc", 0)
    assert reduce(state, MoveCursorLeft()).filter.cursor == 0


def test_move_cursor_right_increments(state):
    state = _raw(state, "abc", 1)
    assert reduce(state, MoveCursorRight()).filter.cursor == 2


def test_move_cursor_right_clamps_at_raw_length(state):
    state = _raw(state, "abc", 3)
    assert reduce(state, MoveCursorRight()).filter.cursor == 3


def test_move_cursor_home_and_end(state):
    state = _raw(state, "abc", 1)
    assert reduce(state, MoveCursorHome()).filter.cursor == 0
    assert reduce(state, MoveCursorEnd()).filter.cursor == 3


def test_cursor_movement_preserves_raw(state):
    state = _raw(state, "abc", 2)
    assert reduce(state, MoveCursorLeft()).filter.raw == "abc"
    assert reduce(state, MoveCursorRight()).filter.raw == "abc"


# ── backspace / forward delete ──────────────────────────────────────────────────

def test_delete_backward_removes_char_before_cursor(state):
    state = _raw(state, "abc", 3)
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.raw == "ab"
    assert new_state.filter.cursor == 2


def test_delete_backward_in_middle(state):
    state = _raw(state, "abc", 2)
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.raw == "ac"
    assert new_state.filter.cursor == 1


def test_delete_backward_at_cursor_zero_is_noop(state):
    state = _raw(state, "abc", 0)
    assert reduce(state, DeleteBackward()) is state


def test_delete_backward_on_empty_is_noop(state):
    assert reduce(state, DeleteBackward()) is state


def test_delete_backward_of_leading_bang_clears_metafilter(state):
    state = _raw(state, "!", 1)
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.raw == ""
    assert new_state.filter.collision_only is False


def test_delete_forward_removes_char_at_cursor(state):
    state = _raw(state, "abc", 1)
    new_state = reduce(state, DeleteForward())
    assert new_state.filter.raw == "ac"
    assert new_state.filter.cursor == 1


def test_delete_forward_at_end_is_noop(state):
    state = _raw(state, "abc", 3)
    assert reduce(state, DeleteForward()) is state


# ── kill-line / unix-line-discard ───────────────────────────────────────────────

def test_kill_to_end_truncates_from_cursor(state):
    state = _raw(state, "abcdef", 2)
    new_state = reduce(state, KillToEnd())
    assert new_state.filter.raw == "ab"
    assert new_state.filter.cursor == 2


def test_kill_to_end_at_end_is_noop(state):
    state = _raw(state, "abc", 3)
    assert reduce(state, KillToEnd()) is state


def test_kill_to_start_removes_through_cursor_and_resets_cursor(state):
    state = _raw(state, "abcdef", 4)
    new_state = reduce(state, KillToStart())
    assert new_state.filter.raw == "ef"
    assert new_state.filter.cursor == 0


def test_kill_to_start_at_zero_is_noop(state):
    state = _raw(state, "abc", 0)
    assert reduce(state, KillToStart()) is state


# ── word kills (ASCII word boundaries [A-Za-z0-9_-]) ────────────────────────────

def test_delete_word_backward_removes_previous_word(state):
    state = _raw(state, "foo bar", 7)
    new_state = reduce(state, DeleteWordBackward())
    assert new_state.filter.raw == "foo "
    assert new_state.filter.cursor == 4


def test_delete_word_backward_skips_trailing_non_word_chars(state):
    state = _raw(state, "foo   ", 6)
    new_state = reduce(state, DeleteWordBackward())
    assert new_state.filter.raw == ""
    assert new_state.filter.cursor == 0


def test_delete_word_backward_at_zero_is_noop(state):
    state = _raw(state, "foo", 0)
    assert reduce(state, DeleteWordBackward()) is state


def test_delete_word_forward_removes_next_word(state):
    state = _raw(state, "foo bar", 0)
    new_state = reduce(state, DeleteWordForward())
    assert new_state.filter.raw == " bar"
    assert new_state.filter.cursor == 0


def test_delete_word_forward_at_end_is_noop(state):
    state = _raw(state, "foo", 3)
    assert reduce(state, DeleteWordForward()) is state


# ── filter clear (Esc) ─────────────────────────────────────────────────────────

def test_clear_filter_resets_raw_and_cursor(state):
    state = _raw(state, "!abc", 4)
    new_state = reduce(state, ClearFilter())
    assert new_state.filter.raw == ""
    assert new_state.filter.text == ""
    assert new_state.filter.cursor == 0
    assert new_state.filter.collision_only is False


def test_clear_filter_on_empty_is_noop(state):
    assert reduce(state, ClearFilter()) is state


# ── immutability and dispatch contract ─────────────────────────────────────────

def test_reduce_does_not_mutate_input_state(state):
    original_filter = state.filter
    reduce(state, InsertCharacter("z"))
    assert state.filter is original_filter
    assert state.filter.raw == ""


def test_reduce_returns_new_frozen_filter_state(state):
    new_state = reduce(state, InsertCharacter("z"))
    assert isinstance(new_state.filter, FilterState)
    assert new_state.filter is not state.filter


def test_reduce_ignores_unknown_action(state):
    class _Unknown:
        pass

    assert reduce(state, _Unknown()) is state


def test_every_mutation_keeps_derived_fields_in_sync(state):
    state = reduce(state, InsertCharacter("!"))
    state = reduce(state, InsertCharacter("3"))
    assert state.filter.raw == "!3"
    assert (state.filter.collision_only, state.filter.text) == parse_filter(state.filter.raw)
