"""
TASK-008 — golden render test for frame_submit_no_resolution.

From the initial browsing state (AT-T collision outstanding, empty filter) the
reviewer edits ordinal 1 (APPLE), types "APPL", and submits with Enter. The
commit writes the buffer literally to row 1's target token (FR22), the app
returns to BROWSING with the empty filter intact (FR16), and the collision
indicators are recalculated: the AT-T pair on rows 2 and 3 still renders ``!``
and the header still reports one unresolved collision (FR8).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_submit_no_resolution_screen):
    return frame_submit_no_resolution_screen.display


# ── FR22: the committed token renders on the edited row ──────────────────────

def test_row_1_shows_the_committed_target_token(display):
    assert "APPL " in display[4]  # committed value, no trailing E
    assert "APPLE" not in display[4].split('"')[0]  # token cell updated…
    assert 'user_symbol: "APPLE"' in display[4]  # …while the source is untouched


def test_app_returned_to_browsing_with_the_selection_on_the_edited_row(display):
    assert display[4].startswith("▸")
    assert "type to edit" not in display[-1]  # no edit footer


# ── FR8: collision indicators recalculated after the commit ──────────────────

def test_the_unresolved_at_t_collision_markers_remain(display):
    assert display[5][6] == "!"  # ordinal 2
    assert display[6][6] == "!"  # ordinal 3


def test_header_still_reports_the_outstanding_collision(display):
    assert "1 unresolved collision" in display[0]


# ── FR16: the empty filter is preserved, ghost hint intact ───────────────────

def test_filter_line_returns_to_the_collision_ghost(display):
    assert "Filter: Tab to view collisions" in display[1]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_submit_no_resolution_matches_snapshot(
    frame_submit_no_resolution_screen, assert_snapshot
):
    assert_snapshot(
        frame_submit_no_resolution_screen,
        Path(__file__).parent / "snapshots" / "frame_submit_no_resolution.txt",
    )
