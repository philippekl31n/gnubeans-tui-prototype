"""
TASK-006 — BDD step definitions for entering edit mode and typed input.

Steps drive the same input-layer normalisation the live loop uses: Enter,
printable characters, and Backspace arrive as key text, are mapped by
``key_to_action``, and dispatched through ``reduce`` (spec §7.1/§7.2). Assertions
read the resulting ``EditState`` and the derived ghost/validation/footer
selectors so the scenario exercises the dispatch path end to end.
"""
from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_footer_content, select_ghost_suffix
from mapping_resolution_tui.state import FooterHint, Mode

scenarios("../features/edit_mode.feature")

_ENTER = "\r"
_BACKSPACE = "\x7f"


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state

    def dispatch(self, key):
        action = key_to_action(key)
        if action is not None:
            self.state = reduce(self.state, action)

    def edited_mapping(self):
        ordinal = self.state.edit.mapping_ordinal
        return next(m for m in self.state.mappings if m.ordinal == ordinal)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


@given(parsers.parse("the reviewer has selected ordinal {ordinal:d}"))
def select_ordinal(ctx, ordinal):
    ctx.state = replace(
        ctx.state,
        selection=replace(ctx.state.selection, selected_ordinal=ordinal),
    )


@given(parsers.parse("the reviewer is editing ordinal {ordinal:d}"))
def editing_ordinal(ctx, ordinal):
    select_ordinal(ctx, ordinal)
    ctx.dispatch(_ENTER)


@when("the reviewer presses enter")
def press_enter(ctx):
    ctx.dispatch(_ENTER)


@when(parsers.parse('the reviewer types "{text}" into the token input'))
def type_token(ctx, text):
    for char in text:
        ctx.dispatch(char)


@when("the reviewer presses backspace in the token input")
def press_backspace(ctx):
    ctx.dispatch(_BACKSPACE)


@then("the mode is EDITING")
def assert_mode_editing(ctx):
    assert ctx.state.mode == Mode.EDITING


@then(parsers.parse("the edited ordinal is {ordinal:d}"))
def assert_edited_ordinal(ctx, ordinal):
    assert ctx.state.edit.mapping_ordinal == ordinal


@then("the edit buffer is empty")
def assert_buffer_empty(ctx):
    assert ctx.state.edit.buffer == ""


@then(parsers.parse('the edit buffer is "{text}"'))
def assert_buffer(ctx, text):
    assert ctx.state.edit.buffer == text


@then(parsers.parse("the edit cursor is at position {position:d}"))
def assert_cursor(ctx, position):
    assert ctx.state.edit.cursor == position


@then(parsers.parse('the ghost suffix is "{suffix}"'))
def assert_ghost(ctx, suffix):
    assert select_ghost_suffix(ctx.state, ctx.edited_mapping()) == suffix


@then("the ghost suffix is empty")
def assert_ghost_empty(ctx):
    assert select_ghost_suffix(ctx.state, ctx.edited_mapping()) == ""


@then(parsers.parse('the validation status is "{status}"'))
def assert_validation_status(ctx, status):
    assert ctx.state.edit.validation.status == status


@then(parsers.parse('the footer error reads "{text}"'))
def assert_footer_error(ctx, text):
    assert select_footer_content(ctx.state).error == text


@then("the submit hint is offered")
def assert_submit_offered(ctx):
    assert FooterHint.SUBMIT in select_footer_content(ctx.state).hints


@then("the submit hint is not offered")
def assert_submit_not_offered(ctx):
    assert FooterHint.SUBMIT not in select_footer_content(ctx.state).hints
