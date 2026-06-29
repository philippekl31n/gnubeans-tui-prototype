"""
TASK-003 — golden render test for frame esc-clear (Esc restores every row).

Proves that pressing Esc from a filtered BROWSING state clears ``filter.raw``
and resets ``filter.cursor`` to 0, restoring the full list. The rendered frame
is byte-identical to frame 1a — same 15-line geometry, the ``Tab to view
collisions`` ghost, row 1 selected — which this test pins by comparing against
the frame_1a snapshot directly.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_esc_clear_screen):
    return frame_esc_clear_screen.display  # list[str], 80 cols wide, pyte-rendered


def test_restored_list_pages_from_row_1(display):
    # The cleared filter restores all 11 rows; the first page renders ordinals
    # 1..9 (body capacity = height 15 - 6), exactly as frame 1a does.
    body = [display[i] for i in range(4, 13)]
    ordinals = [line.split()[1 if line.startswith("▸") else 0] for line in body]
    assert ordinals == [str(n) for n in range(1, 10)]


def test_filter_prompt_returns_to_the_ghost(display):
    assert display[1].rstrip() == "  Filter: Tab to view collisions"


def test_selection_returns_to_row_1(display):
    assert display[4].startswith("▸")


def test_footer_drops_the_clear_filter_hint(display):
    # With the filter cleared there is nothing to clear, so the hint is gone.
    assert "clear filter" not in display[14]


def test_frame_esc_clear_is_identical_to_frame_1a(frame_esc_clear_lines, frame_1a_lines):
    # Pins the AC "output identical to frame_1a": the rendered lines (ANSI and
    # all) must match the initial browsing frame exactly, so the dedicated
    # snapshot below can never silently drift from frame_1a.
    assert frame_esc_clear_lines == frame_1a_lines


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_esc_clear_matches_snapshot(frame_esc_clear_screen, assert_snapshot):
    assert_snapshot(
        frame_esc_clear_screen, Path(__file__).parent / "snapshots" / "frame_esc_clear.txt"
    )
