"""
Story 1.5 — golden render test for frame 1a (initial browsing state).
Geometry assertions use ANSI-stripped lines; style assertions inspect raw spans.
"""
import pytest


@pytest.fixture
def frame_lines():
    from mapping_resolution_tui.fixtures.storyboard import make_storyboard_config, make_storyboard_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.renderer import render_frame
    state = make_initial_state(make_storyboard_config(), make_storyboard_mappings(), frame_height=15)
    return render_frame(state)


@pytest.fixture
def stripped(frame_lines):
    from mapping_resolution_tui.renderer import strip_ansi
    return [strip_ansi(line) for line in frame_lines]


# ── AC5: geometry ─────────────────────────────────────────────────────────────

def test_frame_is_exactly_15_lines(frame_lines):
    assert len(frame_lines) == 15


def test_header_row_contains_unresolved_collision_count(stripped):
    assert "1 unresolved collision" in stripped[0]


def test_header_row_contains_review_count(stripped):
    assert "11" in stripped[0]


def test_row_1_has_selection_cursor(stripped):
    # display position 1 is frame line index 4 (header+prompt+blank+table_header)
    assert stripped[4].startswith("▸")


def test_rows_2_and_3_have_collision_markers(stripped):
    assert "!" in stripped[5]
    assert "!" in stripped[6]


def test_rows_without_collision_have_no_marker(stripped):
    # ordinal 1 (display pos 1, index 4) has no collision
    assert "!" not in stripped[4]


def test_footer_is_on_row_15(stripped):
    assert "edit selected" in stripped[14]
    assert "pageup" in stripped[14] or "page" in stripped[14].lower()


def test_row_14_is_blank_separator(stripped):
    assert stripped[13].strip() == ""


def test_row_3_is_blank(stripped):
    assert stripped[2].strip() == ""


def test_table_header_row_contains_column_labels(stripped):
    assert "Beancount Token" in stripped[3]
    assert "GnuCash Source" in stripped[3]


# ── AC6: style spans ──────────────────────────────────────────────────────────

def test_header_shortcut_text_contains_dim_span(frame_lines):
    # "ctrl+c cancel" portion must be wrapped in a dim ANSI sequence
    DIM = "\x1b[2m"
    assert DIM in frame_lines[0]


def test_selected_row_contains_reverse_video_span(frame_lines):
    # the ▸ cursor row (index 4) must contain a reverse-video span
    REVERSE = "\x1b[7m"
    assert REVERSE in frame_lines[4]
