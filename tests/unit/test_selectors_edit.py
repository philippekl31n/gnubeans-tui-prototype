import pytest
from unittest.mock import Mock

from mapping_resolution_tui.state import (
    AppState, EditState, Mapping, Source, FocusRegion, ValidationState
)
from mapping_resolution_tui.selectors import (
    select_ghost_suffix,
    select_concrete_value,
    select_source_pointer_value,
    select_edit_render_row,
    VisibleSource,
    EditRowContent,
)

@pytest.fixture
def sample_mapping():
    return Mapping(
        ordinal=1,
        sources=[
            Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
            Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
        ],
        default_source_label="user_symbol",
        target_value=None,
    )

@pytest.fixture
def mock_state():
    state = Mock(spec=AppState)
    state.edit = Mock(spec=EditState)
    return state

def test_select_ghost_suffix_returns_suffix_when_prefix_matches(mock_state, sample_mapping):
    mock_state.edit.buffer = "APP"
    mock_state.edit.cursor = 3
    assert select_ghost_suffix(mock_state, sample_mapping) == "LE"

def test_select_ghost_suffix_returns_empty_when_buffer_empty_and_target_set(mock_state, sample_mapping):
    from dataclasses import replace
    mapping_with_target = replace(sample_mapping, target_value="APPLE")
    mock_state.edit.buffer = ""
    mock_state.edit.cursor = 0
    assert select_ghost_suffix(mock_state, mapping_with_target) == ""

def test_select_ghost_suffix_returns_full_default_when_buffer_empty_and_target_none(mock_state, sample_mapping):
    mock_state.edit.buffer = ""
    mock_state.edit.cursor = 0
    assert select_ghost_suffix(mock_state, sample_mapping) == "APPLE"

def test_select_ghost_suffix_returns_empty_when_cursor_not_at_end(mock_state, sample_mapping):
    mock_state.edit.buffer = "APP"
    mock_state.edit.cursor = 2
    assert select_ghost_suffix(mock_state, sample_mapping) == ""

def test_select_ghost_suffix_returns_empty_when_prefix_mismatches(mock_state, sample_mapping):
    mock_state.edit.buffer = "APL"
    mock_state.edit.cursor = 3
    assert select_ghost_suffix(mock_state, sample_mapping) == ""

def test_select_ghost_suffix_returns_empty_when_not_editing(sample_mapping):
    state = Mock(spec=AppState)
    state.edit = None
    assert select_ghost_suffix(state, sample_mapping) == ""

def test_select_concrete_value_returns_buffer_when_non_empty(mock_state, sample_mapping):
    mock_state.edit.buffer = "APP"
    assert select_concrete_value(mock_state, sample_mapping) == "APP"

def test_select_concrete_value_returns_default_when_buffer_empty(mock_state, sample_mapping):
    mock_state.edit.buffer = ""
    assert select_concrete_value(mock_state, sample_mapping) == "APPLE"

def test_select_concrete_value_returns_default_when_not_editing(sample_mapping):
    state = Mock(spec=AppState)
    state.edit = None
    assert select_concrete_value(state, sample_mapping) == "APPLE"

def test_select_source_pointer_value_returns_pointed_value(mock_state, sample_mapping):
    mock_state.edit.source_pointer_index = 0
    assert select_source_pointer_value(mock_state, sample_mapping) == "AAPL"
    
    mock_state.edit.source_pointer_index = 1
    assert select_source_pointer_value(mock_state, sample_mapping) == "APPLE"

def test_select_source_pointer_value_returns_none_when_pointer_none(mock_state, sample_mapping):
    mock_state.edit.source_pointer_index = None
    assert select_source_pointer_value(mock_state, sample_mapping) is None

def test_select_source_pointer_value_returns_none_when_out_of_bounds(mock_state, sample_mapping):
    mock_state.edit.source_pointer_index = 2
    assert select_source_pointer_value(mock_state, sample_mapping) is None

def test_select_source_pointer_value_returns_none_when_not_editing(sample_mapping):
    state = Mock(spec=AppState)
    state.edit = None
    assert select_source_pointer_value(state, sample_mapping) is None

def test_select_edit_render_row(mock_state, sample_mapping):
    mock_state.edit.buffer = "APP"
    mock_state.edit.cursor = 3
    mock_state.edit.focus_region = FocusRegion.TOKEN_INPUT
    mock_state.edit.source_pointer_index = 1
    mock_state.edit.validation = ValidationState(
        status="INVALID",
        icon="X",
        error_message="Too short"
    )
    
    row = select_edit_render_row(mock_state, sample_mapping)
    
    assert row.buffer_text == "APP"
    assert row.ghost_suffix == "LE"
    assert row.cursor_offset == 3
    assert row.validation_icon == "X"
    assert row.validation_error == "Too short"
    assert row.focus_region == FocusRegion.TOKEN_INPUT
    
    assert len(row.visible_sources) == 2
    assert row.visible_sources[0].source.original_value == "AAPL"
    assert row.visible_sources[0].is_pointed is False
    assert row.visible_sources[1].source.original_value == "APPLE"
    assert row.visible_sources[1].is_pointed is True

def test_select_edit_render_row_raises_when_not_editing(sample_mapping):
    state = Mock(spec=AppState)
    state.edit = None
    with pytest.raises(ValueError, match="Cannot select edit render row when not editing"):
        select_edit_render_row(state, sample_mapping)
