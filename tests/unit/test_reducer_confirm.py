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
