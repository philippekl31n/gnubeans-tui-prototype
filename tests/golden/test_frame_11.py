"""
TASK-006 — golden render test for frame 11 (max-length flash, FR20).

Continuing from frame 10, the reviewer fills the buffer to the 24-character
cap ("44PL56789012345678901234") and types a 25th character. The over-limit
character is discarded (buffer/cursor stay at 24), ``edit.max_length_flash_until``
arms (asserted directly in ``tests/unit/test_reducer_edit.py``), and the error
message becomes "24 chars max". Because the buffer is exactly
``max_token_length`` long with no ghost suffix, the reverse-video cursor pins
to the last character instead of appending an extra cursor column past the
end (spec §7.6). This frame only covers the immediate post-discard render —
the transient "pop-then-hold" flash styling itself (reverse-video burst before
reverting to the steady error) is TASK-009 scope, not asserted here. Geometry
uses pyte ``screen.display``; the reverse-video cursor uses pyte cell
attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_11_screen):
    return frame_11_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_fifteen_lines_ending_at_footer(frame_11_lines):
    assert len(frame_11_lines) == 15


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


# ── buffer pinned at the 24-character cap (spec §7.6) ────────────────────────

def test_buffer_holds_exactly_the_24_character_cap(display):
    assert display[4][7:31] == "44PL56789012345678901234"
    assert len("44PL56789012345678901234") == 24


def test_the_25th_character_was_discarded(display):
    # A trailing "5" would appear at column 31 if the over-limit char had been
    # accepted; instead the icon starts there.
    assert display[4][31] != "5"


def test_reverse_video_cursor_pins_to_the_last_character_not_past_it(frame_11_screen):
    # Buffer length == max_token_length with no ghost, so the cursor covers the
    # last buffer character (col 30, 0-based) rather than an appended column.
    assert frame_11_screen.buffer[4][30].reverse is True
    assert frame_11_screen.buffer[4][31].reverse is False


def test_error_icon_renders_immediately_after_the_pinned_cursor(display):
    assert display[4][32] == "✗"


# ── footer: over-limit error message ─────────────────────────────────────────

def test_footer_shows_the_24_chars_max_error(display):
    footer = display[-1]
    assert "Error: 24 chars max" in footer


def test_footer_omits_type_to_edit_and_submit_while_over_limit(display):
    footer = display[-1]
    assert "type to edit" not in footer
    assert "submit" not in footer
    assert "select source" in footer
    assert "esc cancel" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_11_matches_snapshot(frame_11_screen, assert_snapshot):
    assert_snapshot(frame_11_screen, Path(__file__).parent / "snapshots" / "frame_11.txt")
