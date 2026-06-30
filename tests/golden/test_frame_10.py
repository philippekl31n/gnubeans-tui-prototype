"""
TASK-006 — golden render test for frame 10 (invalid typed buffer).

Typing ``4``, ``4``, ``P``, ``L`` inserts every character into the buffer
(``44PL``) even though it is invalid: the commodity policy reports
``must start with A-Z``, the ``✗`` icon renders two columns past the cursor
(FR19/§6.3), and the footer leads with the error and drops both the submit and
the ``type to edit`` hints (spec §6.6).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_10_screen):
    return frame_10_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_eleven_lines_ending_at_footer(frame_10_lines):
    assert len(frame_10_lines) == 11


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


# ── invalid printable characters are inserted (FR19) ─────────────────────────

def test_invalid_characters_are_inserted_into_the_buffer(display):
    assert display[4][7:11] == "44PL"


def test_no_ghost_text_when_buffer_deviates(display):
    # "44PL" is not a prefix of "APPLE", so no ghost trails the cursor block.
    assert display[4][11] == " "  # reverse-video cursor block (a space)


def test_invalid_icon_two_columns_right_of_the_cursor(display):
    # Cursor block at col 12; ✗ at cursor + 2 = col 14 (index 13).
    assert display[4][13] == "✗"
    assert "✓" not in display[4]


def test_reverse_video_cursor_block_after_buffer(frame_10_screen):
    assert frame_10_screen.buffer[4][11].reverse is True


# ── footer: error leads, submit gated (spec §6.6) ────────────────────────────

def test_footer_shows_policy_error_and_no_submit(display):
    footer = display[10]
    assert "Error: must start with A-Z" in footer
    assert "select source" in footer
    assert "esc cancel" in footer
    assert "submit" not in footer
    assert "type to edit" not in footer


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_10_matches_snapshot(frame_10_screen, assert_snapshot):
    assert_snapshot(frame_10_screen, Path(__file__).parent / "snapshots" / "frame_10.txt")
