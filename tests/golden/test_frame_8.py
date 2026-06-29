"""
TASK-002 — golden render test for frame 8 (text filter "1" active).

Proves single-character text input, row narrowing to ordinals 1/4/10/11, bold
match-highlight metadata on the ordinal display and target token cells, the
filter cursor block, and the variable-height layout contract (the under-full
4-row frame ends at the footer with no trailing blank padding). The frame is
taken over a collision-free dataset (the AT-T collision on ordinal 3 is resolved
before the filter is typed, per the storyboard), so the header shows the
collision-free submit affordance. Geometry uses pyte screen.display; style
assertions use pyte cell attributes.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_8_screen):
    return frame_8_screen.display  # list[str], 80 cols wide, pyte-rendered


def bold_text(screen, row):
    """The concatenation of the bold-attributed characters on a display row."""
    line = screen.display[row]
    return "".join(
        ch for col, ch in enumerate(line) if screen.buffer[row][col].bold
    )


# ── geometry: under-full variable-height frame ──────────────────────────────

def test_frame_is_exactly_10_lines_ending_at_footer(frame_8_lines):
    # header, prompt, blank, table header, 4 body rows, blank separator, footer.
    assert len(frame_8_lines) == 10


def test_frame_ends_at_footer_with_no_trailing_padding(display):
    assert "clear filter" in display[9]
    # there is no display row below the footer.
    assert len(display) == 10


def test_only_ordinals_1_4_10_11_are_visible(display):
    body = [display[i] for i in range(4, 8)]
    # the ordinal is the first whitespace-separated token after the row cursor
    assert body[0].split()[1] == "1"  # row 0 carries the "▸" selection cursor
    assert body[1].split()[0] == "4"
    assert body[2].split()[0] == "10"
    assert body[3].split()[0] == "11"


def test_row_4_shows_the_c100_f_token(display):
    assert "C100-F" in display[5]


# ── selection & filter prompt ────────────────────────────────────────────────

def test_first_visible_row_has_selection_cursor(display):
    assert display[4].startswith("▸")


def test_filter_prompt_shows_the_typed_text(display):
    assert "Filter: 1" in display[1]


def test_filter_cursor_block_follows_the_typed_character(frame_8_screen):
    # "  Filter: " is 10 chars (0–9); the "1" sits at index 10 and the reverse-
    # video cursor block sits at index 11 (cursor == len(raw)).
    assert frame_8_screen.buffer[1][10].reverse is False
    assert frame_8_screen.buffer[1][11].reverse is True


# ── header / footer ──────────────────────────────────────────────────────────

def test_header_is_collision_free(display):
    # frame_8 is taken over a collision-free dataset (the storyboard resolves the
    # AT-T collision before this frame), so the header shows the collision-free
    # submit affordance and never reports an unresolved collision (spec §3.2).
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


def test_footer_offers_clear_filter_while_filtering(display):
    assert "esc" in display[9]
    assert "clear filter" in display[9]


# ── bold match-highlight metadata (FR11) ─────────────────────────────────────

def test_ordinal_digit_is_bold_when_it_matches(frame_8_screen):
    # row 1: ordinal "1" matches; APPLE does not -> only the digit is bold.
    assert bold_text(frame_8_screen, 4) == "1"


def test_target_token_match_is_bold(frame_8_screen):
    # row 4 (display index 5): the "1" inside C100-F is bold; the ordinal "4" is not.
    assert bold_text(frame_8_screen, 5) == "1"


def test_two_digit_ordinal_bolds_only_the_matched_digits(frame_8_screen):
    # row 10 (index 6): only the leading "1" matches.
    assert bold_text(frame_8_screen, 6) == "1"
    # row 11 (index 7): both digits match.
    assert bold_text(frame_8_screen, 7) == "11"


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_8_matches_snapshot(frame_8_screen, assert_snapshot):
    assert_snapshot(frame_8_screen, Path(__file__).parent / "snapshots" / "frame_8.txt")
