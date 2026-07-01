"""
TASK-009 — golden render test for frame 11, burst phase (FR20, spec §7.6).

The max-length flash is a two-phase "pop-then-hold" micro-animation. This frame
is the same over-limit state as frame 11 rendered mid-burst (before the 150ms
deadline): the capped ``✗`` icon and the footer ``Error: 24 chars max`` line
render reverse-video, drawing the eye to the moment of rejection. Once the
deadline passes the frame reverts to the held style asserted by frame 11.

Geometry is identical to frame 11 — reverse-video is an attribute, not a glyph —
so the plain-text snapshot matches; the burst is asserted via pyte cell reverse
attributes against an injected deterministic render clock (no real sleep).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_11_burst_screen):
    return frame_11_burst_screen.display


# ── geometry is identical to the held frame; only styling differs ─────────────

def test_geometry_matches_the_held_frame(frame_11_burst_lines, frame_11_lines):
    from mapping_resolution_tui.renderer import strip_ansi

    assert [strip_ansi(line) for line in frame_11_burst_lines] == [
        strip_ansi(line) for line in frame_11_lines
    ]


def test_frame_is_eleven_lines_ending_at_footer(frame_11_burst_lines):
    assert len(frame_11_burst_lines) == 11


# ── burst styling (reverse-video icon + footer error) ─────────────────────────

def test_capped_icon_is_reverse_video(frame_11_burst_screen):
    # The capped ✗ sits at the token-field end + 2 = col 33 (index 32, spec §6.3).
    assert frame_11_burst_screen.display[4][32] == "✗"
    assert frame_11_burst_screen.buffer[4][32].reverse is True


def test_footer_error_line_is_reverse_video(frame_11_burst_screen):
    footer = frame_11_burst_screen.display[10]
    assert "Error: 24 chars max" in footer
    start = footer.index("Error:")
    message = "Error: 24 chars max"
    assert all(
        frame_11_burst_screen.buffer[10][start + k].reverse
        for k in range(len(message))
    )
    assert "submit" not in footer


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_11_burst_matches_snapshot(frame_11_burst_screen, assert_snapshot):
    assert_snapshot(
        frame_11_burst_screen,
        Path(__file__).parent / "snapshots" / "frame_11_burst.txt",
    )
