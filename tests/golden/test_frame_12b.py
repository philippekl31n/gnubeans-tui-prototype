"""
TASK-007 — golden render test for frame 12b (source pointer on the second
source, buffer updated to match, FR21).

Continuing from frame 9, the reviewer presses Up instead of Down: entering
SOURCE_LIST from TOKEN_INPUT via Up jumps straight to the last active source
(index 1, ``user_symbol: "APPLE"``); the buffer autofills from that source's
effective value ("APPLE") and re-validates, keeping the checkmark. Geometry
uses pyte ``screen.display``; the reverse-video cursor uses pyte cell
attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_12b_screen):
    return frame_12b_screen.display


def test_frame_is_fifteen_lines_ending_at_footer(frame_12b_lines):
    assert len(frame_12b_lines) == 15


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


def test_token_row_has_no_row_cursor_glyph(display):
    assert display[4][0] == " "


def test_buffer_shows_the_second_sources_value(display):
    assert display[4][7:12] == "APPLE"
    assert display[4][12] == " "  # no ghost characters follow


def test_reverse_video_cursor_sits_past_the_last_buffer_character(frame_12b_screen):
    assert frame_12b_screen.buffer[4][12].reverse is True
    assert frame_12b_screen.buffer[4][11].reverse is False


def test_checkmark_renders_for_the_concrete_autofilled_value(display):
    assert display[4][14] == "✓"
    assert "✗" not in display[4]


def test_pointer_glyph_moved_to_the_second_source(display):
    assert display[4][32] == " "
    assert display[5][32] == "▸"


def test_first_source_row_shows_the_active_cmdty_id_value(display):
    assert '┃ cmdty_id: "AAPL"' in display[4]


def test_footer_still_offers_submit(display):
    footer = display[-1]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "↵ submit" in footer
    assert "esc cancel" in footer


def test_frame_12b_matches_snapshot(frame_12b_screen, assert_snapshot):
    assert_snapshot(frame_12b_screen, Path(__file__).parent / "snapshots" / "frame_12b.txt")
