"""
TASK-008 — golden render test for frame_esc_from_edit (cancel restores frame 8).

From the frame 8 context (resolved dataset, filter '1', ordinal 1 selected) the
reviewer enters edit mode, types "XYZ" into the buffer, and presses Esc. The
edit is discarded and the browsing context — filter.raw, filter.cursor,
collision_only, selection, and scroll — is preserved exactly as it was on
entry, so the rendered frame is bit-identical to frame 8 (FR16).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_esc_from_edit_screen):
    return frame_esc_from_edit_screen.display


# ── FR16: the pre-edit browsing frame is restored exactly ─────────────────────

def test_frame_is_bit_identical_to_the_pre_edit_frame_8(
    frame_esc_from_edit_lines, frame_8_lines
):
    assert frame_esc_from_edit_lines == frame_8_lines


def test_filter_line_shows_the_preserved_text_filter(display):
    assert "Filter: 1" in display[1]


def test_discarded_buffer_leaves_the_original_token_on_row_1(display):
    # The typed "XYZ" never lands: row 1 still shows the committed APPLE.
    assert "APPLE" in display[4]
    assert all("XYZ" not in row for row in display)


def test_footer_returns_to_the_browsing_hints(display):
    footer = display[-1]
    assert "↵ edit selected" in footer
    assert "esc clear filter" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_esc_from_edit_matches_snapshot(
    frame_esc_from_edit_screen, assert_snapshot
):
    assert_snapshot(
        frame_esc_from_edit_screen,
        Path(__file__).parent / "snapshots" / "frame_esc_from_edit.txt",
    )
