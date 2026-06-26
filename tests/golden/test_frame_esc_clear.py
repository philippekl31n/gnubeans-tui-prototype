"""
TASK-003 — golden render test for the Esc-clear frame.

Pressing Esc from a filtered browsing state clears ``filter.raw`` and resets the
cursor to 0, restoring every row. The resulting frame MUST be bit-identical to
frame 1a (spec §3.3 / §10.1 frame 2 row narrative; storyboard esc-clear).

Geometry assertions use pyte ``screen.display``; the bit-identity check compares
the raw rendered lines (ANSI included) against the frame 1a fixture.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_esc_clear_screen):
    return frame_esc_clear_screen.display


# ── identity with frame 1a ────────────────────────────────────────────────────

def test_rendered_lines_are_bit_identical_to_frame_1a(frame_esc_clear_lines, frame_1a_lines):
    # Including ANSI styling: clearing the filter restores the exact initial frame.
    assert frame_esc_clear_lines == frame_1a_lines


def test_frame_fills_the_15_row_terminal(frame_esc_clear_screen):
    # All 11 rows restored; the 9-row body fills the 15-row terminal exactly.
    assert frame_esc_clear_screen.lines == 15


# ── restored browsing state geometry ──────────────────────────────────────────

def test_filter_prompt_is_back_to_the_collision_ghost(display):
    assert display[1].startswith("  Filter: Tab to view collisions")


def test_selection_is_back_on_row_1(display):
    assert display[4].startswith("▸")


def test_collision_markers_are_restored_on_rows_2_and_3(display):
    assert "!" in display[5]
    assert "!" in display[6]


def test_footer_drops_the_clear_filter_hint(display):
    # With no active filter the footer omits "clear filter" (spec §6.6).
    assert "edit selected" in display[14]
    assert "clear filter" not in display[14]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_esc_clear_matches_snapshot(frame_esc_clear_screen, assert_snapshot):
    assert_snapshot(
        frame_esc_clear_screen, Path(__file__).parent / "snapshots" / "frame_esc_clear.txt"
    )
