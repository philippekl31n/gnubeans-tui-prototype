"""
Step definitions for the collision-metafilter BDD scenarios (TASK-003).

Steps drive the loop's input layer end to end: a Tab / character / named key is
normalised by ``key_to_action`` exactly as the live loop does, then dispatched
through ``reduce``. The bang-autocomplete ghost gate lives in the reducer, so
these scenarios exercise the real Tab → AutocompleteBang → reduce path.
"""
from dataclasses import replace

from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_action
from mapping_resolution_tui.reducer import reduce
from mapping_resolution_tui.selectors import select_visible_rows

scenarios("../features/collision_metafilter.feature")

_TAB = "\t"
_ESC = "\x1b"


def _dispatch_key(state, key):
    action = key_to_action(key)
    if action is None:
        return state
    return reduce(state, action)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="state")
def storyboard_loaded(initial_state):
    return initial_state


@given("the AT-T collision is resolved", target_fixture="state")
def at_t_collision_resolved(state):
    # Resolve the only collision (ordinal 3 AT-T -> ATT) so no unresolved
    # collisions remain and the "Tab to view collisions" ghost disappears.
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


@when("the reviewer presses Tab", target_fixture="state")
def reviewer_presses_tab(state):
    return _dispatch_key(state, _TAB)


@when(parsers.parse('the reviewer types "{text}" into the filter'), target_fixture="state")
def reviewer_types(state, text):
    for ch in text:
        state = _dispatch_key(state, ch)
    return state


@when("the reviewer presses esc", target_fixture="state")
def reviewer_presses_esc(state):
    return _dispatch_key(state, _ESC)


@then(parsers.parse("the visible ordinals are {ordinals}"))
def visible_ordinals_are(state, ordinals):
    expected = [int(tok) for tok in ordinals.replace(",", " ").split()]
    assert [m.ordinal for m in select_visible_rows(state)] == expected


@then("all 11 rows are visible")
def all_rows_visible(state):
    assert [m.ordinal for m in select_visible_rows(state)] == list(range(1, 12))


@then(parsers.parse("the selected ordinal is {ordinal:d}"))
def selected_ordinal_is(state, ordinal):
    assert state.selection.selected_ordinal == ordinal


@then(parsers.parse('the filter prompt shows "{text}"'))
def filter_prompt_shows(state, text):
    assert state.filter.raw == text


@then("the filter prompt is empty")
def filter_prompt_empty(state):
    assert state.filter.raw == ""


@then("the collision metafilter is active")
def metafilter_active(state):
    assert state.filter.collision_only is True


@then("the collision metafilter is not active")
def metafilter_not_active(state):
    assert state.filter.collision_only is False
