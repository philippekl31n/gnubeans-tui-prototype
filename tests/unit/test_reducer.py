"""
Unit tests for the Redux-style dispatch reducer (browsing-mode filtering).
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.actions import (
    ClearFilter,
    DeleteBackward,
    InsertCharacter,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import FilterState


@pytest.fixture
def state():
    from tests.fixtures.storyboard import make_config, make_mappings

    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def _with_filter_state(state, **kwargs):
    return replace(state, filter=replace(state.filter, **kwargs))


# ── character insertion (FR9) ──────────────────────────────────────────────────

def test_insert_character_appends_and_advances_cursor(state):
    new_state = reduce(state, InsertCharacter("a"))
    assert new_state.filter.text == "a"
    assert new_state.filter.cursor == 1


def test_insert_character_inserts_at_cursor_in_middle(state):
    state = _with_filter_state(state, text="ac", cursor=1, raw="ac")
    new_state = reduce(state, InsertCharacter("b"))
    assert new_state.filter.text == "abc"
    assert new_state.filter.cursor == 2


def test_insert_character_keeps_raw_in_sync(state):
    new_state = reduce(state, InsertCharacter("x"))
    assert new_state.filter.raw == "x"


def test_insert_character_keeps_raw_in_sync_with_metafilter(state):
    state = _with_filter_state(state, collision_only=True, raw="!")
    new_state = reduce(state, InsertCharacter("x"))
    assert new_state.filter.raw == "!x"
    assert new_state.filter.text == "x"


# ── cursor movement (FR11) ─────────────────────────────────────────────────────

def test_move_cursor_left_decrements(state):
    state = _with_filter_state(state, text="abc", cursor=2, raw="abc")
    assert reduce(state, MoveCursorLeft()).filter.cursor == 1


def test_move_cursor_left_clamps_at_zero(state):
    state = _with_filter_state(state, text="abc", cursor=0, raw="abc")
    assert reduce(state, MoveCursorLeft()).filter.cursor == 0


def test_move_cursor_right_increments(state):
    state = _with_filter_state(state, text="abc", cursor=1, raw="abc")
    assert reduce(state, MoveCursorRight()).filter.cursor == 2


def test_move_cursor_right_clamps_at_text_length(state):
    state = _with_filter_state(state, text="abc", cursor=3, raw="abc")
    assert reduce(state, MoveCursorRight()).filter.cursor == 3


def test_cursor_movement_preserves_text(state):
    state = _with_filter_state(state, text="abc", cursor=2, raw="abc")
    assert reduce(state, MoveCursorLeft()).filter.text == "abc"
    assert reduce(state, MoveCursorRight()).filter.text == "abc"


# ── collision-only toggle (FR10) ───────────────────────────────────────────────

def test_toggle_collision_only_on(state):
    new_state = reduce(state, ToggleCollisionOnly())
    assert new_state.filter.collision_only is True
    assert new_state.filter.raw == "!"


def test_toggle_collision_only_off(state):
    state = _with_filter_state(state, collision_only=True, raw="!")
    new_state = reduce(state, ToggleCollisionOnly())
    assert new_state.filter.collision_only is False
    assert new_state.filter.raw == ""


def test_toggle_collision_only_does_not_insert_literal_bang(state):
    state = _with_filter_state(state, text="ab", cursor=2, raw="ab")
    new_state = reduce(state, ToggleCollisionOnly())
    assert new_state.filter.text == "ab"
    assert new_state.filter.raw == "!ab"


# ── filter clear (Esc) ─────────────────────────────────────────────────────────

def test_clear_filter_resets_text_collision_and_cursor(state):
    state = _with_filter_state(state, text="abc", cursor=3, collision_only=True, raw="!abc")
    new_state = reduce(state, ClearFilter())
    assert new_state.filter.text == ""
    assert new_state.filter.cursor == 0
    assert new_state.filter.collision_only is False
    assert new_state.filter.raw == ""


# ── backspace / delete (FR10/FR13) ─────────────────────────────────────────────

def test_delete_backward_removes_char_before_cursor(state):
    state = _with_filter_state(state, text="abc", cursor=3, raw="abc")
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.text == "ab"
    assert new_state.filter.cursor == 2


def test_delete_backward_in_middle(state):
    state = _with_filter_state(state, text="abc", cursor=2, raw="abc")
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.text == "ac"
    assert new_state.filter.cursor == 1


def test_delete_backward_at_empty_with_metafilter_clears_metafilter(state):
    state = _with_filter_state(state, text="", cursor=0, collision_only=True, raw="!")
    new_state = reduce(state, DeleteBackward())
    assert new_state.filter.collision_only is False
    assert new_state.filter.text == ""
    assert new_state.filter.raw == ""


def test_delete_backward_at_empty_without_metafilter_is_noop(state):
    new_state = reduce(state, DeleteBackward())
    assert new_state is state


def test_delete_backward_at_cursor_zero_with_text_is_noop(state):
    state = _with_filter_state(state, text="abc", cursor=0, raw="abc")
    new_state = reduce(state, DeleteBackward())
    assert new_state is state


# ── immutability and dispatch contract ─────────────────────────────────────────

def test_reduce_does_not_mutate_input_state(state):
    original_filter = state.filter
    reduce(state, InsertCharacter("z"))
    assert state.filter is original_filter
    assert state.filter.text == ""


def test_reduce_returns_new_frozen_filter_state(state):
    new_state = reduce(state, InsertCharacter("z"))
    assert isinstance(new_state.filter, FilterState)
    assert new_state.filter is not state.filter


def test_reduce_ignores_unknown_action(state):
    class _Unknown:
        pass

    assert reduce(state, _Unknown()) is state


def test_raw_stays_in_sync_across_a_sequence(state):
    state = reduce(state, ToggleCollisionOnly())
    state = reduce(state, InsertCharacter("3"))
    assert state.filter.collision_only is True
    assert state.filter.text == "3"
    assert state.filter.raw == "!3"
