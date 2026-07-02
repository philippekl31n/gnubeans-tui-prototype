"""
TASK-009 — unit tests for the confirmation-mode selectors.

``select_confirmation_prompt`` and ``select_confirmation_header`` are pure
functions over frozen state that drive the CONFIRMING render (spec §6.4–6.6).
``select_body_rows`` is asserted to ignore the active filter in CONFIRMING mode
(spec §8.2 / §10.1 frame 14).
"""
from dataclasses import replace

import pytest

from tests.fixtures.storyboard import make_config, make_mappings
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import (
    select_body_rows,
    select_confirmation_header,
    select_confirmation_prompt,
    select_visible_rows,
)
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    ConfirmationPromptContent,
    ConfirmationState,
    Mode,
)


def _base_state(frame_height: int = 15):
    return make_initial_state(make_config(), make_mappings(), frame_height=frame_height)


def _confirming(state, kind, choice):
    return replace(
        state,
        mode=Mode.CONFIRMING,
        confirmation=ConfirmationState(
            kind=kind,
            choice=choice,
            second_ctrl_c_armed=kind is ConfirmationKind.EXIT,
        ),
    )


def _resolved_state():
    """Base state with the AT-T collision resolved (ordinal 3 -> 'ATT')."""
    state = _base_state()
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


# ── select_confirmation_prompt ────────────────────────────────────────────────

def test_prompt_uses_accept_prompt_for_accept_kind():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    assert select_confirmation_prompt(state).prompt == "Accept all?"


def test_prompt_uses_exit_prompt_for_exit_kind():
    state = _confirming(_base_state(), ConfirmationKind.EXIT, ConfirmationChoice.NO)
    assert select_confirmation_prompt(state).prompt == "Skip adding commodities?"


def test_prompt_no_active_yields_lowercase_yes_uppercase_no():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    content = select_confirmation_prompt(state)
    assert content.yes_active is False
    assert content.yes_indicator == "y"
    assert content.no_indicator == "N"


def test_prompt_yes_active_yields_uppercase_yes_lowercase_no():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.YES)
    content = select_confirmation_prompt(state)
    assert content.yes_active is True
    assert content.yes_indicator == "Y"
    assert content.no_indicator == "n"


def test_prompt_returns_frozen_confirmation_prompt_content():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    content = select_confirmation_prompt(state)
    assert isinstance(content, ConfirmationPromptContent)
    with pytest.raises(Exception):
        content.prompt = "mutated"  # frozen dataclass


def test_prompt_is_pure_and_leaves_state_unchanged():
    state = _confirming(_resolved_state(), ConfirmationKind.EXIT, ConfirmationChoice.YES)
    before = state
    select_confirmation_prompt(state)
    assert state is before
    assert state.confirmation.choice is ConfirmationChoice.YES


# ── select_confirmation_header ────────────────────────────────────────────────

def test_header_accept_omits_collision_clause():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    assert (
        select_confirmation_header(state)
        == "❯ Reviewing 11 commodity mappings. ctrl+c cancel"
    )


def test_header_exit_keeps_collision_count_and_exit_shortcut():
    state = _confirming(_base_state(), ConfirmationKind.EXIT, ConfirmationChoice.NO)
    assert (
        select_confirmation_header(state)
        == "❯ Reviewing 11 commodity mappings. 1 unresolved collision. ctrl+c exit"
    )


def test_header_exit_with_zero_collisions_omits_collision_clause():
    state = _confirming(_resolved_state(), ConfirmationKind.EXIT, ConfirmationChoice.NO)
    assert (
        select_confirmation_header(state)
        == "❯ Reviewing 11 commodity mappings. ctrl+c exit"
    )


def test_header_pluralises_multiple_collisions():
    # Point ordinal 1 (APPLE) at MSFT so a second collision group appears
    # alongside the existing AT-T group: two unresolved collisions.
    state = _base_state()
    mappings = [
        replace(m, target_value="MSFT") if m.ordinal == 1 else m
        for m in state.mappings
    ]
    state = _confirming(
        replace(state, mappings=mappings),
        ConfirmationKind.EXIT,
        ConfirmationChoice.NO,
    )
    assert (
        select_confirmation_header(state)
        == "❯ Reviewing 11 commodity mappings. 2 unresolved collisions. ctrl+c exit"
    )


def test_header_returns_plain_text_without_ansi():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    assert "\x1b[" not in select_confirmation_header(state)


def test_header_is_pure_and_leaves_state_unchanged():
    state = _confirming(_base_state(), ConfirmationKind.EXIT, ConfirmationChoice.NO)
    before = state
    select_confirmation_header(state)
    assert state is before


# ── select_body_rows ignores the filter in CONFIRMING (spec §10.1 frame 14) ──

def test_body_rows_in_confirming_ignore_the_active_filter():
    state = _resolved_state()
    state = reduce(state, "1")
    state = reduce(state, "2")  # filter "12" matches no rows
    state = _confirming(state, ConfirmationKind.ACCEPT, ConfirmationChoice.NO)

    assert select_visible_rows(state) == []  # filter matches nothing
    assert [m.ordinal for m in select_body_rows(state)] == [1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_body_rows_in_browsing_still_respect_the_filter():
    state = _resolved_state()
    state = reduce(state, "1")
    state = reduce(state, "2")  # BROWSING with filter "12" -> no rows
    assert select_body_rows(state) == []


# ── the renderer never resets the choice on redraw (spec §4.1 / §10.2) ───────

def test_render_lines_is_idempotent_and_preserves_the_choice():
    from mapping_resolution_tui.renderer import render_lines

    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    first = render_lines(state)
    second = render_lines(state)
    assert first == second
    assert state.confirmation.choice is ConfirmationChoice.NO
