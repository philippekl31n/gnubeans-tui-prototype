"""
TASK-007 — BDD step definitions for source-list navigation and buffer autofill.

Steps drive the reducer through the same input-layer normalisation the live loop
uses: Enter, printable characters, Backspace, and the ``↑`` / ``↓`` arrow keys
arrive as key text or blessed ``Keystroke`` objects, are mapped by
``key_to_action``, and dispatched through ``reduce`` (spec §7.4 / FR21).
Assertions read the resulting ``EditState`` and the rendered source-pointer
column so the scenario exercises the dispatch path end to end.
"""
from dataclasses import replace

from blessed.keyboard import Keystroke
from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from mapping_resolution_tui.state import FocusRegion, Mode

scenarios("../features/source_navigation.feature")

_ENTER = "\r"
_BACKSPACE = "\x7f"
_KEY_DOWN = Keystroke("\x1b[B", code=258, name="KEY_DOWN")
_KEY_UP = Keystroke("\x1b[A", code=259, name="KEY_UP")


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state

    def dispatch(self, key):
        action = key_to_action(key)
        if action is not None:
            self.state = reduce(self.state, action)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


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


@when("the reviewer presses down arrow in the edit view")
def press_down(ctx):
    ctx.dispatch(_KEY_DOWN)


@when("the reviewer presses up arrow in the edit view")
def press_up(ctx):
    ctx.dispatch(_KEY_UP)


@when("the reviewer presses backspace in the token input")
def press_backspace(ctx):
    ctx.dispatch(_BACKSPACE)


@then(parsers.parse("the focus region is {region}"))
def assert_focus_region(ctx, region):
    assert ctx.state.edit.focus_region == FocusRegion[region]


@then(parsers.parse("the source pointer index is {index:d}"))
def assert_source_pointer_index(ctx, index):
    assert ctx.state.edit.source_pointer_index == index


@then("the source pointer index is cleared")
def assert_source_pointer_cleared(ctx):
    assert ctx.state.edit.source_pointer_index is None


@then("the saved source entry buffer is empty")
def assert_entry_buffer_empty(ctx):
    assert ctx.state.edit.source_entry_buffer == ""


@then("the saved source entry buffer is cleared")
def assert_entry_buffer_cleared(ctx):
    assert ctx.state.edit.source_entry_buffer is None


@then(parsers.parse('the edit buffer is "{text}"'))
def assert_buffer(ctx, text):
    assert ctx.state.edit.buffer == text


@then(parsers.parse("the edit cursor is at position {position:d}"))
def assert_cursor(ctx, position):
    assert ctx.state.edit.cursor == position


@then(parsers.parse('the validation status is "{status}"'))
def assert_validation_status(ctx, status):
    assert ctx.state.edit.validation.status == status


@then(parsers.parse("the source pointer is on the {label} source"))
def assert_pointer_on_source(ctx, label):
    lines = [strip_ansi(line) for line in render_lines(ctx.state)]
    source_lines = [line for line in lines if "┃" in line]
    pointed = [line for line in source_lines if "▸" in line]
    assert len(pointed) == 1
    assert f"{label}:" in pointed[0]


@then("exactly one source pointer indicator is rendered")
def assert_single_pointer(ctx):
    lines = [strip_ansi(line) for line in render_lines(ctx.state)]
    # The row cursor ▸ is suppressed in the source list, so the only ▸ present is
    # the source pointer (spec §6.3 / §7.4).
    assert sum(line.count("▸") for line in lines) == 1
    assert ctx.state.mode == Mode.EDITING
