"""
TASK-012 — golden render test for frame 1b (ctrl+c exit confirmation).

From the initial browsing state (frame 1a, the AT-T collision still open) the
reviewer presses ctrl+c. The app enters the exit confirmation: CONFIRMING /
EXIT, ``choice = NO``, ``second_ctrl_c_armed = True`` (spec §4.2). The header
keeps the ``1 unresolved collision`` count and swaps its shortcut to ``ctrl+c
exit``; the prompt is ``Skip adding commodities? [y/N]`` with the active NO
reverse-video and bold; the confirming table windows the full 11-row list
(ordinals 1..9 at ``scrollOffset = 0``) with no row cursor while rows 2/3 keep
their ``!`` markers; the footer is the choice-driven ``↑↓ scroll · shift+↑↓
pageup/dn · ↵ edit mappings`` (spec §6.4–6.6, storyboard frame 1b).

Geometry assertions use pyte ``screen.display``; style assertions use pyte cell
attributes and raw ANSI inspection for SGR 2 (dim).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_1b_screen):
    return frame_1b_screen.display


# ── app state (spec §4.2 / §10.1 frame 1b, §10.2 defect-prevention rows) ─────

def test_state_is_exit_confirmation_armed_with_no_active():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.state import (
        ConfirmationChoice,
        ConfirmationKind,
        Mode,
    )

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.QUIT)

    assert state.mode == Mode.CONFIRMING
    assert state.confirmation.kind == ConfirmationKind.EXIT
    assert state.confirmation.choice == ConfirmationChoice.NO
    assert state.confirmation.second_ctrl_c_armed is True
    assert state.result.status == "RUNNING"


def test_second_ctrl_c_from_this_state_sends_sigint():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.QUIT)   # frame 1b: armed exit confirmation
    state = reduce(state, KeyEvent.QUIT)   # second ctrl+c force-exits
    assert state.result.status == "SIGINT"


def test_frame_is_exactly_15_lines(frame_1b_screen):
    assert frame_1b_screen.lines == 15


# ── header (spec §6.4) — collision count kept, shortcut is ctrl+c exit ───────

def test_header_keeps_the_unresolved_collision_count(display):
    assert "1 unresolved collision" in display[0]


def test_header_shortcut_is_ctrl_c_exit(display):
    assert "ctrl+c exit" in display[0]
    assert "ctrl+c cancel" not in display[0]


def test_header_shortcut_uses_dim(frame_1b_lines):
    # pyte does not track SGR 2 (dim/faint); inspect the raw ANSI output.
    assert "\x1b[2m" in frame_1b_lines[0]


# ── prompt (spec §6.5) — Skip adding commodities? [y/N] ──────────────────────

def test_prompt_is_skip_adding_commodities_with_no_active(display):
    assert display[1].strip() == "Skip adding commodities? [y/N]"


def test_active_no_choice_is_reverse_video_and_bold(frame_1b_screen):
    prompt = frame_1b_screen.display[1]
    n_col = prompt.index("[y/") + 3
    cell = frame_1b_screen.buffer[1][n_col]
    assert prompt[n_col] == "N"
    assert cell.reverse is True
    assert cell.bold is True


# ── table body (spec §8.2 / §8.4) — full list windowed 1..9, no cursor ───────

def test_no_row_renders_a_selection_cursor(display):
    # Body occupies display rows 4..12; CONFIRMING renders no ▸ cursor glyph.
    assert all("▸" not in display[i] for i in range(4, 13))


def test_first_visible_body_row_is_ordinal_1(display):
    row = display[4]
    assert row.split()[0] == "1"
    assert "APPLE" in row


def test_last_visible_body_row_is_ordinal_9(display):
    row = display[12]
    assert row.split()[0] == "9"
    assert "SPY" in row


def test_collision_rows_keep_their_markers(display):
    assert "!" in display[5]  # ordinal 2 (AT-T)
    assert "!" in display[6]  # ordinal 3 (AT-T)


def test_non_collision_row_has_no_marker(display):
    assert "!" not in display[4]  # ordinal 1 (APPLE)


def test_body_rows_are_not_super_dim(frame_1b_lines):
    # Super-dim (SGR 2) rows are an EDITING affordance only; the confirming body
    # MUST render at normal brightness (spec §8.4). Only the header shortcut may
    # legitimately carry SGR 2, so no body line (indices 4..12) may.
    assert all("\x1b[2m" not in frame_1b_lines[i] for i in range(4, 13))


# ── footer (spec §6.6, choice-driven for NO) ─────────────────────────────────

def test_footer_shows_scroll_page_and_edit_mappings(display):
    footer = display[14]
    assert "↑↓ scroll" in footer
    assert "shift+↑↓ pageup/dn" in footer
    assert "↵ edit mappings" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_1b_matches_snapshot(frame_1b_screen, assert_snapshot):
    assert_snapshot(frame_1b_screen, Path(__file__).parent / "snapshots" / "frame_1b.txt")
