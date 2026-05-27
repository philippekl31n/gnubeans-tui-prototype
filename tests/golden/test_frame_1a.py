"""
Story 1.5 — golden render test for frame 1a (initial browsing state).
Geometry assertions use pyte screen.display; style assertions use pyte cell
attributes where possible, and raw ANSI inspection for SGR 2 (dim) which
pyte does not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_1a_screen):
    return frame_1a_screen.display  # list[str], 80 cols wide, pyte-rendered


# ── AC5: geometry ─────────────────────────────────────────────────────────────

def test_frame_is_exactly_15_lines(frame_1a_screen):
    assert frame_1a_screen.lines == 15


def test_header_row_contains_unresolved_collision_count(display):
    assert "1 unresolved collision" in display[0]


def test_header_row_contains_review_count(display):
    assert "11" in display[0]


def test_row_1_has_selection_cursor(display):
    # display position 1 is frame line index 4 (header+prompt+blank+table_header)
    assert display[4].startswith("▸")


def test_rows_2_and_3_have_collision_markers(display):
    assert "!" in display[5]
    assert "!" in display[6]


def test_rows_without_collision_have_no_marker(display):
    # ordinal 1 (display pos 1, index 4) has no collision
    assert "!" not in display[4]


def test_footer_is_on_row_15(display):
    assert "edit selected" in display[14]
    assert "pageup" in display[14] or "page" in display[14].lower()


def test_row_14_is_blank_separator(display):
    assert display[13].strip() == ""


def test_row_3_is_blank(display):
    assert display[2].strip() == ""


def test_table_header_row_contains_column_labels(display):
    assert "Beancount Token" in display[3]
    assert "GnuCash Source" in display[3]


# ── AC6: style spans ──────────────────────────────────────────────────────────

def test_header_prompt_glyph_is_bold(frame_1a_screen):
    assert frame_1a_screen.buffer[0][0].bold is True


def test_filter_hint_first_char_is_reverse_video(frame_1a_screen):
    # "  Filter: " is 10 chars (indices 0–9); index 10 is the first hint char wrapped in _REV
    assert frame_1a_screen.buffer[1][10].reverse is True


def test_header_shortcut_uses_dim_for_ctrl_c_cancel(frame_1a_lines):
    # pyte does not track SGR 2 (dim/faint), so this inspects raw ANSI output directly.
    assert "\x1b[2m" in frame_1a_lines[0]


# ── AC7: snapshot ─────────────────────────────────────────────────────────────

def test_frame_1a_matches_snapshot(frame_1a_screen, assert_snapshot):
    assert_snapshot(frame_1a_screen, Path(__file__).parent / "snapshots" / "frame_1a.txt")
