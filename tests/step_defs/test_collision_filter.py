"""
TASK-003 — BDD step definitions for the collision metafilter and filter clear.

Steps drive the reducer through dispatched actions (and the input layer's
readline-alias normalisation) so the bang autocomplete, literal-bang editing,
backspace, and Esc-clear behaviours are exercised through the same dispatch
pipeline used by the live loop.
"""
from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.actions import (
    ClearFilter,
    DeleteBackward,
    InsertCharacter,
)
from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import parse_filter, select_visible_rows

scenarios("../features/collision_filter.feature")


class _Ctx:
    """Mutable holder so successive steps can advance a single AppState."""

    def __init__(self, state):
        self.state = state


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="ctx")
def loaded_ctx():
    from tests.fixtures.storyboard import make_config, make_mappings

    return _Ctx(make_initial_state(make_config(), make_mappings(), frame_height=15))


@given("the collision is resolved so no unresolved collisions remain")
def resolve_collision(ctx):
    # Give one of the AT-T pair (ordinal 3) a distinct target so the only
    # storyboard collision group disappears, hiding the Tab ghost.
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in ctx.state.mappings
    ]
    ctx.state = replace(ctx.state, mappings=mappings)


@given(parsers.parse('the filter buffer already contains "{raw}" with the cursor at offset {offset:d}'))
def preload_filter(ctx, raw, offset):
    collision_only, text = parse_filter(raw)
    ctx.state = replace(
        ctx.state,
        filter=replace(
            ctx.state.filter,
            raw=raw,
            text=text,
            collision_only=collision_only,
            cursor=offset,
        ),
    )


@when(parsers.parse('the reviewer types "{text}" into the filter'))
def type_text(ctx, text):
    for char in text:
        ctx.state = reduce(ctx.state, InsertCharacter(char))


@when(parsers.parse('the reviewer presses "{alias}"'))
def press_alias(ctx, alias):
    # The bang autocomplete arrives as Tab / ctrl+i (\x09) and is normalised by
    # the input layer exactly as the live loop does.
    aliases = {"tab": "\t"}
    action = key_to_action(aliases[alias])
    if action is not None:
        ctx.state = reduce(ctx.state, action)


@when("the reviewer presses backspace")
def press_backspace(ctx):
    ctx.state = reduce(ctx.state, DeleteBackward())


@when("the reviewer presses Esc")
def press_esc(ctx):
    ctx.state = reduce(ctx.state, ClearFilter())


@then(parsers.parse('the filter buffer is "{raw}"'))
def assert_raw(ctx, raw):
    assert ctx.state.filter.raw == raw


@then("the filter buffer is empty")
def assert_raw_empty(ctx):
    assert ctx.state.filter.raw == ""


@then(parsers.parse('the filter search text is "{text}"'))
def assert_text(ctx, text):
    assert ctx.state.filter.text == text


@then("the filter search text is empty")
def assert_text_empty(ctx):
    assert ctx.state.filter.text == ""


@then("the collision-only metafilter is active")
def assert_collision_only_active(ctx):
    assert ctx.state.filter.collision_only is True


@then("the collision-only metafilter is inactive")
def assert_collision_only_inactive(ctx):
    assert ctx.state.filter.collision_only is False


@then(parsers.parse("the filter cursor is at offset {offset:d}"))
def assert_cursor(ctx, offset):
    assert ctx.state.filter.cursor == offset


@then(parsers.parse("the visible ordinals are {ordinals}"))
def assert_visible_ordinals(ctx, ordinals):
    expected = [int(part) for part in ordinals.split(",")]
    assert [m.ordinal for m in select_visible_rows(ctx.state)] == expected


@then(parsers.parse("the selected ordinal is {ordinal:d}"))
def assert_selected_ordinal(ctx, ordinal):
    assert ctx.state.selection.selected_ordinal == ordinal
