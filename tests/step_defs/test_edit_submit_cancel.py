"""
TASK-008 — BDD step definitions for submitting and cancelling an edit.

Steps drive the same input-layer normalisation the live loop uses: Enter, Esc,
printable characters, and ctrl+u arrive as key text, are mapped by
``key_to_action``, and dispatched through ``reduce`` (spec §4.2 / §9). Assertions
read the resulting ``AppState`` — mode, mapping targets, confirmation, filter,
selection — and the live collision selector, so the scenario exercises the
dispatch path end to end.
"""
from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import (
    select_footer_content,
    select_render_collision_ordinals,
)
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    Mode,
)

scenarios("../features/edit_submit_cancel.feature")

_ENTER = "\r"
_ESC = "\x1b"
_CTRL_U = "\x15"  # unix-line-discard: clears the token buffer


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state

    def dispatch(self, key):
        action = key_to_action(key)
        if action is not None:
            self.state = reduce(self.state, action)

    def mapping(self, ordinal):
        return next(m for m in self.state.mappings if m.ordinal == ordinal)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


@given("the AT-T collision has already been resolved")
def resolve_at_t(ctx):
    # Commit ordinal 3 to "ATT" (as the storyboard does before frame 8), leaving
    # the dataset collision-free.
    ctx.state = replace(
        ctx.state,
        mappings=[
            replace(m, target_value="ATT") if m.ordinal == 3 else m
            for m in ctx.state.mappings
        ],
    )


@given(parsers.parse('the reviewer has filtered to "{text}"'))
def filter_to(ctx, text):
    for char in text:
        ctx.dispatch(char)


@given(parsers.parse("the reviewer is editing ordinal {ordinal:d}"))
def editing_ordinal(ctx, ordinal):
    ctx.state = replace(
        ctx.state,
        selection=replace(ctx.state.selection, selected_ordinal=ordinal),
    )
    ctx.dispatch(_ENTER)


@when(parsers.parse('the reviewer types "{text}" into the token input'))
def type_token(ctx, text):
    for char in text:
        ctx.dispatch(char)


@when("the reviewer presses enter")
def press_enter(ctx):
    ctx.dispatch(_ENTER)


@when("the reviewer presses escape")
def press_escape(ctx):
    ctx.dispatch(_ESC)


@when("the reviewer clears the token input")
def clear_token(ctx):
    ctx.dispatch(_CTRL_U)


@then(parsers.parse("the mode is {mode}"))
def assert_mode(ctx, mode):
    assert ctx.state.mode == Mode[mode]


@then(parsers.parse("the confirmation kind is {kind}"))
def assert_confirmation_kind(ctx, kind):
    assert ctx.state.confirmation.kind == ConfirmationKind[kind]


@then(parsers.parse("the confirmation choice is {choice}"))
def assert_confirmation_choice(ctx, choice):
    assert ctx.state.confirmation.choice == ConfirmationChoice[choice]


@then(parsers.parse('the mapping {ordinal:d} target value is "{value}"'))
def assert_mapping_target(ctx, ordinal, value):
    assert ctx.mapping(ordinal).target_value == value


@then(parsers.parse("the mapping {ordinal:d} target value is unset"))
def assert_mapping_target_unset(ctx, ordinal):
    assert ctx.mapping(ordinal).target_value is None


@then(parsers.parse("the selected ordinal is {ordinal:d}"))
def assert_selected_ordinal(ctx, ordinal):
    assert ctx.state.selection.selected_ordinal == ordinal


@then(parsers.parse('the filter raw is "{raw}"'))
def assert_filter_raw(ctx, raw):
    assert ctx.state.filter.raw == raw


@then("there is no active edit")
def assert_no_edit(ctx):
    assert ctx.state.edit is None


@then("the edit buffer is empty")
def assert_buffer_empty(ctx):
    assert ctx.state.edit.buffer == ""


@then(parsers.parse('the footer error reads "{text}"'))
def assert_footer_error(ctx, text):
    assert select_footer_content(ctx.state).error == text


@then(parsers.parse("the live collision ordinals are {ordinals}"))
def assert_live_collision_ordinals(ctx, ordinals):
    expected = frozenset(int(part) for part in ordinals.replace(",", " ").split())
    assert select_render_collision_ordinals(ctx.state) == expected


@then("there are no live collision ordinals")
def assert_no_live_collision_ordinals(ctx):
    assert select_render_collision_ordinals(ctx.state) == frozenset()
