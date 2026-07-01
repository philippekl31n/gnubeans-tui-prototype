import pytest
from dataclasses import replace
from mapping_resolution_tui.state import AppConfig, AppState, Mode, Mapping, EditState, FocusRegion
from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from tests.fixtures.storyboard import make_config, make_mappings

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
