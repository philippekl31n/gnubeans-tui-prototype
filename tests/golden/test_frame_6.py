"""
TASK-009 — golden render test for frame 6 (accept confirmation, NO active).

Resolving the final AT-T collision (ordinal 3 -> "ATT") and submitting drives
the app into CONFIRMING mode with kind=ACCEPT and choice=NO (FR23 auto-entry,
spec §4.2). The full table renders at scrollOffset=0 with no row cursor and no
super-dim rows; the header omits the collision count and ends in "ctrl+c
cancel"; the prompt is "Accept all? [y/N]" with the active NO indicator in
reverse-video (spec §6.4–6.6, storyboard frame 6).

The footer follows the choice-driven rule, so with choice=NO it renders the
"↵ edit mappings" hint — identical to frame 7a and never the obsolete
"↵ confirm" (spec §6.6 / §10.2). Geometry uses pyte ``screen.display``; style
uses pyte cell attributes and raw ANSI inspection for SGR 2 (dim).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_6_screen):
    return frame_6_screen.display


# ── app state / geometry ──────────────────────────────────────────────────────

def test_state_is_accept_confirmation_with_no_active():
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.state import (
        ConfirmationChoice,
        ConfirmationKind,
        Mode,
    )

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    for char in "ATT":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ENTER)

    assert state.mode == Mode.CONFIRMING
    assert state.confirmation.kind == ConfirmationKind.ACCEPT
    assert state.confirmation.choice == ConfirmationChoice.NO
    assert state.selection.scroll_offset == 0


def test_frame_is_exactly_15_lines(frame_6_screen):
    assert frame_6_screen.lines == 15


# ── header (spec §6.4) ──────────────────────────────────────────────────────

def test_header_omits_the_collision_count(display):
    assert "unresolved collision" not in display[0]


def test_header_shortcut_is_ctrl_c_cancel(display):
    assert "ctrl+c cancel" in display[0]
    assert "ctrl+c exit" not in display[0]


def test_header_glyph_is_bold(frame_6_screen):
    assert frame_6_screen.buffer[0][0].bold is True


def test_header_shortcut_is_dim(frame_6_lines):
    # pyte does not track SGR 2 (dim); inspect the raw ANSI output directly.
    assert "\x1b[2m" in frame_6_lines[0]


# ── prompt (spec §6.5) ──────────────────────────────────────────────────────

def test_prompt_is_accept_all_with_no_active(display):
    assert display[1].strip() == "Accept all? [y/N]"


def test_active_no_choice_is_reverse_video_and_bold(frame_6_screen):
    prompt = frame_6_screen.display[1]
    n_col = prompt.index("[y/") + 3
    cell = frame_6_screen.buffer[1][n_col]
    assert prompt[n_col] == "N"
    assert cell.reverse is True
    assert cell.bold is True


def test_inactive_yes_choice_is_plain(frame_6_screen):
    prompt = frame_6_screen.display[1]
    y_col = prompt.index("[y/") + 1
    cell = frame_6_screen.buffer[1][y_col]
    assert prompt[y_col] == "y"
    assert cell.reverse is False
    assert cell.bold is False


# ── table body (spec §6.4 / §8.2) ───────────────────────────────────────────

def test_no_row_renders_a_selection_cursor(display):
    # Body occupies display rows 4..12; none may carry the ▸ cursor glyph.
    assert all("▸" not in display[i] for i in range(4, 13))


def test_resolved_row_3_shows_att_and_no_collision_marker(display):
    row_3 = display[6]
    assert "ATT" in row_3
    assert "!" not in row_3


def test_full_table_first_nine_rows_visible(display):
    assert "APPLE" in display[4]
    assert "SPY" in display[12]


# ── footer (spec §6.6, choice-driven) ───────────────────────────────────────

def test_footer_shows_scroll_page_and_edit_mappings(display):
    footer = display[14]
    assert "scroll" in footer
    assert "pageup/dn" in footer
    assert "edit mappings" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_6_matches_snapshot(frame_6_screen, assert_snapshot):
    assert_snapshot(frame_6_screen, Path(__file__).parent / "snapshots" / "frame_6.txt")
