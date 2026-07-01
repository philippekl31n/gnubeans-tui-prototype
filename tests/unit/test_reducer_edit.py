import pytest
from dataclasses import replace
from mapping_resolution_tui.state import (
    AppConfig, AppState, Mode, Mapping, EditState, FocusRegion, TargetValidationContext,
)
from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_default_source_value
from tests.fixtures.storyboard import make_config, make_mappings


def _select(state, ordinal):
    return replace(state, selection=replace(state.selection, selected_ordinal=ordinal))


def _with_target_value(state, ordinal, target_value):
    mappings = [
        replace(m, target_value=target_value) if m.ordinal == ordinal else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)

def test_accept_line_enters_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    assert state.mode == Mode.BROWSING

    state = reduce(state, KeyEvent.ENTER)
    assert state.mode == Mode.EDITING
    assert state.edit is not None
    assert state.edit.buffer == ""
    assert state.edit.cursor == 0
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

def test_enter_edit_seeds_ghost_validation_for_empty_target():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    mapping = next(m for m in state.mappings if m.ordinal == state.selection.selected_ordinal)
    assert mapping.target_value is None  # sanity: exercising the ghost-default path
    default_value = select_default_source_value(mapping)
    expected = config.target_policy.validate(
        default_value,
        TargetValidationContext(is_concrete_buffer=False, is_ghost_only_default=True, mapping=mapping),
    )

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == ""
    assert state.edit.validation == expected
    assert state.edit.validation.icon is None  # ghost-only default never shows the checkmark


def test_enter_edit_seeds_concrete_validation_for_valid_target_value():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    ordinal = state.mappings[0].ordinal
    state = _select(_with_target_value(state, ordinal, "AAPL"), ordinal)

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == "AAPL"
    assert state.edit.validation.status == "VALID"
    assert state.edit.validation.icon == "✓"  # concrete buffer, not ghost — checkmark shown


def test_enter_edit_seeds_concrete_validation_for_invalid_target_value():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    ordinal = state.mappings[0].ordinal
    state = _select(_with_target_value(state, ordinal, "aapl"), ordinal)  # lowercase: fails policy

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == "aapl"
    assert state.edit.validation.status == "INVALID"
    assert state.edit.validation.error_message == "must start with A-Z"


def test_escape_cancels_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.mode == Mode.EDITING

    state = reduce(state, KeyEvent.ESCAPE)
    assert state.mode == Mode.BROWSING
    assert state.edit is None

def test_insert_char_in_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    state = reduce(state, "A")
    assert state.edit.buffer == "A"
    assert state.edit.cursor == 1

def test_over_limit_character_is_discarded_and_flashes():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":  # 24 valid chars, fills the cap
        state = reduce(state, ch)
    before_buffer = state.edit.buffer
    assert len(before_buffer) == 24

    flashed = reduce(state, "Y", now=100.0)

    assert flashed.edit.buffer == before_buffer  # 25th char discarded
    assert flashed.edit.cursor == 24
    assert flashed.edit.max_length_flash_until == 100.0 + 1.0
    assert flashed.edit.validation.error_message == "24 chars max"
    assert flashed.edit.validation.icon == "✗"

def test_flash_clears_on_next_accepted_edit():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":
        state = reduce(state, ch)
    flashed = reduce(state, "Y", now=100.0)
    assert flashed.edit.max_length_flash_until is not None

    cleared = reduce(flashed, KeyEvent.BACKSPACE)
    assert cleared.edit.max_length_flash_until is None

def _with_source_list_focus(state):
    # No reducer path reaches SOURCE_LIST yet (source-pointer navigation is a
    # future task), so the fixture is hand-built directly on edit.
    return replace(
        state,
        edit=replace(
            state.edit,
            focus_region=FocusRegion.SOURCE_LIST,
            source_pointer_index=0,
            source_entry_buffer="prior text",
        ),
    )

def test_accepted_edit_exits_source_list():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, "A")
    state = _with_source_list_focus(state)
    assert state.edit.focus_region == FocusRegion.SOURCE_LIST

    result = reduce(state, KeyEvent.BACKSPACE)
    assert result.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert result.edit.source_pointer_index is None
    assert result.edit.source_entry_buffer is None

def test_over_limit_reject_exits_source_list():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":  # 24 valid chars, fills the cap
        state = reduce(state, ch)
    state = _with_source_list_focus(state)
    assert state.edit.focus_region == FocusRegion.SOURCE_LIST

    flashed = reduce(state, "Y", now=100.0)
    assert flashed.edit.buffer == state.edit.buffer  # 25th char still discarded
    assert flashed.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert flashed.edit.source_pointer_index is None
    assert flashed.edit.source_entry_buffer is None

def test_repeated_over_limit_rearms_the_flash_window():
    # Each rejected over-limit char re-arms max_length_flash_until from `now`,
    # not just the first one (FR20).
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":
        state = reduce(state, ch)

    first = reduce(state, "Y", now=100.0)
    assert first.edit.max_length_flash_until == 101.0

    second = reduce(first, "Z", now=200.0)
    assert second.edit.max_length_flash_until == 201.0


def test_enter_edit_is_noop_without_a_selection():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = _select(state, None)

    result = reduce(state, KeyEvent.ENTER)

    assert result is state
    assert result.mode == Mode.BROWSING
    assert result.edit is None


def test_enter_edit_preserves_filter_state():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.TAB)  # autocompletes filter.raw = "!"
    assert state.filter.raw == "!"

    state = reduce(state, KeyEvent.ENTER)

    assert state.mode == Mode.EDITING
    assert state.filter.raw == "!"  # entering EDITING never touches the filter


# ── readline aliases (FR18) ───────────────────────────────────────────────────

def _typed(state, text):
    for ch in text:
        state = reduce(state, ch)
    return state

def test_cursor_home_and_end_move_to_buffer_boundaries():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL")
    assert state.edit.cursor == 4

    state = reduce(state, KeyEvent.CURSOR_HOME)
    assert state.edit.cursor == 0

    state = reduce(state, KeyEvent.CURSOR_END)
    assert state.edit.cursor == 4


def test_cursor_left_clamps_at_zero():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.cursor == 0

    state = reduce(state, KeyEvent.CURSOR_LEFT)
    assert state.edit.cursor == 0


def test_cursor_right_clamps_at_buffer_end():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AB")
    assert state.edit.cursor == 2

    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    assert state.edit.cursor == 2


def test_kill_line_clears_after_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 2

    state = reduce(state, KeyEvent.KILL_LINE)

    assert state.edit.buffer == "AB"
    assert state.edit.cursor == 2


def test_unix_line_discard_clears_before_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 2

    state = reduce(state, KeyEvent.UNIX_LINE_DISCARD)

    assert state.edit.buffer == "CD"
    assert state.edit.cursor == 0


def test_kill_word_deletes_the_word_ahead_of_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL XYZ")
    state = reduce(state, KeyEvent.CURSOR_HOME)

    state = reduce(state, KeyEvent.KILL_WORD)

    assert state.edit.buffer == " XYZ"
    assert state.edit.cursor == 0


def test_backward_kill_word_deletes_the_word_behind_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL XYZ")  # cursor already at the end

    state = reduce(state, KeyEvent.BACKWARD_KILL_WORD)

    assert state.edit.buffer == "AAPL "
    assert state.edit.cursor == 5


def test_delete_char_removes_the_character_at_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 1

    state = reduce(state, KeyEvent.DELETE_CHAR)

    assert state.edit.buffer == "ACD"
    assert state.edit.cursor == 1


def test_delete_char_at_end_of_buffer_is_noop():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AB")

    result = reduce(state, KeyEvent.DELETE_CHAR)

    assert result is state


def test_backspace_on_empty_buffer_is_noop():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.buffer == ""

    result = reduce(state, KeyEvent.BACKSPACE)

    assert result is state
