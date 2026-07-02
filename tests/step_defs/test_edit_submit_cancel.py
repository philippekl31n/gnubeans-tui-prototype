"""TASK-008 BDD step definitions: submit, cancel, and live collision recompute."""

from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_event
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_render_collision_ordinals
from mapping_resolution_tui.state import ConfirmationChoice, ConfirmationKind, Mode

scenarios("../features/edit_submit_cancel.feature")


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


@then(parsers.parse("the confirmation kind should be {kind}"))
def confirmation_kind_is(ctx, kind):
    assert ctx.state.confirmation.kind == ConfirmationKind[kind]


@then(parsers.parse("the confirmation choice should be {choice}"))
def confirmation_choice_is(ctx, choice):
    assert ctx.state.confirmation.choice == ConfirmationChoice[choice]


@then(parsers.parse('mapping {ordinal:d} should have target value "{expected}"'))
def mapping_has_target(ctx, ordinal, expected):
    mapping = next(m for m in ctx.state.mappings if m.ordinal == ordinal)
    assert mapping.target_value == expected


@then(parsers.parse("mapping {ordinal:d} should have no target value"))
def mapping_has_no_target(ctx, ordinal):
    mapping = next(m for m in ctx.state.mappings if m.ordinal == ordinal)
    assert mapping.target_value is None


@then(parsers.parse("the selected ordinal should be {ordinal:d}"))
def selected_ordinal_is(ctx, ordinal):
    assert ctx.state.selection.selected_ordinal == ordinal


@then(parsers.parse('the filter raw should be "{expected}"'))
def filter_raw_is(ctx, expected):
    assert ctx.state.filter.raw == expected


@then(parsers.parse('the edit validation error should be "{expected}"'))
def edit_validation_error_is(ctx, expected):
    assert ctx.state.edit is not None
    assert ctx.state.edit.validation.error_message == expected


@then("the edit buffer should be empty")
def edit_buffer_empty(ctx):
    assert ctx.state.edit is not None
    assert ctx.state.edit.buffer == ""


@then("the edit should be cleared")
def edit_cleared(ctx):
    assert ctx.state.edit is None


@then(parsers.parse("the live collision ordinals should be {a:d} and {b:d}"))
def live_collision_ordinals_are(ctx, a, b):
    assert select_render_collision_ordinals(ctx.state) == frozenset({a, b})


@then("there should be no live collision ordinals")
def no_live_collision_ordinals(ctx):
    assert select_render_collision_ordinals(ctx.state) == frozenset()
