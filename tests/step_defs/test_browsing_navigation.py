from pytest_bdd import given, when, then, parsers, scenarios
import blessed

from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.selectors import select_visible_rows
from tests.fixtures.storyboard import make_config, make_mappings

scenarios("../features/browsing_navigation.feature")


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="state")
def state_storyboard():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


@when(parsers.parse('the reviewer types "{text}" into the filter'), target_fixture="state")
def type_text(state, text):
    for char in text:
        state = reduce(state, key_to_action(char))
    return state


@when("the reviewer presses esc", target_fixture="state")
def press_esc(state):
    return reduce(state, key_to_action("\x1b"))


class _NamedKey:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return ""


@when("the reviewer presses down", target_fixture="state")
def press_down(state):
    return reduce(state, key_to_action(_NamedKey("KEY_DOWN")))


@when("the reviewer presses up", target_fixture="state")
def press_up(state):
    return reduce(state, key_to_action(_NamedKey("KEY_UP")))


@when("the reviewer presses page down", target_fixture="state")
def press_page_down(state):
    return reduce(state, key_to_action(_NamedKey("KEY_PGDOWN")))


@when("the reviewer presses page up", target_fixture="state")
def press_page_up(state):
    return reduce(state, key_to_action(_NamedKey("KEY_PGUP")))


@when("the reviewer presses ctrl+n", target_fixture="state")
def press_ctrl_n(state):
    return reduce(state, key_to_action("\x0e"))


@when("the reviewer presses ctrl+p", target_fixture="state")
def press_ctrl_p(state):
    return reduce(state, key_to_action("\x10"))


@then(parsers.parse("the visible ordinals are {ordinals}"))
def check_visible_ordinals(state, ordinals):
    visible = select_visible_rows(state)
    expected = [int(x.strip()) for x in ordinals.split(",")]
    assert [m.ordinal for m in visible] == expected


@then("no rows are visible")
def check_no_rows(state):
    visible = select_visible_rows(state)
    assert not visible


@then(parsers.parse("the selected ordinal is {ordinal}"))
def check_selected_ordinal(state, ordinal):
    if ordinal == "None":
        assert state.selection.selected_ordinal is None
    else:
        assert state.selection.selected_ordinal == int(ordinal)


@then(parsers.parse("the scroll offset is {offset:d}"))
def check_scroll_offset(state, offset):
    assert state.selection.scroll_offset == offset


@then(parsers.parse('the footer shows "{text}"'))
def check_footer(state, text):
    lines = render_lines(state)
    footer = lines[-1]
    assert text in footer
