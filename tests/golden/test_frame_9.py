"""
TASK-006 — golden render test for frame 9 (ghost suffix streaming, full body).

The reviewer selects the first row (ordinal 1, "APPLE", ``target_value`` null,
default source ``user_symbol``) and presses Enter. Unlike frame 4, this
mapping has no committed collision, so even though the buffer is empty and the
rendered value is entirely ghost text, the edit is submittable — the footer
gains the submit affordance because ``select_edit_is_submittable`` only checks
validation status, live collisions, and whether the concrete value differs
from the committed target, not whether the buffer itself is ghost-only (spec
§7.5, FR15/FR17/FR22). The anchor block sits at the very top of the visible
list, so the body fills entirely with "after" context rows (no "before" rows
are possible) up to the full 15-row terminal capacity. Geometry uses pyte
``screen.display``; the reverse-video cursor uses pyte cell attributes.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_9_screen):
    return frame_9_screen.display


# ── geometry: full-capacity anchored block with only trailing context ───────

def test_frame_is_fifteen_lines_ending_at_footer(frame_9_lines):
    # header, prompt, blank, table header, edit row, second source row, 7
    # trailing context rows (ordinals 2-8), blank separator, footer.
    assert len(frame_9_lines) == 15


def test_header_is_collision_free(display):
    # ordinal 3's collision was already resolved to "ATT" before this edit, and
    # ordinal 1 (being edited) has no committed collision of its own.
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


def test_editing_prompt_names_the_default_source_value(display):
    assert display[1].rstrip() == '  Editing mapping for "APPLE":'


def test_edit_row_has_row_cursor_and_no_collision_marker(display):
    row = display[4]
    assert row.startswith("▸")
    assert row[6] == " "


def test_trailing_context_rows_cover_ordinals_2_through_8(display):
    ordinals = [display[i].split()[0] for i in range(6, 13)]
    assert ordinals == ["2", "3", "4", "5", "6", "7", "8"]


def test_trailing_context_rows_are_super_dim(frame_9_lines):
    for i in range(6, 13):
        assert frame_9_lines[i].startswith("\x1b[2m")


# ── ghost text + reverse-video cursor (FR17) ─────────────────────────────────

def test_ghost_text_streams_the_full_default_value(display):
    assert display[4][7:12] == "APPLE"


def test_reverse_video_cursor_covers_the_first_ghost_character(frame_9_screen):
    assert frame_9_screen.buffer[4][7].reverse is True
    assert frame_9_screen.buffer[4][6].reverse is False


def test_ghost_characters_after_the_cursor_are_dim(frame_9_lines):
    row = frame_9_lines[4]
    assert "\x1b[2mP\x1b[0m\x1b[2mP\x1b[0m\x1b[2mL\x1b[0m\x1b[2mE\x1b[0m" in row


def test_no_validation_icon_renders_for_the_empty_buffer(display):
    # buffer_text is empty, so the renderer never shows a validation icon
    # regardless of the ghost default's own (VALID, no-icon) status.
    assert "✓" not in display[4]
    assert "✗" not in display[4]


# ── second source: active value, not the "(not set)" case ───────────────────

def test_second_source_row_shows_the_active_cmdty_id_value(display):
    assert '┃ cmdty_id: "AAPL"' in display[4]
    assert display[5].strip() == '┃ user_symbol: "APPLE"'


# ── footer: submit is offered for a ghost-only, non-colliding edit ──────────

def test_footer_gains_the_submit_hint(display):
    footer = display[-1]
    assert "type to edit" in footer
    assert "select source" in footer
    assert "↵ submit" in footer
    assert "esc cancel" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_9_matches_snapshot(frame_9_screen, assert_snapshot):
    assert_snapshot(frame_9_screen, Path(__file__).parent / "snapshots" / "frame_9.txt")
