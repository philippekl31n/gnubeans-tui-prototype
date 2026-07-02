"""TASK-012 BDD step definitions: the exit-confirmation flow."""

from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_event
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import ConfirmationChoice, ConfirmationKind, Mode

scenarios("../features/exit_confirmation.feature")


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


@given("the AT-T collision is already resolved")
def resolved_dataset(ctx):
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in ctx.state.mappings
    ]
    ctx.state = replace(ctx.state, mappings=mappings)


@when(parsers.parse('I press "{key}"'))
def press_key(ctx, key):
    from blessed.keyboard import Keystroke
    ctx.dispatch(Keystroke(name=key))


@when("I press ctrl+c")
def press_ctrl_c(ctx):
    ctx.dispatch("\x03")


@when("I press ctrl+s")
def press_ctrl_s(ctx):
    ctx.dispatch("\x13")


@when(parsers.parse('I type "{text}"'))
def type_text(ctx, text):
    for char in text:
        ctx.dispatch(char)


@then(parsers.parse("the app should be in {mode_name} mode"))
def app_in_mode(ctx, mode_name):
    assert ctx.state.mode is Mode[mode_name]


@then(parsers.parse("the confirmation kind should be {kind}"))
def confirmation_kind_is(ctx, kind):
    assert ctx.state.confirmation.kind is ConfirmationKind[kind]


@then(parsers.parse("the confirmation choice should be {choice}"))
def confirmation_choice_is(ctx, choice):
    assert ctx.state.confirmation.choice is ConfirmationChoice[choice]


@then("the second ctrl+c should be armed")
def second_ctrl_c_is_armed(ctx):
    assert ctx.state.confirmation.second_ctrl_c_armed is True


@then(parsers.parse("the result status should be {status}"))
def result_status_is(ctx, status):
    assert ctx.state.result.status == status
