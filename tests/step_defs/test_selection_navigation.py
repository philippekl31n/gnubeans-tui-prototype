"""
TASK-004 — BDD step definitions for selection clamping, browsing navigation,
and the empty-result frame.

Steps drive the reducer through the same input-layer normalisation the live loop
uses: arrows and page keys arrive as blessed ``Keystroke`` objects and readline
aliases (``ctrl+n`` / ``ctrl+p``) as control bytes, so ``key_to_action`` plus the
reducer are exercised end to end (spec §3.4, §8.2, §8.3, §8.5).
"""
from dataclasses import replace

from blessed.keyboard import Keystroke
from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.actions import InsertChar
from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from mapping_resolution_tui.selectors import select_body_rows, select_visible_rows

scenarios("../features/selection_navigation.feature")


# Blessed Keystrokes for the navigation keys the live loop normalises.
_KEY_DOWN = Keystroke("\x1b[B", code=258, name="KEY_DOWN")
_KEY_UP = Keystroke("\x1b[A", code=259, name="KEY_UP")
_KEY_PGDOWN = Keystroke("\x1b[6~", code=338, name="KEY_PGDOWN")
_KEY_PGUP = Keystroke("\x1b[5~", code=339, name="KEY_PGUP")
_ALIASES = {"ctrl+n": "\x0e", "ctrl+p": "\x10"}


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state
        self.lines = None

    def dispatch(self, key):
        action = key_to_action(key)
        if action is not None:
            self.state = reduce(self.state, action)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


@given(parsers.parse("the reviewer has selected ordinal {ordinal:d}"))
def preselect_ordinal(ctx, ordinal):
    ctx.state = replace(
        ctx.state,
        selection=replace(ctx.state.selection, selected_ordinal=ordinal),
    )


@when(parsers.parse('the reviewer types "{text}" into the filter'))
def type_text(ctx, text):
    for char in text:
        ctx.state = reduce(ctx.state, InsertChar(char))


@when("the reviewer presses down arrow")
def press_down(ctx):
    ctx.dispatch(_KEY_DOWN)


@when("the reviewer presses up arrow")
def press_up(ctx):
    ctx.dispatch(_KEY_UP)


@when(parsers.parse("the reviewer presses down arrow {count:d} times"))
def press_down_n(ctx, count):
    for _ in range(count):
        ctx.dispatch(_KEY_DOWN)


@when(parsers.parse('the reviewer presses "{alias}"'))
def press_alias(ctx, alias):
    ctx.dispatch(_ALIASES[alias])


@when("the reviewer presses page down")
def press_page_down(ctx):
    ctx.dispatch(_KEY_PGDOWN)


@when("the reviewer presses page up")
def press_page_up(ctx):
    ctx.dispatch(_KEY_PGUP)


@when("a plain down arrow arrives because the terminal cannot detect shift")
def plain_down_arrow(ctx):
    # When Shift+arrows are indistinguishable, the shifted chord arrives as a
    # plain KEY_DOWN and MUST move exactly one row (spec §5 / §10.2).
    ctx.dispatch(_KEY_DOWN)


@when("PgDn arrives from the same terminal")
def pgdn_from_terminal(ctx):
    ctx.dispatch(_KEY_PGDOWN)


@when("the browsing frame is rendered")
def render_frame(ctx):
    ctx.lines = render_lines(ctx.state)


@then(parsers.parse("the selected ordinal is {ordinal:d}"))
def assert_selected_ordinal(ctx, ordinal):
    assert ctx.state.selection.selected_ordinal == ordinal


@then(parsers.parse("the scroll offset is {offset:d}"))
def assert_scroll_offset(ctx, offset):
    assert ctx.state.selection.scroll_offset == offset


@then(parsers.parse("the visible ordinals are {ordinals}"))
def assert_visible_ordinals(ctx, ordinals):
    expected = [int(part) for part in ordinals.split(",")]
    assert [m.ordinal for m in select_visible_rows(ctx.state)] == expected


@then("no rows are visible")
def assert_no_rows(ctx):
    assert select_visible_rows(ctx.state) == []


@then("the selection is cleared")
def assert_selection_cleared(ctx):
    assert ctx.state.selection.selected_ordinal is None


@then("a single blank body row is shown under the table header")
def assert_single_blank_body_row(ctx):
    lines = ctx.lines if ctx.lines is not None else render_lines(ctx.state)
    # header, prompt, blank, table header, blank body row, blank separator, footer.
    assert len(lines) == 7
    assert "Beancount Token" in strip_ansi(lines[3])
    assert strip_ansi(lines[4]).strip() == ""
    assert strip_ansi(lines[5]).strip() == ""


@then("no row cursor is rendered")
def assert_no_row_cursor(ctx):
    lines = ctx.lines if ctx.lines is not None else render_lines(ctx.state)
    assert all("▸" not in strip_ansi(line) for line in lines)


@then(parsers.parse('the footer reads "{text}"'))
def assert_footer_text(ctx, text):
    lines = ctx.lines if ctx.lines is not None else render_lines(ctx.state)
    assert strip_ansi(lines[-1]).strip() == text


@then("the selected row is visible in the rendered body")
def assert_selected_row_visible(ctx):
    selected = ctx.state.selection.selected_ordinal
    assert selected in {m.ordinal for m in select_body_rows(ctx.state)}
    lines = render_lines(ctx.state)
    cursor_rows = [strip_ansi(line) for line in lines if strip_ansi(line).startswith("▸")]
    assert len(cursor_rows) == 1
    fields = cursor_rows[0].split()
    assert fields[1] == str(selected)


@then(parsers.parse("the rendered body still shows ordinal {ordinal:d}"))
def assert_body_shows_ordinal(ctx, ordinal):
    assert ordinal in {m.ordinal for m in select_body_rows(ctx.state)}


@then(parsers.parse("the row cursor is on ordinal {ordinal:d}"))
def assert_row_cursor_on_ordinal(ctx, ordinal):
    lines = render_lines(ctx.state)
    cursor_rows = [strip_ansi(line) for line in lines if strip_ansi(line).startswith("▸")]
    assert len(cursor_rows) == 1
    assert cursor_rows[0].split()[1] == str(ordinal)
