"""
TASK-006 — golden render test for frame 5 (valid typed buffer, submit offered).

Typing ``A``, ``T``, ``T`` over the ghost ``AT-T`` produces buffer ``ATT``: the
third character deviates from the default-source prefix, so the ghost disappears
(FR17), the policy validates the concrete buffer as ``VALID`` with a ``✓`` icon
two columns past the cursor (FR18/§6.3), the live collision recompute drops the
``!`` from the edited row, and the footer gains the submit hint (spec §6.6).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_5_screen):
    return frame_5_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_seven_lines_ending_at_footer(frame_5_lines):
    assert len(frame_5_lines) == 7


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "AT-T":'


# ── typed buffer, ghost gone, valid icon ─────────────────────────────────────

def test_buffer_renders_without_ghost(display):
    # "ATT" occupies the token field start (cols 8..10, 1-based); no ghost trails.
    assert display[4][7:10] == "ATT"


def test_reverse_video_cursor_is_a_block_after_the_buffer(frame_5_screen):
    # Cursor at the buffer end with no ghost -> a reverse-video space at col 11.
    assert frame_5_screen.display[4][10] == " "
    assert frame_5_screen.buffer[4][10].reverse is True


def test_valid_icon_two_columns_right_of_the_cursor(display):
    # ✓ renders at cursor + 2: cursor at col 11, icon at col 13 (index 12).
    assert display[4][12] == "✓"
    assert "✗" not in display[4]


def test_live_collision_marker_cleared_on_edited_row(display):
    # "ATT" no longer equals "AT-T", so the edited row drops its collision marker.
    assert display[4][6] == " "


# ── footer: submit offered once valid (spec §6.6) ────────────────────────────

def test_footer_includes_submit(display):
    footer = display[6]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "↵ submit" in footer
    assert "esc cancel" in footer
    assert "Error" not in footer


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_5_matches_snapshot(frame_5_screen, assert_snapshot):
    assert_snapshot(frame_5_screen, Path(__file__).parent / "snapshots" / "frame_5.txt")
