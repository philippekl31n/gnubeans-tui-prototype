"""
TASK-010 — golden render test for the accept terminal frame (storyboard 15).

Enter on YES in the accept confirmation marks the run ACCEPTED and the render
collapses to the two-row §6.7 terminal result frame: the created message over
a bare prompt glyph, with nothing below row 2.
"""
from pathlib import Path


def test_terminal_frame_is_exactly_two_rows(frame_accept_terminal_lines):
    assert frame_accept_terminal_lines == ["11 commodities created.", "❯"]


def test_frame_accept_terminal_matches_snapshot(frame_accept_terminal_screen, assert_snapshot):
    assert_snapshot(
        frame_accept_terminal_screen,
        Path(__file__).parent / "snapshots" / "frame_accept_terminal.txt",
    )
