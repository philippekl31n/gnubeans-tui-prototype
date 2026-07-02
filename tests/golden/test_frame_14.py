"""
TASK-010 — golden render test for frame 14 (ctrl+s re-entry into accept).

From the frame 13 context (all collisions resolved, '12' filter matching no
rows) ctrl+s opens the accept confirmation: the zero-collision guard passes
regardless of the empty result (spec §3.4), and CONFIRMING windows the full
mapping list, so the frame is identical to frame 6.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_14_screen):
    return frame_14_screen.display


def test_frame_14_is_identical_to_frame_6(display, frame_6_screen):
    assert display == frame_6_screen.display


def test_full_table_renders_despite_the_no_match_filter(display):
    assert [row.split()[0] for row in display[4:13]] == [str(n) for n in range(1, 10)]


def test_frame_14_matches_snapshot(frame_14_screen, assert_snapshot):
    assert_snapshot(frame_14_screen, Path(__file__).parent / "snapshots" / "frame_14.txt")
