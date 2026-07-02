"""
TASK-009 — golden render test for frame 14 (accept confirmation ignores filter).

The AT-T collision (ordinal 3) is resolved to "ATT", then the reviewer applies
the "12" text filter (frame 13, no matching rows) before re-entering the accept
confirmation. The confirming table MUST ignore the active filter and render the
full 11-row list windowed at scrollOffset=0 (spec §8.2 / §10.1 frame 14) — the
key behaviour that distinguishes this frame from frame 6. The prompt defaults to
NO and the footer shows the edit-mappings hint (spec §6.5–6.6).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_14_screen):
    return frame_14_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_exactly_15_lines(frame_14_screen):
    assert frame_14_screen.lines == 15


# ── the confirming table ignores the active filter (spec §10.1 frame 14) ─────

def test_full_table_renders_despite_the_non_matching_filter(display):
    # The "12" filter matches no rows in BROWSING, yet the confirming table
    # renders the full first page (ordinals 1..9), proving the filter does not
    # constrain the confirming body.
    assert "APPLE" in display[4]
    assert "SPY" in display[12]


def test_no_filter_prompt_is_shown(display):
    assert "Filter:" not in display[1]


def test_confirming_body_row_count_is_a_full_page():
    from mapping_resolution_tui.selectors import select_body_rows, select_visible_rows

    # Rebuild the frame-14 state to assert the selector directly: the filtered
    # visible rows are empty, but the confirming body is the full-list window.
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.state import ConfirmationChoice, ConfirmationKind, Mode

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, "2")
    state = replace(
        state,
        mode=Mode.CONFIRMING,
        confirmation=replace(
            state.confirmation,
            kind=ConfirmationKind.ACCEPT,
            choice=ConfirmationChoice.NO,
        ),
    )

    assert select_visible_rows(state) == []
    body = select_body_rows(state)
    assert [m.ordinal for m in body] == [1, 2, 3, 4, 5, 6, 7, 8, 9]


# ── prompt / header / footer ─────────────────────────────────────────────────

def test_prompt_is_accept_all_with_no_active(display):
    assert display[1].strip() == "Accept all? [y/N]"


def test_header_omits_collision_count_and_ends_ctrl_c_cancel(display):
    assert "unresolved collision" not in display[0]
    assert "ctrl+c cancel" in display[0]


def test_no_row_renders_a_selection_cursor(display):
    assert all("▸" not in display[i] for i in range(4, 13))


def test_footer_shows_edit_mappings(display):
    footer = display[14]
    assert "scroll" in footer
    assert "pageup/dn" in footer
    assert "edit mappings" in footer


# ── snapshot ──────────────────────────────────────────────────────────────────

def test_frame_14_matches_snapshot(frame_14_screen, assert_snapshot):
    assert_snapshot(frame_14_screen, Path(__file__).parent / "snapshots" / "frame_14.txt")
