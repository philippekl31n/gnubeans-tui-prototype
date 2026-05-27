import pytest
from pytest_bdd import given, when, then, scenarios

scenarios("../features/initial_state.feature")


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="state")
def storyboard_state():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


@when("the initial state is inspected", target_fixture="inspected_state")
def inspect_state(state):
    return state


@then("the mode is BROWSING")
def mode_is_browsing(state):
    from mapping_resolution_tui.state import Mode
    assert state.mode == Mode.BROWSING


@then("the filter text is empty")
def filter_is_empty(state):
    assert state.filter.text == ""
    assert state.filter.collision_only is False


@then("the selected ordinal is 1")
def selected_ordinal_is_1(state):
    assert state.selection.selected_ordinal == 1


@then("the scroll offset is 0")
def scroll_offset_is_0(state):
    assert state.selection.scroll_offset == 0


@then("edit state is absent")
def edit_is_none(state):
    assert state.edit is None


@when("the visible rows are computed for the initial state", target_fixture="displayed_rows")
def compute_displayed_rows(state):
    from mapping_resolution_tui.selectors import select_visible_rows, select_body_capacity
    visible = select_visible_rows(state)
    capacity = select_body_capacity(state.terminal.height)
    return visible[state.selection.scroll_offset : state.selection.scroll_offset + capacity]


@then("exactly 9 rows are shown in the frame")
def exactly_9_rows(displayed_rows):
    assert len(displayed_rows) == 9


@then("all ordinals from 1 through 9 are among the displayed rows")
def ordinals_1_through_9(displayed_rows):
    assert {m.ordinal for m in displayed_rows} == {1, 2, 3, 4, 5, 6, 7, 8, 9}
