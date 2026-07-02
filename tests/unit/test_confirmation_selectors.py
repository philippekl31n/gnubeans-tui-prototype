"""
TASK-009 — unit tests for the confirmation-mode selectors.

``select_confirmation_prompt`` and ``select_confirmation_header`` are pure
functions over frozen state that drive the CONFIRMING render (spec §6.4–6.5).
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from tests.fixtures.storyboard import make_config, make_mappings
from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.selectors import select_confirmation_prompt
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


def test_prompt_indicators_track_choice_for_exit_kind_too():
    state = _confirming(_base_state(), ConfirmationKind.EXIT, ConfirmationChoice.YES)
    content = select_confirmation_prompt(state)
    assert (content.yes_indicator, content.no_indicator) == ("Y", "n")
    assert content.yes_active is True


def test_prompt_returns_frozen_confirmation_prompt_content():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    content = select_confirmation_prompt(state)
    assert isinstance(content, ConfirmationPromptContent)
    with pytest.raises(FrozenInstanceError):
        content.prompt = "mutated"


def test_prompt_is_pure_and_leaves_state_unchanged():
    state = _confirming(_resolved_state(), ConfirmationKind.EXIT, ConfirmationChoice.YES)
    before = state
    select_confirmation_prompt(state)
    assert state is before
    assert state.confirmation.choice is ConfirmationChoice.YES
