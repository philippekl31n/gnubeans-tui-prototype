"""
TASK-003 — golden render test for frame 2 (collision metafilter engaged).

Proves the Tab / ctrl+i bang autocomplete: from frame 1a a single Tab
autocompletes a leading ``!`` (``filter.raw='!'``, ``filter.cursor=1``,
collision-only derived), narrowing the list to the two collision rows 2 and 3
with the selection clamped onto row 2. Also proves the metafilter-only prompt
template (``!`` literal + dim ``Type to filter`` ghost with only ``T``
reverse-video) and the variable-height layout contract (the under-full 2-row
frame ends at the footer with no trailing blank padding). Geometry uses pyte
screen.display; style assertions use pyte cell attributes, with raw ANSI for the
dim ghost which pyte does not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_2_screen):
    return frame_2_screen.display  # list[str], 80 cols wide, pyte-rendered


# ── geometry: under-full variable-height frame ──────────────────────────────

def test_frame_is_exactly_8_lines_ending_at_footer(frame_2_lines):
    # header, prompt, blank, table header, 2 body rows, blank separator, footer.
    assert len(frame_2_lines) == 8


def test_frame_ends_at_footer_with_no_trailing_padding(display):
    assert "clear filter" in display[7]
    # there is no display row below the footer.
    assert len(display) == 8


# ── metafilter narrowing & selection clamp ──────────────────────────────────

def test_only_collision_rows_2_and_3_are_visible(display):
    body = [display[i] for i in range(4, 6)]
    assert body[0].split()[1] == "2"  # row 0 carries the "▸" selection cursor
    assert body[1].split()[0] == "3"


def test_selection_clamps_to_first_collision_row(display):
    # The metafilter hides row 1, so the cursor snaps to the first visible row 2.
    assert display[4].startswith("▸")
    assert not display[5].startswith("▸")


def test_both_visible_rows_have_collision_markers(display):
    assert "!" in display[4]
    assert "!" in display[5]


# ── metafilter-only prompt template (spec §6.5) ─────────────────────────────

def test_prompt_shows_the_metafilter_ghost(display):
    assert display[1].rstrip() == "  Filter: !Type to filter"


def test_bang_is_literal_and_only_ghost_T_is_reverse_video(frame_2_screen):
    # "  Filter: " is 10 chars (0–9); the literal "!" sits at index 10 (plain)
    # and the ghost "T" at index 11 carries the reverse-video caret.
    assert frame_2_screen.buffer[1][10].reverse is False  # the literal !
    assert frame_2_screen.buffer[1][11].reverse is True   # ghost "T" caret
    assert frame_2_screen.buffer[1][12].reverse is False  # "y" of the ghost


def test_prompt_ghost_remainder_is_dim(frame_2_lines):
    # pyte does not track SGR 2 (dim/faint); inspect the raw ANSI of the prompt.
    assert "\x1b[2m" in frame_2_lines[1]


# ── header / footer ──────────────────────────────────────────────────────────

def test_header_reports_the_unresolved_collision(display):
    assert "1 unresolved collision" in display[0]


def test_footer_offers_clear_filter(display):
    assert "esc" in display[7]
    assert "clear filter" in display[7]


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_2_matches_snapshot(frame_2_screen, assert_snapshot):
    assert_snapshot(frame_2_screen, Path(__file__).parent / "snapshots" / "frame_2.txt")
