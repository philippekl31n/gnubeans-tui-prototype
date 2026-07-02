from dataclasses import replace
from pytest_bdd import given, when, then, parsers, scenarios
from mapping_resolution_tui.loop import key_to_event
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import Mode

scenarios("../features/confirming_scroll.feature")

class _Ctx:
    def __init__(self, state):
        self.state = state

    def dispatch(self, key):
        event = key_to_event(key)
        if event is not None:
            self.state = reduce(self.state, event)

@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings
    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))

@given(parsers.parse("the selection is on ordinal {ordinal:d}"))
def selection_on_ordinal(ctx, ordinal):
    ctx.state = replace(
        ctx.state, selection=replace(ctx.state.selection, selected_ordinal=ordinal)
    )

@when(parsers.parse('I press "{key}"'))
def press_key(ctx, key):
    from blessed.keyboard import Keystroke
    ctx.dispatch(Keystroke(name=key))

@when(parsers.parse('I type "{text}"'))
def type_text(ctx, text):
    for char in text:
        ctx.dispatch(char)

@then(parsers.parse("the app should be in {mode_name} mode"))
def app_in_mode(ctx, mode_name):
    assert ctx.state.mode == Mode[mode_name]

@then(parsers.parse("the scroll offset should be {offset:d}"))
def assert_scroll_offset(ctx, offset):
    assert ctx.state.selection.scroll_offset == offset

@then(parsers.parse("the selected ordinal should be {ordinal:d}"))
def assert_selected_ordinal(ctx, ordinal):
    assert ctx.state.selection.selected_ordinal == ordinal
