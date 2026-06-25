"""
TASK-002 — golden render test for frame 8 (single-character text filter).

The reviewer types ``1`` in BROWSING over a collision-free dataset. Visible rows
narrow to ordinals 1, 4, 10, and 11; ordinal 4 is included only because its
target token ``C100-F`` contains a ``1`` (source ``100-F`` must not match).

Geometry assertions use pyte ``screen.display``; bold/reverse style assertions
use pyte cell attributes, and raw ANSI inspection covers SGR 2 (dim) which pyte
does not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_8_screen):
    return frame_8_screen.display


# ── geometry ────────────────────────────────────────────────────────────────

def test_frame_ends_at_footer_with_no_trailing_padding(frame_8_lines):
    # Under-full frame (4 body rows): header, prompt, blank, table header,
    # 4 body rows, blank separator, footer = 10 lines, ending at the footer.
    # The variable-height layout contract forbids blank padding below the
    # footer (spec §6.1/§6.2).
    assert len(frame_8_lines) == 10
    assert "edit selected" in frame_8_lines[-1]
    assert "clear filter" in frame_8_lines[-1]


def test_header_is_collision_free(display):
    assert "ctrl+s submit" in display[0]
    assert "unresolved collision" not in display[0]


def test_prompt_shows_filter_text(display):
    assert display[1].startswith("  Filter: 1")


def test_only_matching_rows_are_visible(display):
    body = [display[i] for i in range(4, 8)]
    ordinals = [line.split()[0] if line.split()[0] != "▸" else line.split()[1] for line in body]
    assert ordinals == ["1", "4", "10", "11"]
    # No further body rows below the four matches.
    assert display[8].strip() == ""


def test_selected_row_is_first_match(display):
    assert display[4].startswith("▸")


def test_source_value_does_not_create_a_match(display):
    # Ordinal 4 matched on its token C100-F; its source 100-F is shown but the
    # row is present because of the token, not the source.
    assert "C100-F" in display[5]
    assert "100-F" in display[5]


def test_footer_offers_clear_filter(display):
    footer = next(line for line in display if "edit selected" in line)
    assert "esc clear filter" in footer


# ── style spans ───────────────────────────────────────────────────────────────

def test_prompt_cursor_block_is_reverse_video_after_query(frame_8_screen):
    # "  Filter: " is 10 chars (cols 0–9), "1" at col 10, cursor space at col 11.
    assert frame_8_screen.buffer[1][10].reverse is False
    assert frame_8_screen.buffer[1][11].reverse is True
    assert frame_8_screen.display[1][11] == " "


def test_ordinal_1_digit_is_bold_but_pad_space_is_not(frame_8_screen):
    # Ordinal cell occupies cols 3–4; "1" at col 4 is bold, the pad space is not.
    assert frame_8_screen.buffer[4][3].bold is False
    assert frame_8_screen.buffer[4][4].bold is True


def test_token_match_in_c100f_is_bold(frame_8_screen):
    # Token starts at col 8: "C" at col 8 (not bold), "1" at col 9 (bold).
    assert frame_8_screen.buffer[5][8].bold is False
    assert frame_8_screen.buffer[5][9].bold is True


def test_ordinal_10_bolds_only_the_leading_one(frame_8_screen):
    assert frame_8_screen.buffer[6][3].bold is True   # "1"
    assert frame_8_screen.buffer[6][4].bold is False  # "0"


def test_ordinal_11_bolds_every_matched_digit(frame_8_screen):
    # Every non-overlapping match is bold (spec §3.3), so both ones are bold.
    assert frame_8_screen.buffer[7][3].bold is True
    assert frame_8_screen.buffer[7][4].bold is True


def test_source_columns_are_never_bold(frame_8_screen):
    # The GnuCash Source column (from col 34 onward) carries no bold highlight.
    for row in range(4, 8):
        assert not any(frame_8_screen.buffer[row][col].bold for col in range(34, 80))


def test_header_shortcut_uses_dim(frame_8_lines):
    # pyte does not track SGR 2 (dim/faint); inspect raw ANSI output directly.
    assert "\x1b[2m" in frame_8_lines[0]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_8_matches_snapshot(frame_8_screen, assert_snapshot):
    assert_snapshot(frame_8_screen, Path(__file__).parent / "snapshots" / "frame_8.txt")
