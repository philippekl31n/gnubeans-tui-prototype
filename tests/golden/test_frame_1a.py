"""
Story 1.5 — golden render test for frame 1a (initial browsing state).
Geometry assertions use pyte screen.display; style assertions use pyte cell
attributes where possible, and raw ANSI inspection for SGR 2 (dim) which
pyte does not track.
"""
from pathlib import Path
import pytest

from mapping_resolution_tui.renderer import strip_ansi


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


# ── AC6 (FR36): inspectable style spans ───────────────────────────────────────
# render_lines() returns printable lines with a parallel .spans structure: one
# list of (start_col, end_col, style) tuples per line, measured in the
# ANSI-stripped display columns, so bold/dim/reverse can be asserted without
# parsing raw escape codes and without those codes affecting display width.


def _span_text(line: str, span):
    start, end, _style = span
    return strip_ansi(line)[start:end]


def test_render_lines_returns_parallel_style_spans(frame_1a_lines):
    # One span list per printable line, and the spans never widen the line:
    # every span stays within the stripped line's display width.
    assert len(frame_1a_lines.spans) == len(frame_1a_lines)
    for line, spans in zip(frame_1a_lines, frame_1a_lines.spans):
        width = len(strip_ansi(line))
        for start, end, style in spans:
            assert 0 <= start < end <= width
            assert style in {"bold", "dim", "reverse"}


def test_header_glyph_bold_span(frame_1a_lines):
    # The leading ❯ glyph is a one-column bold span at column 0.
    assert (0, 1, "bold") in frame_1a_lines.spans[0]


def test_header_shortcut_dim_span(frame_1a_lines):
    # The trailing keyboard shortcut is a dim span covering exactly "ctrl+c cancel".
    dim_spans = [s for s in frame_1a_lines.spans[0] if s[2] == "dim"]
    assert [_span_text(frame_1a_lines[0], s) for s in dim_spans] == ["ctrl+c cancel"]


def test_filter_ghost_reverse_and_dim_spans(frame_1a_lines):
    # The empty-filter ghost renders its first character reverse-video and the
    # remainder dim; "  Filter: " is 10 columns, so the caret is at column 10.
    spans = frame_1a_lines.spans[1]
    reverse = [s for s in spans if s[2] == "reverse"]
    dim = [s for s in spans if s[2] == "dim"]
    assert reverse == [(10, 11, "reverse")]
    assert [_span_text(frame_1a_lines[1], s) for s in reverse] == ["T"]
    assert [_span_text(frame_1a_lines[1], s) for s in dim] == ["ab to view collisions"]


# ── AC7: snapshot ─────────────────────────────────────────────────────────────

def test_frame_1a_matches_snapshot(frame_1a_screen, assert_snapshot):
    assert_snapshot(frame_1a_screen, Path(__file__).parent / "snapshots" / "frame_1a.txt")
