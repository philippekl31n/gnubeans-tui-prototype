import pytest
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
