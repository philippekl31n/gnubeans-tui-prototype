"""
TASK-011 — golden render test for frame 7a (accept confirmation, scrolled once).

Continues frame 6: from the accept confirmation (CONFIRMING/ACCEPT, choice=NO,
scrollOffset=0) the reviewer presses ``↓`` once. CONFIRMING has no row cursor, so
the arrow scrolls the body window only (spec §8.4): ``scrollOffset`` advances to
1 and the body shows ordinals 2..10 at normal brightness — no super-dim rows
(that styling is EDITING-only). ``selectedOrdinal`` is unaffected. The ``Accept
all? [y/N]`` prompt and the ``↑↓ scroll · shift+↑↓ pageup/dn · ↵ edit mappings``
footer are unchanged from frame 6 (spec §6.4–6.6, storyboard frames 6/7a).

Geometry assertions use pyte ``screen.display``; style assertions use pyte cell
attributes and raw ANSI inspection for SGR 2 (dim).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_7a_screen):
    return frame_7a_screen.display


# ── app state / geometry ──────────────────────────────────────────────────────

def test_state_is_accept_confirmation_scrolled_by_one_row():
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
    state = reduce(state, KeyEvent.ENTER)           # frame 6
    selected_before = state.selection.selected_ordinal
    state = reduce(state, KeyEvent.SELECTION_DOWN)  # ↓ scrolls one row

    assert state.mode == Mode.CONFIRMING
    assert state.confirmation.kind == ConfirmationKind.ACCEPT
    assert state.confirmation.choice == ConfirmationChoice.NO
    assert state.selection.scroll_offset == 1
    # No row cursor in CONFIRMING: scrolling MUST NOT move the selection (§8.4).
    assert state.selection.selected_ordinal == selected_before


def test_frame_is_exactly_15_lines(frame_7a_screen):
    assert frame_7a_screen.lines == 15


# ── header (spec §6.4) — unchanged from frame 6 ─────────────────────────────

def test_header_omits_the_collision_count(display):
    assert "unresolved collision" not in display[0]


def test_header_shortcut_is_ctrl_c_cancel(display):
    assert "ctrl+c cancel" in display[0]
    assert "ctrl+c exit" not in display[0]


# ── prompt (spec §6.5) — unchanged from frame 6 ─────────────────────────────

def test_prompt_is_accept_all_with_no_active(display):
    assert display[1].strip() == "Accept all? [y/N]"


def test_active_no_choice_is_reverse_video_and_bold(frame_7a_screen):
    prompt = frame_7a_screen.display[1]
    n_col = prompt.index("[y/") + 3
    cell = frame_7a_screen.buffer[1][n_col]
    assert prompt[n_col] == "N"
    assert cell.reverse is True
    assert cell.bold is True


# ── table body (spec §8.2 / §8.4) — scrolled to offset 1 ────────────────────

def test_no_row_renders_a_selection_cursor(display):
    # Body occupies display rows 4..12; CONFIRMING renders no ▸ cursor glyph.
    assert all("▸" not in display[i] for i in range(4, 13))


def test_first_visible_body_row_is_ordinal_2(display):
    row = display[4]
    assert row.split()[0] == "2"
    assert "AT-T" in row


def test_last_visible_body_row_is_ordinal_10(display):
    row = display[12]
    assert row.split()[0] == "10"
    assert "VTSAX" in row


def test_row_1_apple_scrolled_out_of_view(display):
    assert all("APPLE" not in display[i] for i in range(4, 13))


def test_body_rows_are_not_super_dim(frame_7a_lines):
    # Super-dim (SGR 2) rows are an EDITING affordance only; the confirming body
    # MUST render at normal brightness (spec §8.4). Only the header shortcut may
    # legitimately carry SGR 2, so no body line (indices 4..12) may.
    assert all("\x1b[2m" not in frame_7a_lines[i] for i in range(4, 13))


# ── footer (spec §6.6, choice-driven) — unchanged from frame 6 ──────────────

def test_footer_shows_scroll_page_and_edit_mappings(display):
    footer = display[14]
    assert "↑↓ scroll" in footer
    assert "shift+↑↓ pageup/dn" in footer
    assert "↵ edit mappings" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_7a_matches_snapshot(frame_7a_screen, assert_snapshot):
    assert_snapshot(frame_7a_screen, Path(__file__).parent / "snapshots" / "frame_7a.txt")
