"""
TASK-007 — golden render test for frame 12a (source pointer on the first
source, buffer autofilled, FR21).

Continuing from frame 9 (editing ordinal 1, "APPLE", buffer empty, focus on
the token input), the reviewer presses Down. Focus moves to the source list
at pointer index 0 (``cmdty_id: "AAPL"``); the buffer autofills from that
source's effective value ("AAPL") and validates as a concrete, non-ghost
value, so the checkmark renders. The row-cursor glyph (col 0 ``▸``) is
suppressed while focus is on the source list; the pointer glyph instead
renders in the source-pointer column, on the same physical row as the token
input for the first source (spec §7.4, §7.5). Geometry uses pyte
``screen.display``; the reverse-video cursor uses pyte cell attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_12a_screen):
    return frame_12a_screen.display


def test_frame_is_fifteen_lines_ending_at_footer(frame_12a_lines):
    assert len(frame_12a_lines) == 15


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


def test_token_row_has_no_row_cursor_glyph(display):
    assert display[4][0] == " "


def test_buffer_shows_the_first_sources_value(display):
    assert display[4][7:11] == "AAPL"
    assert display[4][11] == " "  # no ghost characters follow


def test_reverse_video_cursor_sits_past_the_last_buffer_character(frame_12a_screen):
    assert frame_12a_screen.buffer[4][11].reverse is True
    assert frame_12a_screen.buffer[4][10].reverse is False


def test_checkmark_renders_for_the_concrete_autofilled_value(display):
    assert display[4][13] == "✓"
    assert "✗" not in display[4]


def test_pointer_glyph_marks_the_first_source(display):
    assert display[4][32] == "▸"
    assert display[5][32] == " "


def test_second_source_row_has_no_pointer_glyph(display):
    assert '┃ user_symbol: "APPLE"' in display[5]


def test_footer_still_offers_submit(display):
    footer = display[-1]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "↵ submit" in footer
    assert "esc cancel" in footer


def test_frame_12a_matches_snapshot(frame_12a_screen, assert_snapshot):
    assert_snapshot(frame_12a_screen, Path(__file__).parent / "snapshots" / "frame_12a.txt")
