"""
TASK-010 — golden render test for frame 6 (accept confirmation entered).

Resolving the final collision (ordinal 3 -> "ATT") auto-enters the accept
confirmation with choice NO (FR23). The full table renders at scroll 0 with no
row cursor, the prompt reads "Accept all? [y/N]" with the N reverse-video and
bold, and the footer reads "↵ edit mappings" — identical to frame 7a, never
"↵ confirm" (spec §4.1, §6.4–6.6).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_6_screen):
    return frame_6_screen.display


# ── geometry and header (spec §6.1/§6.4) ─────────────────────────────────────

def test_frame_is_fifteen_lines_with_the_zero_collision_header(frame_6_lines, display):
    # 4 fixed rows, 9 body rows (capacity at height 15), separator, footer.
    assert len(frame_6_lines) == 15
    assert display[0].startswith("❯ Reviewing 11 commodity mappings. ctrl+c cancel")


def test_full_table_renders_with_no_row_cursor(display):
    body = display[4:13]
    assert [row.split()[0] for row in body] == [str(n) for n in range(1, 10)]
    assert all("▸" not in row for row in body)


# ── prompt (spec §6.5) ────────────────────────────────────────────────────────

def test_prompt_reads_accept_all_with_no_active(display):
    assert display[1].startswith("  Accept all? [y/N]")


def test_the_active_n_choice_is_reverse_video_and_bold(frame_6_screen):
    # "  Accept all? [y/N]" — the N cell at column 17 carries the active-choice
    # styling; the inactive y at column 15 carries none.
    assert frame_6_screen.buffer[1][17].reverse is True
    assert frame_6_screen.buffer[1][17].bold is True
    assert frame_6_screen.buffer[1][15].reverse is False


# ── footer (spec §6.6) ────────────────────────────────────────────────────────

def test_footer_reads_edit_mappings_never_confirm(display):
    footer = display[-1]
    assert "↑↓ scroll" in footer
    assert "↵ edit mappings" in footer
    assert "confirm" not in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_6_matches_snapshot(frame_6_screen, assert_snapshot):
    assert_snapshot(frame_6_screen, Path(__file__).parent / "snapshots" / "frame_6.txt")
