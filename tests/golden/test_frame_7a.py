"""
TASK-011 — golden render test for frame 7a (accept confirmation, scrolled once).

From frame 6 (CONFIRMING/ACCEPT, choice NO, scroll 0) the reviewer presses ``↓``
once. CONFIRMING has no row cursor, so the arrow scrolls the body window only
(spec §8.4): ordinals 2..10 render at normal brightness — never super-dim, that
styling is EDITING-only — while the "Accept all? [y/N]" prompt and the
"↑↓ scroll · shift+↑↓ pageup/dn · ↵ edit mappings" footer are unchanged from
frame 6 (spec §6.4–6.6, storyboard frames 6/7a).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_7a_screen):
    return frame_7a_screen.display


# ── geometry and table body (spec §8.2/§8.4) ─────────────────────────────────

def test_frame_is_fifteen_lines_scrolled_to_ordinals_2_through_10(frame_7a_lines, display):
    assert len(frame_7a_lines) == 15
    body = display[4:13]
    assert [row.split()[0] for row in body] == [str(n) for n in range(2, 11)]


def test_row_1_scrolled_out_and_no_row_cursor_renders(display):
    body = display[4:13]
    assert all("APPLE" not in row for row in body)
    assert all("▸" not in row for row in body)


def test_body_rows_are_never_super_dim(frame_7a_lines):
    # Super-dim (SGR 2) is an EDITING affordance; the confirming body renders
    # at normal brightness at every scroll position (spec §8.4).
    assert all("\x1b[2m" not in line for line in frame_7a_lines[4:13])


# ── prompt and footer, unchanged from frame 6 (spec §6.5/§6.6) ────────────────

def test_prompt_still_reads_accept_all_with_no_active(frame_7a_screen, display):
    assert display[1].startswith("  Accept all? [y/N]")
    assert frame_7a_screen.buffer[1][17].reverse is True
    assert frame_7a_screen.buffer[1][17].bold is True


def test_footer_still_reads_edit_mappings_with_scroll_hints(display):
    footer = display[-1]
    assert "↑↓ scroll" in footer
    assert "shift+↑↓ pageup/dn" in footer
    assert "↵ edit mappings" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_7a_matches_snapshot(frame_7a_screen, assert_snapshot):
    assert_snapshot(frame_7a_screen, Path(__file__).parent / "snapshots" / "frame_7a.txt")
