"""
TASK-009 — golden render test for frame 15 (terminal accepted-result frame).

Confirming the accept with choice=YES commits all mappings and exits the TUI:
``result.status = ACCEPTED``. The render collapses to the two-row result frame
of the created message over a bare prompt glyph, with no rows below row 2 (spec
§6.7, storyboard frame 15).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_15_screen):
    return frame_15_screen.display


def test_frame_is_two_lines(frame_15_lines):
    assert len(frame_15_lines) == 2


def test_row_1_is_the_created_message(display):
    assert display[0].rstrip() == "11 commodities created."


def test_row_2_is_the_prompt_glyph(display):
    assert display[1].rstrip() == "❯"


def test_no_table_or_prompt_content_remains(frame_15_lines):
    joined = "\n".join(frame_15_lines)
    assert "Accept all?" not in joined
    assert "Beancount Token" not in joined


def test_frame_15_matches_snapshot(frame_15_screen, assert_snapshot):
    assert_snapshot(frame_15_screen, Path(__file__).parent / "snapshots" / "frame_15.txt")
