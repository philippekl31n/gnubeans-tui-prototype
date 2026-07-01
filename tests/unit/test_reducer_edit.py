import pytest
from mapping_resolution_tui.state import AppConfig, AppState, Mode, Mapping, EditState, FocusRegion
from mapping_resolution_tui.actions import AcceptLine, Escape, InsertChar, Backspace
from mapping_resolution_tui.reducer import make_initial_state, reduce
from tests.fixtures.storyboard import make_config, make_mappings

def test_accept_line_enters_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    assert state.mode == Mode.BROWSING

    state = reduce(state, AcceptLine())
    assert state.mode == Mode.EDITING
    assert state.edit is not None
    assert state.edit.buffer == ""
    assert state.edit.cursor == 0
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

def test_escape_cancels_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, AcceptLine())
    assert state.mode == Mode.EDITING

    state = reduce(state, Escape())
    assert state.mode == Mode.BROWSING
    assert state.edit is None

def test_insert_char_in_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, AcceptLine())

    state = reduce(state, InsertChar("A"))
    assert state.edit.buffer == "A"
    assert state.edit.cursor == 1

def test_over_limit_arms_flash():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, AcceptLine())

    for _ in range(24):
        state = reduce(state, InsertChar("A"))
    
    # 25th character is over limit
    flashed = reduce(state, InsertChar("B"), now=100.0)
    assert flashed.edit.buffer == "A" * 24  # Discarded
    assert flashed.edit.max_length_flash_until == 100.0 + 0.150

    # Next accepted keystroke clears it
    cleared = reduce(flashed, Backspace())
    assert cleared.edit.max_length_flash_until is None
