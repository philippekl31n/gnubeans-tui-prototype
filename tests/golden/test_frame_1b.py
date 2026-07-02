"""
TASK-012 — golden render test for frame 1b (exit confirmation entered).

ctrl+c from BROWSING with an unresolved collision opens the exit confirmation
with choice NO and the second ctrl+c armed. The full table renders at scroll 0
with no row cursor and no super-dim rows, the prompt reads "Skip adding
commodities? [y/N]" with the N reverse-video and bold, and the footer reads
"↵ edit mappings" (spec §4.2, §6.4–6.6).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_1b_screen):
    return frame_1b_screen.display


# ── geometry and header (spec §6.1/§6.4) ─────────────────────────────────────

def test_frame_is_fifteen_lines_with_the_collision_header(frame_1b_lines, display):
    # 4 fixed rows, 9 body rows (capacity at height 15), separator, footer.
    assert len(frame_1b_lines) == 15
    assert display[0].startswith(
        "❯ Reviewing 11 commodity mappings. 1 unresolved collision. ctrl+c exit"
    )


def test_full_table_renders_with_no_row_cursor(display):
    body = display[4:13]
    assert [row.split()[0] for row in body] == [str(n) for n in range(1, 10)]
    assert all("▸" not in row for row in body)


def test_collision_rows_keep_their_bang_marker(display):
    # CONFIRMING renders the full table as-is: the unresolved AT-T collision
    # rows stay flagged, never super-dimmed away (spec §6.4).
    assert display[5].lstrip().startswith("2  !AT-T")
    assert display[6].lstrip().startswith("3  !AT-T")


# ── prompt (spec §6.5) ────────────────────────────────────────────────────────

def test_prompt_reads_skip_adding_commodities_with_no_active(display):
    assert display[1].startswith("  Skip adding commodities? [y/N]")


def test_the_active_n_choice_is_reverse_video_and_bold(frame_1b_screen):
    # "  Skip adding commodities? [y/N]" — the N cell at column 30 carries the
    # active-choice styling; the inactive y at column 28 carries none.
    assert frame_1b_screen.buffer[1][30].reverse is True
    assert frame_1b_screen.buffer[1][30].bold is True
    assert frame_1b_screen.buffer[1][28].reverse is False


# ── footer (spec §6.6) ────────────────────────────────────────────────────────

def test_footer_reads_edit_mappings_while_no_is_active(display):
    footer = display[-1]
    assert "↑↓ scroll" in footer
    assert "shift+↑↓ pageup/dn" in footer
    assert "↵ edit mappings" in footer
    assert "skip" not in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_1b_matches_snapshot(frame_1b_screen, assert_snapshot):
    assert_snapshot(
        frame_1b_screen, Path(__file__).parent / "snapshots" / "frame_1b.txt"
    )
