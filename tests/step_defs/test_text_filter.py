"""
TASK-002 — BDD step definitions for text filter input.

Steps drive the reducer through dispatched actions (and the input layer's
readline-alias normalisation) and assert the resulting AppState and rendered
frame, matching the dispatch pipeline used by the live loop.
"""
from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.actions import (
    DeleteBackward,
    InsertCharacter,
    MoveCursorLeft,
    MoveCursorRight,
)
from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.selectors import select_visible_rows
from tests.conftest import make_pyte_screen

scenarios("../features/text_filter.feature")


_ALIASES = {"ctrl+b": "\x02", "ctrl+f": "\x06", "ctrl+h": "\x08"}


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


@given(parsers.parse('the filter already contains "{text}" with the cursor at offset {offset:d}'))
def preload_filter(ctx, text, offset):
    ctx.state = replace(
        ctx.state,
        filter=replace(ctx.state.filter, text=text, cursor=offset, raw=text),
    )


@when(parsers.parse('the reviewer types "{text}" into the filter'))
def type_text(ctx, text):
    for char in text:
        ctx.state = reduce(ctx.state, InsertCharacter(char))


@when("the reviewer presses left arrow")
def press_left(ctx):
    ctx.state = reduce(ctx.state, MoveCursorLeft())


@when("the reviewer presses right arrow")
def press_right(ctx):
    ctx.state = reduce(ctx.state, MoveCursorRight())


@when(parsers.parse('the reviewer presses "{alias}"'))
def press_alias(ctx, alias):
    action = key_to_action(_ALIASES[alias])
    ctx.state = reduce(ctx.state, action)


@when("the reviewer presses backspace")
def press_backspace(ctx):
    ctx.state = reduce(ctx.state, DeleteBackward())


@when("the filter view is rendered", target_fixture="screen")
def render_screen(ctx):
    return make_pyte_screen(render_lines(ctx.state))


@then(parsers.parse('the filter text is "{text}"'))
def assert_text(ctx, text):
    assert ctx.state.filter.text == text


@then(parsers.parse("the filter cursor is at offset {offset:d}"))
def assert_cursor(ctx, offset):
    assert ctx.state.filter.cursor == offset


@then(parsers.parse("the visible ordinals are {ordinals}"))
def assert_visible_ordinals(ctx, ordinals):
    expected = [int(part) for part in ordinals.split(",")]
    assert [m.ordinal for m in select_visible_rows(ctx.state)] == expected


@then("no rows are visible")
def assert_no_rows(ctx):
    assert select_visible_rows(ctx.state) == []


@then(parsers.parse("the matched ordinal digit on the row for ordinal {ordinal:d} is bold"))
def assert_ordinal_bold(screen, ordinal):
    # Ordinal 1 renders on display row index 4; its "1" digit sits at column 4.
    assert screen.buffer[4][4].bold is True


@then(parsers.parse("the token match on the row for ordinal {ordinal:d} is bold"))
def assert_token_bold(screen, ordinal):
    # Ordinal 4 renders on display row index 5; "C100-F" begins at column 8, so
    # the matched "1" is at column 9 (the "C" at column 8 is not bold).
    assert screen.buffer[5][8].bold is False
    assert screen.buffer[5][9].bold is True


@then("the source column is not bold on any visible row")
def assert_source_not_bold(screen):
    for row in range(4, 8):
        assert not any(screen.buffer[row][col].bold for col in range(34, 80))


@then("the prompt ends with a reverse-video cursor block")
def assert_prompt_cursor(screen):
    # "  Filter: " spans columns 0–9, "1" at column 10, cursor block at column 11.
    assert screen.buffer[1][11].reverse is True
    assert screen.display[1][11] == " "
