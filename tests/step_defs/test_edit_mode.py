from pytest_bdd import given, when, then, parsers, scenarios
from mapping_resolution_tui.state import Mode
from mapping_resolution_tui.loop import key_to_event
from mapping_resolution_tui.reducer import make_initial_state, reduce

scenarios("../features/edit_mode.feature")

class _Ctx:
    def __init__(self, state):
        self.state = state
        self.lines = None

    def dispatch(self, key):
        event = key_to_event(key)
        if event is not None:
            self.state = reduce(self.state, event)

@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings
    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))

@when(parsers.parse('I press "{key}"'))
def press_key(ctx, key):
    from blessed.keyboard import Keystroke
    keystroke = Keystroke(name=key)
    ctx.dispatch(keystroke)

@when(parsers.parse('I type "{text}"'))
def type_text(ctx, text):
    for char in text:
        ctx.dispatch(char)

@then('the app should be in EDITING mode')
def app_in_editing_mode(ctx):
    assert ctx.state.mode == Mode.EDITING

@then('the app should be in BROWSING mode')
def app_in_browsing_mode(ctx):
    assert ctx.state.mode == Mode.BROWSING

@then('the edit buffer should be empty')
def edit_buffer_empty(ctx):
    assert ctx.state.edit is not None
    assert ctx.state.edit.buffer == ""

@then(parsers.parse('the edit buffer should be "{expected}"'))
def edit_buffer_should_be(ctx, expected):
    assert ctx.state.edit is not None
    assert ctx.state.edit.buffer == expected

@then(parsers.parse('the edit cursor should be at {expected:d}'))
def edit_cursor_should_be(ctx, expected):
    assert ctx.state.edit is not None
    assert ctx.state.edit.cursor == expected
