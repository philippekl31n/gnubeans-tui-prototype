"""
TASK-007 — golden render test for frame 12a (source pointer on the first source).

From the empty-buffer edit on the APPLE mapping (frame 9) the reviewer presses
``↓``: focus moves to the source list, the pointer rests on the first active
source ``cmdty_id: "AAPL"``, and the buffer autofills to ``AAPL``. ``AAPL`` is a
valid commodity token, so the ``✓`` icon renders; the row cursor ``▸`` is
suppressed and the source pointer ``▸`` appears in the source column (spec §7.4 /
§6.3 / FR21).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_12a_screen):
    return frame_12a_screen.display


# ── geometry: two-source edit block + dim context ────────────────────────────

def test_frame_is_eleven_lines_ending_at_footer(frame_12a_lines):
    assert len(frame_12a_lines) == 11


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


def test_header_is_collision_free(display):
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


# ── autofilled buffer + validation (FR21) ────────────────────────────────────

def test_buffer_autofilled_from_first_source(display):
    # First active source cmdty_id: "AAPL" -> buffer "AAPL" at the token field.
    assert display[4][7:11] == "AAPL"


def test_valid_icon_two_columns_right_of_the_cursor(display):
    # Cursor block at col 11; ✓ at cursor + 2 = col 13.
    assert display[4][13] == "✓"
    assert "✗" not in display[4]


def test_reverse_video_cursor_block_after_buffer(frame_12a_screen):
    assert frame_12a_screen.buffer[4][11].reverse is True


# ── source pointer (spec §7.4 / §6.3) ────────────────────────────────────────

def test_source_pointer_marks_the_first_source(display):
    # ▸ sits in the source-pointer column (7+W+M = 33, index 32) on the shared
    # token-input row, next to the first source.
    assert display[4][32] == "▸"
    assert display[4].rstrip().endswith('┃ cmdty_id: "AAPL"')


def test_second_source_has_no_pointer(display):
    assert display[5][32] != "▸"
    assert display[5].rstrip().endswith('┃ user_symbol: "APPLE"')


def test_row_cursor_is_suppressed_while_in_source_list(display):
    # The ▸ row cursor is not drawn in column 1 while focus is the source list.
    assert display[4][0] == " "


# ── super-dim surrounding rows ───────────────────────────────────────────────

def test_context_rows_are_present_and_super_dim(display, frame_12a_lines):
    assert display[6].split()[0] == "4"
    assert display[7].split()[0] == "10"
    assert display[8].split()[0] == "11"
    for i in (6, 7, 8):
        assert frame_12a_lines[i].startswith("\x1b[2m")


def test_footer_offers_submit_for_the_valid_autofill(display):
    footer = display[10]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "submit" in footer
    assert "esc cancel" in footer


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_12a_matches_snapshot(frame_12a_screen, assert_snapshot):
    assert_snapshot(frame_12a_screen, Path(__file__).parent / "snapshots" / "frame_12a.txt")
