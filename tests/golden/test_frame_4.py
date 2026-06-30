"""
TASK-006 — golden render test for frame 4 (entering edit mode, ghost text).

From the metafilter ``!3`` the reviewer backspaces, arrows down, and presses
Enter to edit the AT-T collision row (ordinal 3, ``target_value`` null). The
expanded edit block keeps the preceding AT-T collision row visible (super-dim)
above it, the empty buffer renders the ``AT-T`` default as ghost text with a
reverse-video cursor over the first ghost character, the inactive
``user_symbol: (not set)`` source shows below the divider, and the footer omits
the submit affordance while the buffer is still ghost-only (spec §6.6). Geometry
uses pyte ``screen.display``; the reverse-video cursor uses pyte cell attributes;
SGR 2 (dim) is checked in raw ANSI.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_4_screen):
    return frame_4_screen.display


# ── geometry: anchored two-source edit block with preceding context ──────────

def test_frame_is_nine_lines_ending_at_footer(frame_4_lines):
    # header, prompt, blank, table header, dim row 2, edit token row, second
    # source row, blank separator, footer.
    assert len(frame_4_lines) == 9


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "AT-T":'


def test_header_still_reports_the_committed_collision(display):
    # The header count reflects the committed mappings; the live buffer has not
    # yet been committed, so the AT-T collision still stands (spec §3.2).
    assert "1 unresolved collision" in display[0]


def test_preceding_collision_row_is_shown_super_dim(display, frame_4_lines):
    row = display[4]
    assert row.split()[0] == "2"
    assert row[6] == "!"  # live collision marker still set (buffer empty)
    assert not row.startswith("▸")  # context rows carry no row cursor
    assert frame_4_lines[4].startswith("\x1b[2m")


def test_edit_row_has_row_cursor_and_collision_marker(display):
    row = display[5]
    assert row.startswith("▸")
    assert row[6] == "!"  # collision marker column (5+W, 1-based 7)


# ── ghost text + reverse-video cursor (FR17) ─────────────────────────────────

def test_reverse_video_cursor_covers_the_first_ghost_character(frame_4_screen):
    # Empty buffer + null target -> the cursor covers the first ghost char "A"
    # at the token-field start (col 8, 1-based; index 7) on the edit token row.
    assert frame_4_screen.display[5][7] == "A"
    assert frame_4_screen.buffer[5][7].reverse is True


def test_ghost_suffix_renders_after_the_cursor(display):
    # The full default value "AT-T" shows as buffer-prefix ghost: cursor "A"
    # followed by "T-T".
    assert display[5][7:11] == "AT-T"


def test_ghost_text_is_dim(frame_4_lines):
    # pyte does not track SGR 2; inspect the raw edit row directly.
    assert "\x1b[2m" in frame_4_lines[5]


def test_no_validation_icon_for_ghost_only_buffer(display):
    # A ghost-only buffer carries no concrete value, so neither ✓ nor ✗ renders.
    assert "✓" not in display[5]
    assert "✗" not in display[5]


# ── expanded inactive source row (spec §2.3) ─────────────────────────────────

def test_inactive_user_symbol_source_renders_not_set(display):
    assert display[6].rstrip().endswith("┃ user_symbol: (not set)")
    assert display[6].strip().startswith("┃")  # continuation row, no ordinal


# ── footer: submit gated off while ghost-only (spec §6.6) ────────────────────

def test_footer_omits_submit_and_shows_no_error(display):
    footer = display[8]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "esc cancel" in footer
    assert "submit" not in footer
    assert "Error" not in footer


def test_footer_is_two_rows_below_the_edit_block(display):
    assert display[7].strip() == ""  # blank separator
    assert "type to edit" in display[8]


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_4_matches_snapshot(frame_4_screen, assert_snapshot):
    assert_snapshot(frame_4_screen, Path(__file__).parent / "snapshots" / "frame_4.txt")
