"""
TASK-010 — unit tests for the accept-confirmation reducer transitions.

Covers ctrl+s entry from BROWSING (gated on zero unresolved collisions), the
y/n and arrow choice controls, confirming-only scrolling (§8.4/§8.5), and
leaving the confirmation via Enter/NO or Esc with the filter preserved and the
selection clamped onto the (possibly filtered) browsing rows (spec §4.2 / §8.4).
"""
from dataclasses import replace

import pytest

from tests.fixtures.storyboard import make_config, make_mappings
from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    Mode,
)


def _base_state():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def _resolved_state():
    """Base state with the AT-T collision resolved (ordinal 3 -> 'ATT')."""
    state = _base_state()
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


def _accept_confirming():
    """A resolved state that has entered the accept confirmation via ctrl+s."""
    return reduce(_resolved_state(), KeyEvent.SUBMIT)


# ── ctrl+s entry from BROWSING (spec §4.2) ───────────────────────────────────

def test_ctrl_s_with_open_collisions_is_a_noop():
    state = _base_state()  # the fresh storyboard has one unresolved collision
    result = reduce(state, KeyEvent.SUBMIT)
    assert result is state


def test_ctrl_s_with_zero_collisions_enters_accept_confirmation():
    # The collision was already resolved at session start (no edit performed).
    state = _resolved_state()
    result = reduce(state, KeyEvent.SUBMIT)
    assert result.mode == Mode.CONFIRMING
    assert result.confirmation.kind == ConfirmationKind.ACCEPT
    assert result.confirmation.choice == ConfirmationChoice.NO


def test_ctrl_s_after_resolving_then_returning_re_enters_confirmation():
    # Resolve via edit -> auto CONFIRMING; leave with Esc; ctrl+s re-enters.
    state = _base_state()
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    for ch in "ATT":
        state = reduce(state, ch)
    state = reduce(state, KeyEvent.ENTER)   # auto-entry
    assert state.mode == Mode.CONFIRMING
    state = reduce(state, KeyEvent.ESCAPE)  # back to BROWSING
    assert state.mode == Mode.BROWSING
    state = reduce(state, KeyEvent.SUBMIT)  # ctrl+s re-entry
    assert state.mode == Mode.CONFIRMING
    assert state.confirmation.kind == ConfirmationKind.ACCEPT
    assert state.confirmation.choice == ConfirmationChoice.NO


def test_submit_is_a_noop_in_editing():
    state = _base_state()
    state = reduce(state, KeyEvent.ENTER)  # enter EDITING
    assert state.mode == Mode.EDITING
    result = reduce(state, KeyEvent.SUBMIT)
    assert result is state


# ── choice controls: y / n / arrows (spec §4.2 / §5) ─────────────────────────

def test_y_sets_choice_yes_and_n_sets_choice_no():
    state = _accept_confirming()
    assert state.confirmation.choice == ConfirmationChoice.NO
    state = reduce(state, "y")
    assert state.confirmation.choice == ConfirmationChoice.YES
    state = reduce(state, "n")
    assert state.confirmation.choice == ConfirmationChoice.NO


def test_arrows_toggle_the_choice():
    state = _accept_confirming()
    state = reduce(state, KeyEvent.CURSOR_LEFT)
    assert state.confirmation.choice == ConfirmationChoice.YES
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    assert state.confirmation.choice == ConfirmationChoice.NO
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    assert state.confirmation.choice == ConfirmationChoice.YES


def test_repeating_the_same_choice_key_is_a_noop():
    state = _accept_confirming()  # choice = NO
    assert reduce(state, "n") is state


def test_other_printable_in_confirming_is_a_noop():
    state = _accept_confirming()
    assert reduce(state, "x") is state
    assert reduce(state, "1") is state


# ── Enter / Esc (spec §4.2 / §8.4) ───────────────────────────────────────────

def test_enter_with_yes_accepts_all_mappings():
    state = _accept_confirming()
    state = reduce(state, "y")
    result = reduce(state, KeyEvent.ENTER)
    assert result.result.status == "ACCEPTED"


def test_enter_with_no_returns_to_browsing_preserving_filter():
    state = _resolved_state()
    state = reduce(state, "1")  # filter that matches rows 1, 4, 10, 11
    state = reduce(state, KeyEvent.SUBMIT)
    assert state.mode == Mode.CONFIRMING
    result = reduce(state, KeyEvent.ENTER)  # choice defaults to NO
    assert result.mode == Mode.BROWSING
    assert result.filter.raw == "1"
    assert result.confirmation.kind == ConfirmationKind.NONE
    assert result.result.status == "RUNNING"


def test_escape_returns_to_browsing_preserving_filter():
    state = _resolved_state()
    state = reduce(state, "1")
    state = reduce(state, KeyEvent.SUBMIT)
    result = reduce(state, KeyEvent.ESCAPE)
    assert result.mode == Mode.BROWSING
    assert result.filter.raw == "1"


def test_leaving_selects_first_visible_row_at_current_scroll():
    # Scroll the confirming window down two rows (maxFillOffset for 11 rows in a
    # 15-row terminal), then leave with Enter/NO: the selection becomes the row
    # at the current scroll offset and the offset is preserved (spec §8.4).
    state = _accept_confirming()
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.selection.scroll_offset == 2
    result = reduce(state, KeyEvent.ENTER)
    assert result.mode == Mode.BROWSING
    assert result.selection.selected_ordinal == 3  # mappings[2]
    assert result.selection.scroll_offset == 2


def test_leaving_over_a_non_matching_filter_clears_the_selection():
    # frame-14-style: the "12" filter matches nothing, so leaving confirmation
    # clamps to the empty browsing view (selection cleared, scroll reset).
    state = _resolved_state()
    state = reduce(state, "1")
    state = reduce(state, "2")  # filter "12" -> no rows
    state = reduce(state, KeyEvent.SUBMIT)
    result = reduce(state, KeyEvent.ESCAPE)
    assert result.mode == Mode.BROWSING
    assert result.filter.raw == "12"
    assert result.selection.selected_ordinal is None
    assert result.selection.scroll_offset == 0


# ── confirming scrolling moves the window only, never the selection (§8.4) ───

def test_scroll_down_moves_offset_not_selection_and_clamps_to_max_fill():
    state = _accept_confirming()
    selected = state.selection.selected_ordinal
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.selection.scroll_offset == 1
    assert state.selection.selected_ordinal == selected  # selection unchanged
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.selection.scroll_offset == 2  # maxFillOffset = 11 - 9
    assert reduce(state, KeyEvent.SELECTION_DOWN) is state  # clamped


def test_scroll_up_at_the_top_is_a_noop():
    state = _accept_confirming()
    assert state.selection.scroll_offset == 0
    assert reduce(state, KeyEvent.SELECTION_UP) is state


def test_page_movement_scrolls_by_a_page_and_clamps_to_max_scroll():
    state = _accept_confirming()
    # pageSize = bodyCapacity = 9; maxScrollOffset = 11 - 1 = 10.
    state = reduce(state, KeyEvent.PAGE_DOWN)
    assert state.selection.scroll_offset == 9
    state = reduce(state, KeyEvent.PAGE_DOWN)
    assert state.selection.scroll_offset == 10  # clamped to maxScrollOffset
    assert reduce(state, KeyEvent.PAGE_DOWN) is state
    state = reduce(state, KeyEvent.PAGE_UP)
    assert state.selection.scroll_offset == 1
    state = reduce(state, KeyEvent.PAGE_UP)
    assert state.selection.scroll_offset == 0


# ── ctrl+c exit confirmation (TASK-012, spec §4.1/§4.2 ctrl+c rows) ──────────

def test_ctrl_c_in_browsing_enters_exit_confirmation_armed():
    # The fresh storyboard still has an open collision, so the exit confirmation
    # keeps that count while offering the ctrl+c-exit force-quit affordance.
    state = _base_state()
    result = reduce(state, KeyEvent.QUIT)
    assert result.mode == Mode.CONFIRMING
    assert result.confirmation.kind == ConfirmationKind.EXIT
    assert result.confirmation.choice == ConfirmationChoice.NO
    assert result.confirmation.second_ctrl_c_armed is True
    assert result.result.status == "RUNNING"


def test_ctrl_c_from_accept_confirmation_enters_exit_confirmation():
    state = _accept_confirming()  # CONFIRMING / ACCEPT
    result = reduce(state, KeyEvent.QUIT)
    assert result.mode == Mode.CONFIRMING
    assert result.confirmation.kind == ConfirmationKind.EXIT
    assert result.confirmation.choice == ConfirmationChoice.NO
    assert result.confirmation.second_ctrl_c_armed is True


def _exit_confirming():
    """A fresh state that has entered the exit confirmation via ctrl+c."""
    return reduce(_base_state(), KeyEvent.QUIT)


def test_exit_confirmation_y_n_and_arrows_set_choice():
    state = _exit_confirming()
    assert state.confirmation.choice == ConfirmationChoice.NO
    state = reduce(state, "y")
    assert state.confirmation.choice == ConfirmationChoice.YES
    state = reduce(state, "n")
    assert state.confirmation.choice == ConfirmationChoice.NO
    state = reduce(state, KeyEvent.CURSOR_LEFT)
    assert state.confirmation.choice == ConfirmationChoice.YES
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    assert state.confirmation.choice == ConfirmationChoice.NO


def test_second_ctrl_c_in_exit_confirmation_marks_sigint_bypassing_choice():
    # The second ctrl+c force-exits regardless of the choice — it MUST NOT be
    # gated on YES (spec §4.2). Even with choice = NO it emits SIGINT.
    state = _exit_confirming()
    assert state.confirmation.choice == ConfirmationChoice.NO
    result = reduce(state, KeyEvent.QUIT)
    assert result.result.status == "SIGINT"


def test_second_ctrl_c_armed_flag_is_never_reset_within_confirming():
    # Toggling the choice and scrolling MUST leave second_ctrl_c_armed set, so a
    # later ctrl+c still force-exits (spec §4.2).
    state = _exit_confirming()
    state = reduce(state, "y")
    state = reduce(state, "n")
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.confirmation.second_ctrl_c_armed is True
    assert reduce(state, KeyEvent.QUIT).result.status == "SIGINT"


def test_enter_on_yes_in_exit_confirmation_marks_skipped_without_sigint():
    state = _exit_confirming()
    state = reduce(state, "y")
    result = reduce(state, KeyEvent.ENTER)
    assert result.result.status == "SKIPPED"  # clean skip, not SIGINT


def test_enter_on_no_in_exit_confirmation_returns_to_browsing():
    state = _exit_confirming()
    result = reduce(state, KeyEvent.ENTER)  # choice defaults to NO
    assert result.mode == Mode.BROWSING
    assert result.confirmation.kind == ConfirmationKind.NONE
    assert result.confirmation.second_ctrl_c_armed is False
    assert result.result.status == "RUNNING"


def test_escape_in_exit_confirmation_returns_to_browsing():
    state = _exit_confirming()
    result = reduce(state, KeyEvent.ESCAPE)
    assert result.mode == Mode.BROWSING
    assert result.confirmation.kind == ConfirmationKind.NONE
    assert result.result.status == "RUNNING"
