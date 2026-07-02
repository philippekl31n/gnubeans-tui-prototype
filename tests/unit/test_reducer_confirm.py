"""
Reducer unit tests for the accept-confirmation flow (TASK-010).

Covers the two CONFIRMING/ACCEPT entry paths — the FR23 auto-entry on
submitting the last collision resolution and the ctrl+s SUBMIT entry from
BROWSING (spec §4.2) — and the in-confirmation key handling: y/n and ←/→
choice movement, Enter, and Esc. No-op paths must preserve object identity
so the loop's repaint skip keeps working.
"""

from dataclasses import replace

from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    Mode,
)
from tests.fixtures.storyboard import make_config, make_mappings


def _initial_state():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def _resolved_state():
    """Initial browsing state with the AT-T collision resolved (0 unresolved)."""
    state = _initial_state()
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


def _reduce_all(state, events):
    for event in events:
        state = reduce(state, event)
    return state


# ── ctrl+s entry from BROWSING (spec §4.2) ───────────────────────────────────


def test_submit_with_zero_collisions_enters_accept_confirmation():
    state = reduce(_resolved_state(), KeyEvent.SUBMIT)
    assert state.mode is Mode.CONFIRMING
    assert state.confirmation.kind is ConfirmationKind.ACCEPT
    assert state.confirmation.choice is ConfirmationChoice.NO


def test_submit_with_unresolved_collisions_is_identity_noop():
    state = _initial_state()
    assert reduce(state, KeyEvent.SUBMIT) is state


def test_submit_preserves_filter_and_selection():
    state = _reduce_all(_resolved_state(), ["A", "T"])
    confirming = reduce(state, KeyEvent.SUBMIT)
    assert confirming.filter is state.filter
    assert confirming.selection is state.selection


def test_submit_with_empty_visible_rows_still_enters_confirmation():
    # Frame 13 -> 14: filter '12' matches nothing, but collisions are zero, so
    # ctrl+s must still open the accept confirmation (spec §3.4).
    state = _reduce_all(_resolved_state(), ["1", "2"])
    assert state.selection.selected_ordinal is None  # sanity: no matching rows
    confirming = reduce(state, KeyEvent.SUBMIT)
    assert confirming.mode is Mode.CONFIRMING
    assert confirming.confirmation.kind is ConfirmationKind.ACCEPT


def test_submit_accepted_after_collisions_resolved_via_edit_flow():
    # AC: ctrl+s accepted whenever the count is zero, whether the collisions
    # were just resolved through the edit flow or already clear at entry.
    state = _reduce_all(
        _initial_state(),
        [KeyEvent.TAB, KeyEvent.SELECTION_DOWN, KeyEvent.ENTER, "A", "T", "T",
         KeyEvent.ENTER, KeyEvent.ESCAPE, KeyEvent.SUBMIT],
    )
    assert state.mode is Mode.CONFIRMING
    assert state.confirmation.kind is ConfirmationKind.ACCEPT
    assert state.confirmation.choice is ConfirmationChoice.NO


def test_submit_is_noop_outside_browsing():
    editing = reduce(_resolved_state(), KeyEvent.ENTER)
    assert editing.mode is Mode.EDITING  # sanity
    assert reduce(editing, KeyEvent.SUBMIT) is editing

    confirming = reduce(_resolved_state(), KeyEvent.SUBMIT)
    assert reduce(confirming, KeyEvent.SUBMIT) is confirming


# ── choice movement: y/n and ←/→ (spec §4.2/§5) ──────────────────────────────


def _confirming_state():
    return reduce(_resolved_state(), KeyEvent.SUBMIT)


def test_y_sets_choice_yes_and_n_sets_choice_no():
    confirming = _confirming_state()
    on_yes = reduce(confirming, "y")
    assert on_yes.confirmation.choice is ConfirmationChoice.YES
    assert on_yes.mode is Mode.CONFIRMING
    on_no = reduce(on_yes, "n")
    assert on_no.confirmation.choice is ConfirmationChoice.NO
    assert on_no.mode is Mode.CONFIRMING


def test_repeated_choice_keys_are_identity_noops():
    confirming = _confirming_state()
    assert reduce(confirming, "n") is confirming
    on_yes = reduce(confirming, "y")
    assert reduce(on_yes, "y") is on_yes


def test_uppercase_and_other_printables_are_identity_noops():
    # Spec §5: only lowercase y/n move the choice in CONFIRMING; every other
    # printable — including uppercase Y/N — mutates nothing.
    confirming = _confirming_state()
    for char in ("Y", "N", "a", "!", " "):
        assert reduce(confirming, char) is confirming


def test_left_and_right_arrows_toggle_choice():
    confirming = _confirming_state()
    toggled = reduce(confirming, KeyEvent.CURSOR_LEFT)
    assert toggled.confirmation.choice is ConfirmationChoice.YES
    toggled = reduce(toggled, KeyEvent.CURSOR_LEFT)
    assert toggled.confirmation.choice is ConfirmationChoice.NO
    toggled = reduce(toggled, KeyEvent.CURSOR_RIGHT)
    assert toggled.confirmation.choice is ConfirmationChoice.YES
    toggled = reduce(toggled, KeyEvent.CURSOR_RIGHT)
    assert toggled.confirmation.choice is ConfirmationChoice.NO


def test_choice_movement_leaves_mode_kind_and_table_state_untouched():
    confirming = _confirming_state()
    on_yes = reduce(confirming, "y")
    assert on_yes.confirmation.kind is ConfirmationKind.ACCEPT
    assert on_yes.mode is Mode.CONFIRMING
    assert on_yes.mappings is confirming.mappings
    assert on_yes.selection is confirming.selection
    assert on_yes.filter is confirming.filter


# ── Enter and Esc: leave or commit (spec §4.2, §8.4) ─────────────────────────


def test_enter_on_no_returns_to_browsing_with_confirmation_reset():
    browsing = reduce(_confirming_state(), KeyEvent.ENTER)
    assert browsing.mode is Mode.BROWSING
    assert browsing.confirmation.kind is ConfirmationKind.NONE
    assert browsing.confirmation.choice is ConfirmationChoice.NO
    assert browsing.confirmation.second_ctrl_c_armed is False
    assert browsing.result.status == "RUNNING"


def test_escape_returns_to_browsing_like_enter_on_no():
    via_enter = reduce(_confirming_state(), KeyEvent.ENTER)
    via_escape = reduce(_confirming_state(), KeyEvent.ESCAPE)
    assert via_escape.mode is Mode.BROWSING
    assert via_escape.confirmation == via_enter.confirmation
    assert via_escape.selection == via_enter.selection


def test_leave_confirming_selects_first_visible_row_at_current_scroll():
    # §8.4: the selected row becomes the first visible row at the current
    # scroll offset — here scroll 0 over the full list, so ordinal 1.
    browsing = reduce(_confirming_state(), KeyEvent.ESCAPE)
    assert browsing.selection.selected_ordinal == 1
    assert browsing.selection.scroll_offset == 0


def test_leave_confirming_preserves_filter_and_snaps_selection_onto_visible_rows():
    # Enter the confirmation with the text filter 'AT' active (rows 2 and 3).
    # The full-list anchor row at scroll 0 (ordinal 1) is filtered out of the
    # BROWSING view, so the selection snaps to the first visible row instead.
    state = _reduce_all(_resolved_state(), ["A", "T", KeyEvent.SUBMIT])
    browsing = reduce(state, KeyEvent.ESCAPE)
    assert browsing.mode is Mode.BROWSING
    assert browsing.filter.raw == "AT"
    assert browsing.selection.selected_ordinal == 2
    assert browsing.selection.scroll_offset == 0


def test_leave_confirming_with_no_matching_rows_clears_selection():
    # Frame 13 -> 14 -> Esc: the preserved '12' filter matches nothing, so the
    # selection clears and the scroll resets.
    state = _reduce_all(_resolved_state(), ["1", "2", KeyEvent.SUBMIT])
    browsing = reduce(state, KeyEvent.ESCAPE)
    assert browsing.mode is Mode.BROWSING
    assert browsing.filter.raw == "12"
    assert browsing.selection.selected_ordinal is None
    assert browsing.selection.scroll_offset == 0


def test_enter_on_yes_marks_the_run_accepted():
    confirming = reduce(_confirming_state(), "y")
    accepted = reduce(confirming, KeyEvent.ENTER)
    assert accepted.result.status == "ACCEPTED"
    assert accepted.mappings is confirming.mappings


def test_leave_confirming_preserves_mappings_identity():
    confirming = _confirming_state()
    browsing = reduce(confirming, KeyEvent.ENTER)
    assert browsing.mappings is confirming.mappings


def test_submit_entry_matches_last_resolution_auto_entry():
    # Both entry paths share _enter_accept_confirmation and must land on the
    # identical CONFIRMING/ACCEPT/NO confirmation state (spec §4.1).
    via_submit = reduce(_resolved_state(), KeyEvent.SUBMIT)
    via_auto = _reduce_all(
        _initial_state(),
        [KeyEvent.TAB, KeyEvent.SELECTION_DOWN, KeyEvent.ENTER, "A", "T", "T",
         KeyEvent.ENTER],
    )
    assert via_auto.mode is Mode.CONFIRMING  # FR23 auto-entry engaged
    assert via_submit.confirmation == via_auto.confirmation


# ── ↑/↓ row scrolling of the confirming window (TASK-011, spec §8.4) ─────────


def test_down_arrow_scrolls_the_window_without_moving_the_selection():
    confirming = _confirming_state()
    scrolled = reduce(confirming, KeyEvent.SELECTION_DOWN)
    assert scrolled.mode is Mode.CONFIRMING
    assert scrolled.selection.scroll_offset == 1
    # No row cursor in CONFIRMING: the arrow scrolls the window only (§8.4).
    assert scrolled.selection.selected_ordinal == confirming.selection.selected_ordinal
    assert scrolled.confirmation is confirming.confirmation
    assert scrolled.mappings is confirming.mappings


def test_up_arrow_scrolls_the_window_back():
    scrolled = reduce(_confirming_state(), KeyEvent.SELECTION_DOWN)
    back = reduce(scrolled, KeyEvent.SELECTION_UP)
    assert back.selection.scroll_offset == 0
    assert back.selection.selected_ordinal == scrolled.selection.selected_ordinal


def test_up_arrow_at_the_top_is_an_identity_noop():
    confirming = _confirming_state()
    assert reduce(confirming, KeyEvent.SELECTION_UP) is confirming


def test_down_arrow_clamps_at_max_fill_offset():
    # 11 mappings over a capacity-9 window: row movement keeps the window full,
    # so the offset clamps at maxFillOffset = 2 (§8.3); only page movement may
    # scroll into a partially-full window (§8.5).
    state = _confirming_state()
    for _ in range(2):
        state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.selection.scroll_offset == 2
    assert reduce(state, KeyEvent.SELECTION_DOWN) is state


def test_row_scrolling_clamps_over_the_full_list_despite_an_active_filter():
    # The confirming table windows the full mapping list, never the filtered
    # visibleRows (spec §10.1 frame 14) — so the clamp bound must too. With
    # the 'AT' filter (2 visible rows) a visibleRows-based clamp would pin the
    # offset at 0; the full-list maxFillOffset still allows 2.
    state = _reduce_all(_resolved_state(), ["A", "T", KeyEvent.SUBMIT])
    for _ in range(3):
        state = reduce(state, KeyEvent.SELECTION_DOWN)
    assert state.selection.scroll_offset == 2
    assert state.filter.raw == "AT"


# ── page scrolling of the confirming window (TASK-011, spec §8.5) ────────────


def test_page_down_scrolls_by_one_page_without_moving_the_selection():
    confirming = _confirming_state()
    paged = reduce(confirming, KeyEvent.PAGE_DOWN)
    assert paged.mode is Mode.CONFIRMING
    assert paged.selection.scroll_offset == 9
    # §8.5: in CONFIRMING, selection MUST NOT change.
    assert paged.selection.selected_ordinal == confirming.selection.selected_ordinal
    assert paged.confirmation is confirming.confirmation


def test_page_down_clamps_at_max_scroll_offset_with_a_partial_window():
    # Unlike row movement, page movement clamps to maxScrollOffset = 10, so
    # the last row may anchor the top of a partially-full window (§8.5,
    # frame 7b: PgDn from offset 1 lands on min(1 + 9, 10) = 10).
    state = reduce(_confirming_state(), KeyEvent.SELECTION_DOWN)
    paged = reduce(state, KeyEvent.PAGE_DOWN)
    assert paged.selection.scroll_offset == 10
    assert reduce(paged, KeyEvent.PAGE_DOWN) is paged


def test_page_up_scrolls_back_and_clamps_at_zero():
    paged = reduce(_confirming_state(), KeyEvent.PAGE_DOWN)
    back = reduce(paged, KeyEvent.PAGE_UP)
    assert back.selection.scroll_offset == 0
    assert back.selection.selected_ordinal == paged.selection.selected_ordinal
    assert reduce(back, KeyEvent.PAGE_UP) is back


def test_page_up_from_a_partial_window_steps_back_by_page_size():
    # Frame 7b -> PgUp: max(10 - 9, 0) = 1, not a snap to the top.
    state = _reduce_all(
        _confirming_state(),
        [KeyEvent.SELECTION_DOWN, KeyEvent.PAGE_DOWN],
    )
    assert state.selection.scroll_offset == 10  # sanity: frame 7b
    assert reduce(state, KeyEvent.PAGE_UP).selection.scroll_offset == 1
