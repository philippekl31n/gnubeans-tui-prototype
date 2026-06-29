"""
TASK-004 — golden render test for frame 13 (empty-result state).

Over the collision-free dataset (ordinal 3 resolved to ``ATT``) the reviewer
types ``12``. No ordinal or target token contains ``12``, so ``visibleRows`` is
empty and ``selectedOrdinal`` is None. The body renders exactly one blank row
below the table header with no row cursor, and the footer becomes the error
variant ``Error: no matching rows  ·  esc clear filter`` (spec §3.4 / §6.1 /
§6.6; storyboard frame 13).

Geometry assertions use pyte ``screen.display``; raw ANSI inspection covers
SGR 2 (dim) which pyte does not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_13_screen):
    return frame_13_screen.display


# ── geometry ────────────────────────────────────────────────────────────────

def test_frame_ends_at_footer_with_no_trailing_padding(frame_13_lines):
    # Empty result: header, prompt, blank, table header, one blank body row,
    # blank separator, footer = 7 lines, ending at the footer on row 7 with no
    # filler rows below it (spec §6.1/§6.2; storyboard frame 13).
    assert len(frame_13_lines) == 7
    assert frame_13_lines[-1].strip().startswith("Error: no matching rows")


def test_header_is_collision_free(display):
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


def test_prompt_shows_the_non_matching_filter(display):
    assert display[1].startswith("  Filter: 12")


def test_single_blank_body_row_under_the_header(display):
    # Table header on row index 3; the empty-result body row (index 4) is blank
    # and the separator (index 5) is blank too.
    assert "Beancount Token" in display[3]
    assert display[4].strip() == ""
    assert display[5].strip() == ""


def test_no_row_cursor_is_rendered(display):
    # The blank body row carries no selection cursor glyph.
    assert "▸" not in "".join(display)


def test_error_footer_text(display):
    # pyte pads each display row to the full screen width; compare trimmed text.
    assert display[6].rstrip() == "  Error: no matching rows  ·  esc clear filter"


def test_footer_is_on_row_7(display):
    # Rows 8 onward are blank (the inline frame does not pad below the footer).
    assert "Error: no matching rows" in display[6]
    assert all(line.strip() == "" for line in display[7:])


def test_header_shortcut_uses_dim(frame_13_lines):
    # pyte does not track SGR 2 (dim/faint); inspect raw ANSI output directly.
    assert "\x1b[2m" in frame_13_lines[0]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_13_matches_snapshot(frame_13_screen, assert_snapshot):
    assert_snapshot(frame_13_screen, Path(__file__).parent / "snapshots" / "frame_13.txt")
