"""
TASK-010 — golden render test for the accepted terminal frame (spec §6.7).

Driven end-to-end through the reducer: with the AT-T collision resolved and the
non-matching ``12`` filter applied, ``ctrl+s`` re-enters the accept confirmation
(frame 14), ``y`` sets the choice to YES, and ``Enter`` commits every mapping,
marking ``result.status = ACCEPTED``. The render collapses to the two-row §6.7
result frame — the created message over a bare prompt glyph, with nothing below
row 2 (storyboard frame 15).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_accept_terminal_screen):
    return frame_accept_terminal_screen.display


# ── the accept flow reaches the ACCEPTED terminal state (spec §4.2) ──────────

def test_accept_flow_marks_the_run_accepted():
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, "2")
    state = reduce(state, KeyEvent.SUBMIT)
    state = reduce(state, "y")
    state = reduce(state, KeyEvent.ENTER)

    assert state.result.status == "ACCEPTED"
    # Every mapping is committed with its resolved target intact.
    assert next(m for m in state.mappings if m.ordinal == 3).target_value == "ATT"


# ── the §6.7 terminal frame geometry ─────────────────────────────────────────

def test_frame_is_two_lines(frame_accept_terminal_lines):
    assert len(frame_accept_terminal_lines) == 2


def test_row_1_is_the_created_message(display):
    assert display[0].rstrip() == "11 commodities created."


def test_row_2_is_the_prompt_glyph(display):
    assert display[1].rstrip() == "❯"


def test_no_table_or_prompt_content_remains(frame_accept_terminal_lines):
    joined = "\n".join(frame_accept_terminal_lines)
    assert "Accept all?" not in joined
    assert "Beancount Token" not in joined


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_accept_terminal_matches_snapshot(frame_accept_terminal_screen, assert_snapshot):
    assert_snapshot(
        frame_accept_terminal_screen,
        Path(__file__).parent / "snapshots" / "frame_accept_terminal.txt",
    )
