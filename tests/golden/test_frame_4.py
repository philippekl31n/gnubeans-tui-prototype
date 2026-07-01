"""
TASK-006 — golden render test for frame 4 (entering edit mode, ghost text).

From the metafilter ``!3`` (frame 3) the reviewer arrows down to the AT-T
collision row (ordinal 3, ``target_value`` null) and presses Enter. The
expanded edit block keeps the preceding AT-T collision row visible (super-dim)
above it, the empty buffer renders the ``AT-T`` default source value as ghost
text with a reverse-video cursor over its first character, the inactive
``user_symbol: (not set)`` source shows below the divider, and the footer omits
the submit affordance because the buffer's ghost-default value ("AT-T") still
collides with ordinal 2's committed value — not because the buffer is
ghost-only per se; frame 9 shows a ghost-only buffer *is* submittable once it
doesn't collide (spec §6.6 / §7.5, FR15/FR17). Geometry uses pyte
``screen.display``; the reverse-video cursor uses pyte cell attributes; SGR 2
(dim) is checked in raw ANSI since pyte does not track it.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_4_screen):
    return frame_4_screen.display


# ── geometry: anchored two-source edit block with preceding context ──────────

def test_frame_is_nine_lines_ending_at_footer(frame_4_lines):
    # header, prompt, blank, table header, dim context row, edit token row,
    # second source row, blank separator, footer.
    assert len(frame_4_lines) == 9
    assert "esc cancel" in frame_4_lines[-1]


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "AT-T":'


def test_header_still_reports_the_committed_collision(display):
    # The live buffer is still empty (ghost-only), so the header's committed
    # collision count is unaffected (spec §3.2).
    assert "1 unresolved collision" in display[0]


def test_preceding_collision_row_is_shown_super_dim(display, frame_4_lines):
    row = display[4]
    assert row.split()[0] == "2"
    assert row[6] == "!"  # committed collision marker column (6+W, 0-based)
    assert not row.startswith("▸")  # context rows carry no row cursor
    assert frame_4_lines[4].startswith("\x1b[2m")


def test_edit_row_has_row_cursor_and_collision_marker(display):
    row = display[5]
    assert row.startswith("▸")
    assert row[6] == "!"  # live marker still set — buffer is empty (no override)


def test_second_source_row_shows_inactive_user_symbol(display):
    row = display[6]
    assert row.strip() == '┃ user_symbol: (not set)'


# ── ghost text + reverse-video cursor (FR17) ─────────────────────────────────

def test_ghost_text_streams_the_full_default_value(display):
    # Empty buffer -> the whole default source value "AT-T" renders as ghost.
    assert display[5][7:11] == "AT-T"


def test_reverse_video_cursor_covers_the_first_ghost_character(frame_4_screen):
    # Empty buffer + null target -> the cursor covers the first ghost char "A"
    # at the token-field start (col 7, 0-based) on the edit token row.
    assert frame_4_screen.buffer[5][7].reverse is True
    assert frame_4_screen.buffer[5][6].reverse is False


def test_ghost_characters_after_the_cursor_are_dim(frame_4_lines):
    row = frame_4_lines[5]
    assert "\x1b[2mT\x1b[0m\x1b[2m-\x1b[0m\x1b[2mT\x1b[0m" in row


def test_first_source_is_shown_after_the_divider(display):
    assert '┃ cmdty_id: "AT-T"' in display[5]


# ── footer: no submit affordance while the ghost default still collides ──────

def test_footer_offers_type_and_select_source_but_not_submit(display):
    footer = display[-1]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "esc cancel" in footer
    assert "submit" not in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_4_matches_snapshot(frame_4_screen, assert_snapshot):
    assert_snapshot(frame_4_screen, Path(__file__).parent / "snapshots" / "frame_4.txt")
