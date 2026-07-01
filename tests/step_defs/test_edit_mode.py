from pytest_bdd import given, when, then, parsers, scenarios
from mapping_resolution_tui.state import Mode, FocusRegion
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

@then('the edit should be cleared')
def edit_should_be_cleared(ctx):
    assert ctx.state.edit is None

@then(parsers.parse('the edit validation error should be "{expected}"'))
def edit_validation_error_should_be(ctx, expected):
    assert ctx.state.edit is not None
    assert ctx.state.edit.validation.error_message == expected

@then('the edit focus should be on the source list')
def edit_focus_source_list(ctx):
    assert ctx.state.edit is not None
    assert ctx.state.edit.focus_region == FocusRegion.SOURCE_LIST

@then('the edit focus should be on the token input')
def edit_focus_token_input(ctx):
    assert ctx.state.edit is not None
    assert ctx.state.edit.focus_region == FocusRegion.TOKEN_INPUT

@then(parsers.parse('the edit source pointer should be at {expected:d}'))
def edit_source_pointer_should_be(ctx, expected):
    assert ctx.state.edit is not None
    assert ctx.state.edit.source_pointer_index == expected
