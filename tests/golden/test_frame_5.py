"""
TASK-006 — golden render test for frame 5 (valid buffer, checkmark, submit hint).

From frame 4 (empty ghost-only buffer on the AT-T collision row) the reviewer
types "ATT". The buffer no longer prefixes the default source value "AT-T", so
the ghost suffix disappears; the buffer is a concrete, valid value so the
reverse-video cursor sits past its last character and a checkmark icon renders;
the live collision markers on both the AT-T rows clear because "ATT" no longer
matches ordinal 2's committed "AT-T"; and the footer gains the submit
affordance (spec §7.5, FR17/FR18/FR22). Geometry uses pyte ``screen.display``;
the reverse-video cursor uses pyte cell attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_5_screen):
    return frame_5_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_nine_lines_ending_at_footer(frame_5_lines):
    assert len(frame_5_lines) == 9
    assert "↵ submit" in frame_5_lines[-1]


def test_header_still_reports_the_committed_collision(display):
    # The edit is still uncommitted, so the header's committed collision count
    # is unaffected by the live buffer (spec §3.2).
    assert "1 unresolved collision" in display[0]


# ── buffer, ghost suffix, and validation (FR17/FR18/FR22) ───────────────────

def test_buffer_shows_the_typed_value_with_no_ghost_suffix(display):
    # "ATT" is not a prefix of the default "AT-T" (diverges at index 2), so no
    # ghost suffix trails the buffer.
    assert display[5][7:10] == "ATT"
    assert display[5][10] == " "  # no ghost characters follow


def test_reverse_video_cursor_sits_past_the_last_buffer_character(frame_5_screen):
    assert frame_5_screen.buffer[5][10].reverse is True
    assert frame_5_screen.buffer[5][9].reverse is False


def test_checkmark_icon_renders_for_the_valid_concrete_buffer(display):
    assert display[5][12] == "✓"


def test_live_collision_markers_clear_on_both_at_t_rows(display):
    # ordinal 2 (context) and ordinal 3 (edit row) both lose the "!" marker
    # because the live "ATT" override no longer collides with ordinal 2's
    # committed "AT-T" (spec §3.2 live-collision preview).
    assert display[4][6] == " "
    assert display[5][6] == " "


# ── footer: submit affordance appears for a valid, changed, non-colliding edit ──

def test_footer_gains_the_submit_hint(display):
    footer = display[-1]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "↵ submit" in footer
    assert "esc cancel" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_5_matches_snapshot(frame_5_screen, assert_snapshot):
    assert_snapshot(frame_5_screen, Path(__file__).parent / "snapshots" / "frame_5.txt")
