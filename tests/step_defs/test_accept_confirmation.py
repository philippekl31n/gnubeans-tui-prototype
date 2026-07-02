"""TASK-010 BDD step definitions: the accept-confirmation flow.

Auto-entry (FR23), ctrl+s entry, y/n and arrow toggling, accepting on YES, and
returning to browsing on NO/Esc with the filter preserved (spec §4.1/§4.2).
"""

from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_event
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import ConfirmationChoice, ConfirmationKind, Mode

scenarios("../features/accept_confirmation.feature")

_CTRL_S = "\x13"  # the raw byte a headless driver injects for ctrl+s


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
def resolve_att(ctx):
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in ctx.state.mappings
    ]
    ctx.state = replace(ctx.state, mappings=mappings)


@given(parsers.parse("the selection is on ordinal {ordinal:d}"))
def selection_on_ordinal(ctx, ordinal):
    ctx.state = replace(
        ctx.state, selection=replace(ctx.state.selection, selected_ordinal=ordinal)
    )


@when("I press ctrl+s")
def press_ctrl_s(ctx):
    ctx.dispatch(_CTRL_S)


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


@then(parsers.parse("the confirmation kind should be {kind}"))
def confirmation_kind_is(ctx, kind):
    assert ctx.state.confirmation.kind == ConfirmationKind[kind]


@then(parsers.parse("the confirmation choice should be {choice}"))
def confirmation_choice_is(ctx, choice):
    assert ctx.state.confirmation.choice == ConfirmationChoice[choice]


@then(parsers.parse("the result status should be {status}"))
def result_status_is(ctx, status):
    assert ctx.state.result.status == status


@then(parsers.parse('the filter raw should be "{expected}"'))
def filter_raw_is(ctx, expected):
    assert ctx.state.filter.raw == expected


@then(parsers.parse('mapping {ordinal:d} should have target value "{expected}"'))
def mapping_has_target(ctx, ordinal, expected):
    mapping = next(m for m in ctx.state.mappings if m.ordinal == ordinal)
    assert mapping.target_value == expected
