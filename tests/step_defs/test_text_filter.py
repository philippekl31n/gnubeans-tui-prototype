"""
Step definitions for the text-filter BDD scenarios (TASK-002).

Steps drive the loop's input layer end to end: each typed character / named key
is normalised and mapped to an action exactly as the live loop does, then the
action is dispatched through ``reduce``. The resulting state is rendered with
``render_lines`` so highlight assertions inspect real frame output.
"""
from pytest_bdd import given, when, then, parsers, scenarios

from mapping_resolution_tui.loop import key_to_action, normalise_key
from mapping_resolution_tui.reducer import reduce
from mapping_resolution_tui.renderer import render_lines
from mapping_resolution_tui.selectors import select_visible_rows
from tests.conftest import make_pyte_screen

scenarios("../features/text_filter.feature")


def _dispatch_key(state, key):
    action = key_to_action(normalise_key(key))
    if action is None:
        return state
    return reduce(state, action)


@given("the storyboard fixture is loaded in a 15-row terminal", target_fixture="state")
def storyboard_loaded(initial_state):
    return initial_state


@when(parsers.parse('the reviewer types "{text}" into the filter'), target_fixture="state")
def reviewer_types(state, text):
    for ch in text:
        state = _dispatch_key(state, ch)
    return state


@when("the reviewer presses backspace", target_fixture="state")
def reviewer_backspaces(state):
    return _dispatch_key(state, "backspace")


@when("the reviewer presses esc", target_fixture="state")
def reviewer_presses_esc(state):
    return _dispatch_key(state, "esc")


@then(parsers.parse("the visible ordinals are {ordinals}"))
def visible_ordinals_are(state, ordinals):
    expected = [int(tok) for tok in ordinals.replace(",", " ").split()]
    assert [m.ordinal for m in select_visible_rows(state)] == expected


@then("all 11 rows are visible")
def all_rows_visible(state):
    assert [m.ordinal for m in select_visible_rows(state)] == list(range(1, 12))


@then("no rows are visible")
def no_rows_visible(state):
    assert select_visible_rows(state) == []


@then(parsers.parse('the filter prompt shows "{text}"'))
def filter_prompt_shows(state, text):
    assert state.filter.raw == text


@then("the filter prompt is empty")
def filter_prompt_empty(state):
    assert state.filter.raw == ""


@then(parsers.parse('the ordinal digit "{digit}" is bold on the first visible row'))
def ordinal_digit_bold(state, digit):
    screen = make_pyte_screen(render_lines(state))
    row = 4  # first body row (header, prompt, blank, table header, then rows)
    bold = "".join(ch for c, ch in enumerate(screen.display[row]) if screen.buffer[row][c].bold)
    assert bold == digit


@then(parsers.parse('the "{digit}" inside the C100-F token is bold'))
def token_digit_bold(state, digit):
    screen = make_pyte_screen(render_lines(state))
    # locate the row whose display contains the C100-F token
    row = next(r for r in range(4, len(screen.display)) if "C100-F" in screen.display[r])
    bold = "".join(ch for c, ch in enumerate(screen.display[row]) if screen.buffer[row][c].bold)
    assert digit in bold
