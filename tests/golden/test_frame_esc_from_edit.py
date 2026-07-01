"""
TASK-008 — golden render test for the Esc-from-edit frame (spec §4.2 / FR16).

From frame 12b (editing ordinal 1 with the buffer autofilled to ``APPLE`` via
source navigation) the reviewer presses Esc. Cancelling discards the edit buffer
and all source-navigation state, clears ``edit``, and returns to ``BROWSING``.
Because no editing transition ever mutates ``filter.*`` or the row selection, the
pre-edit browsing context is restored exactly: the frame is bit-identical to
frame 8 (the ``1`` text filter, the selection on ordinal 1, and the collision-free
dataset all intact). Geometry uses pyte ``screen.display``; the reverse-video
cursor uses pyte cell attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_esc_from_edit_screen):
    return frame_esc_from_edit_screen.display


# ── the cancelled edit restores the pre-edit browsing frame (frame 8) ────────

def test_cancel_restores_the_pre_edit_browsing_frame(
    frame_esc_from_edit_lines, frame_8_lines
):
    # Esc from the edit returns to exactly the browsing frame it began from: the
    # filter, the selection, and every row are identical to frame 8 (FR16).
    assert frame_esc_from_edit_lines == frame_8_lines


def test_mode_is_browsing_not_editing(display):
    # No editing prompt survives the cancel; the filter prompt is back.
    assert display[1].rstrip() == "  Filter: 1"
    assert "Editing mapping" not in display[1]


# ── filter intact ────────────────────────────────────────────────────────────

def test_filter_text_is_preserved(display):
    assert "Filter: 1" in display[1]


def test_filter_cursor_block_follows_the_preserved_character(frame_esc_from_edit_screen):
    # "  Filter: " is 10 chars (0–9); the "1" sits at index 10 and the reverse-
    # video cursor block trails it at index 11 (cursor == len(raw) == 1).
    assert frame_esc_from_edit_screen.buffer[1][10].reverse is False
    assert frame_esc_from_edit_screen.buffer[1][11].reverse is True


# ── selection intact on the row that was being edited ────────────────────────

def test_selection_is_restored_on_the_edited_row(display):
    assert display[4].startswith("▸")
    assert display[4].split()[1] == "1"


def test_only_the_filtered_rows_are_visible(display):
    body = [display[i] for i in range(4, 8)]
    assert body[0].split()[1] == "1"
    assert body[1].split()[0] == "4"
    assert body[2].split()[0] == "10"
    assert body[3].split()[0] == "11"


# ── the discarded buffer never touched the mapping ───────────────────────────

def test_edited_row_target_is_unchanged(display):
    # Ordinal 1 still shows its default APPLE; the cancelled APPLE buffer was
    # never committed and no literal target was written.
    assert display[4].split()[2] == "APPLE"


def test_footer_offers_clear_filter(display):
    assert "clear filter" in display[9]


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_esc_from_edit_matches_snapshot(frame_esc_from_edit_screen, assert_snapshot):
    assert_snapshot(
        frame_esc_from_edit_screen,
        Path(__file__).parent / "snapshots" / "frame_esc_from_edit.txt",
    )
