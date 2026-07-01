"""
TASK-006 — golden render test for frame 10 (invalid input, error icon/message).

Continuing from frame 9 (editing ordinal 1, "APPLE"), the reviewer types
"44PL". The buffer is not a prefix of the default "APPLE", so no ghost suffix
renders; the target policy rejects a leading digit ("must start with A-Z"), so
an error icon replaces the checkmark and the footer's ``type to edit`` hint is
displaced by the error message and the source-navigation/cancel hints only
(spec §7.5, FR19). Geometry uses pyte ``screen.display``; the reverse-video
cursor uses pyte cell attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_10_screen):
    return frame_10_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_fifteen_lines_ending_at_footer(frame_10_lines):
    assert len(frame_10_lines) == 15


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


# ── buffer, no ghost suffix, error icon (FR19) ───────────────────────────────

def test_buffer_shows_the_typed_invalid_value_with_no_ghost_suffix(display):
    assert display[4][7:11] == "44PL"
    assert display[4][11] == " "  # no ghost characters follow


def test_reverse_video_cursor_sits_past_the_last_buffer_character(frame_10_screen):
    assert frame_10_screen.buffer[4][11].reverse is True
    assert frame_10_screen.buffer[4][10].reverse is False


def test_error_icon_renders_in_place_of_the_checkmark(display):
    assert display[4][13] == "✗"
    assert "✓" not in display[4]


# ── footer: error message replaces the type-to-edit hint ────────────────────

def test_footer_shows_the_policy_error_message(display):
    footer = display[-1]
    assert "Error: must start with A-Z" in footer


def test_footer_omits_type_to_edit_and_submit_while_invalid(display):
    footer = display[-1]
    assert "type to edit" not in footer
    assert "submit" not in footer
    assert "select source" in footer
    assert "esc cancel" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_10_matches_snapshot(frame_10_screen, assert_snapshot):
    assert_snapshot(frame_10_screen, Path(__file__).parent / "snapshots" / "frame_10.txt")
