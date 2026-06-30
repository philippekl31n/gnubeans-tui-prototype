"""
TASK-006 — golden render test for frame 9 (editing APPLE with streaming ghost).

Pressing Enter on the filtered APPLE mapping (ordinal 1) over a collision-free
dataset enters EDITING with an empty buffer and the ghost suffix ``APPLE``. The
expanded edit block anchors the body high (spec §8.2): the token-input row shares
the first source ``cmdty_id: "AAPL"``, the second source ``user_symbol: "APPLE"``
takes the next row, and the trailing context rows 4/10/11 render super-dim.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_9_screen):
    return frame_9_screen.display


# ── geometry: two-source edit block + dim context ────────────────────────────

def test_frame_is_eleven_lines_ending_at_footer(frame_9_lines):
    # header, prompt, blank, table header, 2 edit rows, 3 context rows, blank,
    # footer.
    assert len(frame_9_lines) == 11


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


def test_header_is_collision_free(display):
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


# ── ghost text + reverse-video cursor (FR17) ─────────────────────────────────

def test_reverse_video_cursor_covers_the_first_ghost_character(frame_9_screen):
    assert frame_9_screen.display[4][7] == "A"
    assert frame_9_screen.buffer[4][7].reverse is True


def test_ghost_suffix_streams_the_full_default_value(display):
    # Empty buffer -> "APPLE" renders as ghost from the token-field start.
    assert display[4][7:12] == "APPLE"


def test_ghost_text_is_dim(frame_9_lines):
    assert "\x1b[2m" in frame_9_lines[4]


# ── expanded source rows (spec §7.4) ─────────────────────────────────────────

def test_first_source_shares_the_token_input_row(display):
    assert display[4].rstrip().endswith('┃ cmdty_id: "AAPL"')


def test_second_source_takes_its_own_row(display):
    assert display[5].rstrip().endswith('┃ user_symbol: "APPLE"')
    # No row cursor / ordinal on the continuation source row.
    assert display[5].strip().startswith("┃")


# ── super-dim surrounding rows ───────────────────────────────────────────────

def test_context_rows_are_present_and_super_dim(display, frame_9_lines):
    assert display[6].split()[0] == "4"
    assert display[7].split()[0] == "10"
    assert display[8].split()[0] == "11"
    for i in (6, 7, 8):
        assert frame_9_lines[i].startswith("\x1b[2m")


def test_footer_omits_submit_while_ghost_only(display):
    footer = display[10]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "esc cancel" in footer
    assert "submit" not in footer


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_9_matches_snapshot(frame_9_screen, assert_snapshot):
    assert_snapshot(frame_9_screen, Path(__file__).parent / "snapshots" / "frame_9.txt")
