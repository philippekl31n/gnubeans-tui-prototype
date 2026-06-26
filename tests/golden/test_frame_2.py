"""
TASK-003 — golden render test for frame 2 (Tab bang autocomplete).

From the initial browsing state (frame 1a) the reviewer presses Tab. The
``Tab to view collisions`` ghost is visible (empty filter with one unresolved
collision), so the bang autocompletes: ``filter.raw`` becomes ``"!"``,
``filter.cursor`` is 1, and ``collision_only`` derives True. Visible rows narrow
to the AT-T collision pair (ordinals 2 and 3) and selection clamps to row 2.

Geometry assertions use pyte ``screen.display``; reverse-video assertions use
pyte cell attributes, and raw ANSI inspection covers SGR 2 (dim) which pyte does
not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_2_screen):
    return frame_2_screen.display


# ── geometry ────────────────────────────────────────────────────────────────

def test_frame_ends_at_footer_with_no_trailing_padding(frame_2_lines):
    # Under-full frame (2 body rows): header, prompt, blank, table header,
    # 2 body rows, blank separator, footer = 8 lines, ending at the footer with
    # no blank padding below it (spec §6.1/§6.2).
    assert len(frame_2_lines) == 8
    assert "edit selected" in frame_2_lines[-1]
    assert "clear filter" in frame_2_lines[-1]


def test_header_still_reports_one_unresolved_collision(display):
    assert "1 unresolved collision" in display[0]


def test_prompt_shows_metafilter_only_ghost(display):
    # The literal `!` precedes the dim `Type to filter` ghost (spec §6.5).
    assert display[1].startswith("  Filter: !Type to filter")


def test_only_collision_rows_are_visible(display):
    body = [display[4], display[5]]
    ordinals = [line.split()[0] if line.split()[0] != "▸" else line.split()[1] for line in body]
    assert ordinals == ["2", "3"]
    # No further body rows below the collision pair.
    assert display[6].strip() == ""


def test_selected_row_clamps_to_first_collision_row(display):
    assert display[4].startswith("▸")
    assert not display[5].startswith("▸")


def test_both_collision_rows_keep_their_markers(display):
    assert "!" in display[4]
    assert "!" in display[5]


def test_footer_offers_clear_filter(display):
    assert "esc clear filter" in display[-1]


# ── style spans ───────────────────────────────────────────────────────────────

def test_metafilter_bang_is_literal_not_reverse_video(frame_2_screen):
    # "  Filter: " spans cols 0–9; the literal `!` sits at col 10 with no reverse.
    assert frame_2_screen.display[1][10] == "!"
    assert frame_2_screen.buffer[1][10].reverse is False


def test_ghost_caret_is_reverse_video_first_letter(frame_2_screen):
    # Only the `T` of the ghost (col 11) is the reverse-video caret.
    assert frame_2_screen.display[1][11] == "T"
    assert frame_2_screen.buffer[1][11].reverse is True
    assert frame_2_screen.buffer[1][12].reverse is False


def test_ghost_remainder_uses_dim(frame_2_lines):
    # pyte does not track SGR 2 (dim/faint); inspect raw ANSI output directly.
    assert "\x1b[2m" in frame_2_lines[1]


def test_header_shortcut_uses_dim(frame_2_lines):
    assert "\x1b[2m" in frame_2_lines[0]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_2_matches_snapshot(frame_2_screen, assert_snapshot):
    assert_snapshot(frame_2_screen, Path(__file__).parent / "snapshots" / "frame_2.txt")
