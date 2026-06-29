"""
TASK-004 — golden render test for frame 3 (collision metafilter + text filter).

From frame 2 (the autocompleted ``!`` metafilter, ordinal 2 selected) the
reviewer types ``3``. ``filter.raw`` becomes ``"!3"``: ``collision_only`` derives
True and ``text`` derives ``"3"``. Of the two collision rows only ordinal 3
matches ``3``, so the visible list narrows to it and the selection clamps from
ordinal 2 to ordinal 3 (spec §3.4 / §10.1 frame 3).

Geometry assertions use pyte ``screen.display``; bold/reverse style assertions
use pyte cell attributes, and raw ANSI inspection covers SGR 2 (dim) which pyte
does not track.
"""
from pathlib import Path
import pytest


@pytest.fixture
def display(frame_3_screen):
    return frame_3_screen.display


# ── geometry ────────────────────────────────────────────────────────────────

def test_frame_ends_at_footer_with_no_trailing_padding(frame_3_lines):
    # Under-full frame (1 body row): header, prompt, blank, table header,
    # 1 body row, blank separator, footer = 7 lines, ending at the footer on
    # row 7 with no blank padding below it (spec §6.1/§6.2).
    assert len(frame_3_lines) == 7
    assert "edit selected" in frame_3_lines[-1]
    assert "clear filter" in frame_3_lines[-1]


def test_header_still_reports_one_unresolved_collision(display):
    assert "1 unresolved collision" in display[0]


def test_prompt_shows_metafilter_and_text(display):
    # The literal `!3` is rendered followed by the reverse-video cursor block.
    assert display[1].startswith("  Filter: !3")


def test_only_ordinal_3_is_visible(display):
    body = display[4]
    ordinal = body.split()[0] if body.split()[0] != "▸" else body.split()[1]
    assert ordinal == "3"
    # No further body rows below the single match.
    assert display[5].strip() == ""


def test_selected_row_clamped_to_ordinal_3(display):
    assert display[4].startswith("▸")


def test_collision_marker_present_on_the_row(display):
    assert "!" in display[4]


def test_footer_offers_clear_filter(display):
    assert "esc clear filter" in display[-1]


# ── style spans ───────────────────────────────────────────────────────────────

def test_prompt_cursor_block_is_reverse_video_after_query(frame_3_screen):
    # "  Filter: " is 10 chars (cols 0–9), "!" at col 10, "3" at col 11, the
    # reverse-video cursor space at col 12 (cursor sits at the end of "!3").
    assert frame_3_screen.buffer[1][11].reverse is False
    assert frame_3_screen.buffer[1][12].reverse is True
    assert frame_3_screen.display[1][12] == " "


def test_ordinal_3_digit_is_bold(frame_3_screen):
    # Ordinal cell occupies cols 2–3; the matched "3" at col 3 is bold.
    assert frame_3_screen.buffer[4][3].bold is True


def test_token_at_t_is_not_bold(frame_3_screen):
    # The token "AT-T" begins at col 8 and contains no "3"; nothing in it is bold.
    assert not any(frame_3_screen.buffer[4][col].bold for col in range(8, 32))


def test_source_column_is_not_bold(frame_3_screen):
    assert not any(frame_3_screen.buffer[4][col].bold for col in range(34, 80))


def test_header_shortcut_uses_dim(frame_3_lines):
    # pyte does not track SGR 2 (dim/faint); inspect raw ANSI output directly.
    assert "\x1b[2m" in frame_3_lines[0]


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_3_matches_snapshot(frame_3_screen, assert_snapshot):
    assert_snapshot(frame_3_screen, Path(__file__).parent / "snapshots" / "frame_3.txt")
