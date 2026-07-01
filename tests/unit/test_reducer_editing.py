"""
Unit tests for EDITING-mode reduction (TASK-006, spec §7).

Covers the BROWSING -> EDITING transition (FR15), the streaming insert algorithm
with live ghost/validation recompute (FR17/FR18), invalid-character insertion and
submit gating (FR19), the over-limit discard + max-length flash (FR20), Backspace,
and the readline-style aliases on the token input (spec §5.1).
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.actions import (
    AcceptLine,
    Backspace,
    ClearFilter,
    InsertChar,
    KillLine,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    MoveSelectionDown,
    MoveSelectionUp,
    UnixLineDiscard,
)
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import (
    select_footer_content,
    select_ghost_suffix,
)
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    FocusRegion,
    FooterHint,
    Mode,
)
from tests.fixtures.storyboard import make_config, make_mappings


@pytest.fixture
def browsing():
    return make_initial_state(make_config(), make_mappings(), frame_height=15)


def _edit_ordinal(state, ordinal):
    """Enter EDITING on ``ordinal`` by selecting it then pressing Enter."""
    state = replace(state, selection=replace(state.selection, selected_ordinal=ordinal))
    return reduce(state, AcceptLine())


def _mapping(state, ordinal):
    return next(m for m in state.mappings if m.ordinal == ordinal)


# ── entering edit mode (FR15, spec §7.1) ─────────────────────────────────────

def test_enter_edit_initializes_empty_buffer_when_target_is_null(browsing):
    state = _edit_ordinal(browsing, 1)  # APPLE, target_value is None

    assert state.mode == Mode.EDITING
    assert state.edit.mapping_ordinal == 1
    assert state.edit.buffer == ""
    assert state.edit.cursor == 0
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert state.edit.source_pointer_index is None
    assert state.edit.source_entry_buffer is None
    assert state.edit.max_length_flash_until is None


def test_enter_edit_seeds_buffer_from_literal_target(browsing):
    seeded = replace(
        browsing,
        mappings=[
            replace(m, target_value="ZZ9") if m.ordinal == 1 else m
            for m in browsing.mappings
        ],
    )
    state = _edit_ordinal(seeded, 1)

    assert state.edit.buffer == "ZZ9"
    assert state.edit.cursor == 3  # cursor at the end of the seeded buffer


def test_enter_edit_preserves_filter_state(browsing):
    filtered = reduce(browsing, InsertChar("1"))  # filter.raw "1", row 1 selected
    state = reduce(filtered, AcceptLine())

    assert state.mode == Mode.EDITING
    assert state.filter.raw == "1"
    assert state.filter.cursor == 1


def test_enter_edit_is_noop_without_a_selection(browsing):
    empty = reduce(browsing, InsertChar("z"))  # no matching rows -> selection None
    assert empty.selection.selected_ordinal is None
    assert reduce(empty, AcceptLine()) is empty


# ── streaming insert + ghost/validation recompute (FR17/FR18) ────────────────

def test_insert_advances_cursor_and_keeps_prefix_ghost(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, InsertChar("A"))

    assert state.edit.buffer == "A"
    assert state.edit.cursor == 1
    # "A" is still a prefix of the default "APPLE": ghost is the remaining suffix.
    assert select_ghost_suffix(state, _mapping(state, 1)) == "PPLE"
    assert state.edit.validation.status == "VALID"


def test_insert_that_deviates_clears_the_ghost(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AX":
        state = reduce(state, InsertChar(ch))

    assert state.edit.buffer == "AX"
    # "AX" is not a prefix of "APPLE" -> ghost disappears (FR17).
    assert select_ghost_suffix(state, _mapping(state, 1)) == ""


def test_insert_at_cursor_position(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AC":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveCursorLeft())   # cursor between A and C
    state = reduce(state, InsertChar("B"))

    assert state.edit.buffer == "ABC"
    assert state.edit.cursor == 2


# ── invalid characters insert and gate submit (FR19) ─────────────────────────

def test_invalid_character_inserts_and_gates_submit(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, InsertChar("4"))  # invalid: must start with A-Z

    assert state.edit.buffer == "4"  # inserted, not discarded
    assert state.edit.validation.status == "INVALID"
    assert state.edit.validation.icon == "✗"
    assert state.edit.validation.error_message == "must start with A-Z"
    # Submit is gated off; the footer surfaces the error instead.
    footer = select_footer_content(state)
    assert FooterHint.SUBMIT not in footer.hints
    assert footer.error == "must start with A-Z"


def test_bang_is_inserted_and_marked_invalid(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, InsertChar("!"))

    assert state.edit.buffer == "!"
    assert state.edit.validation.status == "INVALID"


def test_valid_buffer_offers_submit(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ATT":
        state = reduce(state, InsertChar(ch))

    assert state.edit.validation.status == "VALID"
    assert FooterHint.SUBMIT in select_footer_content(state).hints


def test_empty_buffer_is_not_submittable(browsing):
    state = _edit_ordinal(browsing, 1)

    assert state.edit.validation.status == "EMPTY"
    assert state.edit.validation.icon is None
    assert FooterHint.SUBMIT not in select_footer_content(state).hints


# ── over-limit discard + max-length flash (FR20) ─────────────────────────────

def _fill_to_cap(state):
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":  # 24 valid chars
        state = reduce(state, InsertChar(ch), now=0.0)
    return state


def test_over_limit_character_is_discarded_and_flashes(browsing):
    state = _fill_to_cap(_edit_ordinal(browsing, 1))
    assert len(state.edit.buffer) == 24
    before = state.edit.buffer

    flashed = reduce(state, InsertChar("Y"), now=100.0)

    from mapping_resolution_tui.reducer import _BURST_DURATION

    assert flashed.edit.buffer == before  # 25th char discarded
    assert flashed.edit.cursor == 24
    assert flashed.edit.max_length_flash_until == 100.0 + _BURST_DURATION
    assert flashed.edit.validation.error_message == "24 chars max"
    assert flashed.edit.validation.icon == "✗"


def test_flash_clears_on_next_accepted_edit(browsing):
    state = _fill_to_cap(_edit_ordinal(browsing, 1))
    flashed = reduce(state, InsertChar("Y"), now=100.0)
    assert flashed.edit.max_length_flash_until is not None

    cleared = reduce(flashed, Backspace())
    assert cleared.edit.max_length_flash_until is None


def test_repeated_over_limit_resets_the_flash_window(browsing):
    # Each over-limit discard overwrites the prior deadline with a fresh 150ms
    # window from the latest keystroke — bursts reset, never stack (spec §7.6).
    from mapping_resolution_tui.reducer import _BURST_DURATION

    state = _fill_to_cap(_edit_ordinal(browsing, 1))
    first = reduce(state, InsertChar("Y"), now=10.0)
    assert first.edit.max_length_flash_until == 10.0 + _BURST_DURATION

    second = reduce(first, InsertChar("Z"), now=10.05)
    assert second.edit.max_length_flash_until == 10.05 + _BURST_DURATION


# ── backspace (spec §7.2) ────────────────────────────────────────────────────

def test_backspace_removes_char_before_cursor(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ATT":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, Backspace())

    assert state.edit.buffer == "AT"
    assert state.edit.cursor == 2


def test_backspace_is_noop_on_empty_buffer(browsing):
    state = _edit_ordinal(browsing, 1)
    assert reduce(state, Backspace()) is state


def test_backspace_to_prefix_restores_ghost(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "APX":
        state = reduce(state, InsertChar(ch))
    assert select_ghost_suffix(state, _mapping(state, 1)) == ""  # deviated

    state = reduce(state, Backspace())  # back to "AP", a prefix again
    assert state.edit.buffer == "AP"
    assert select_ghost_suffix(state, _mapping(state, 1)) == "PLE"


# ── readline aliases on the token input (spec §5.1 / FR18) ───────────────────

def test_ctrl_a_and_ctrl_e_move_to_line_boundaries(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ABC":
        state = reduce(state, InsertChar(ch))

    home = reduce(state, MoveCursorHome())     # ctrl+a
    assert home.edit.cursor == 0
    end = reduce(home, MoveCursorEnd())         # ctrl+e
    assert end.edit.cursor == 3


def test_ctrl_b_and_ctrl_f_move_one_character(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ABC":
        state = reduce(state, InsertChar(ch))

    left = reduce(state, MoveCursorLeft())      # ctrl+b
    assert left.edit.cursor == 2
    right = reduce(left, MoveCursorRight())     # ctrl+f
    assert right.edit.cursor == 3
    # forward-char clamps at the buffer end.
    assert reduce(right, MoveCursorRight()) is right


def test_cursor_left_clamps_at_zero(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, InsertChar("A"))
    state = reduce(state, MoveCursorHome())
    assert reduce(state, MoveCursorLeft()) is state


def test_ctrl_k_kills_to_end_of_line(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ABCDE":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveCursorHome())
    state = reduce(state, MoveCursorRight())
    state = reduce(state, MoveCursorRight())   # cursor after "AB"
    state = reduce(state, KillLine())

    assert state.edit.buffer == "AB"
    assert state.edit.cursor == 2


def test_ctrl_u_discards_to_start_of_line(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "ABCDE":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveCursorLeft())    # cursor before final "E"
    state = reduce(state, UnixLineDiscard())

    assert state.edit.buffer == "E"
    assert state.edit.cursor == 0


def test_ghost_hidden_when_cursor_not_at_end(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AP":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveCursorLeft())  # cursor not at end

    # Ghost only renders at the buffer end (FR17).
    assert select_ghost_suffix(state, _mapping(state, 1)) == ""


# ── source pointer movement + autofill (FR21, spec §7.4) ─────────────────────

def test_down_from_token_input_enters_source_list_at_first_source(browsing):
    state = _edit_ordinal(browsing, 1)  # APPLE: cmdty_id AAPL, user_symbol APPLE
    moved = reduce(state, MoveSelectionDown())

    assert moved.edit.focus_region == FocusRegion.SOURCE_LIST
    assert moved.edit.source_pointer_index == 0
    assert moved.edit.source_entry_buffer == ""  # empty token buffer was saved
    assert moved.edit.buffer == "AAPL"           # autofilled effective value
    assert moved.edit.cursor == 4                # cursor at buffer end
    assert moved.edit.validation.status == "VALID"


def test_up_from_token_input_enters_source_list_at_last_source(browsing):
    state = _edit_ordinal(browsing, 1)
    moved = reduce(state, MoveSelectionUp())

    assert moved.edit.focus_region == FocusRegion.SOURCE_LIST
    assert moved.edit.source_pointer_index == 1  # last active source
    assert moved.edit.buffer == "APPLE"
    assert moved.edit.cursor == 5
    assert moved.edit.validation.status == "VALID"


def test_source_entry_buffer_preserves_in_progress_typing(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AT":
        state = reduce(state, InsertChar(ch))
    moved = reduce(state, MoveSelectionDown())

    assert moved.edit.source_entry_buffer == "AT"  # in-progress buffer stored
    assert moved.edit.buffer == "AAPL"             # autofilled over the top


def test_move_down_within_source_list_advances_pointer(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, MoveSelectionDown())      # -> first source AAPL
    state = reduce(state, MoveSelectionDown())      # -> second source APPLE

    assert state.edit.focus_region == FocusRegion.SOURCE_LIST
    assert state.edit.source_pointer_index == 1
    assert state.edit.buffer == "APPLE"
    assert state.edit.source_entry_buffer == ""     # entry buffer unchanged


def test_move_up_within_source_list_retreats_pointer(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, MoveSelectionUp())         # token input -> last source APPLE
    state = reduce(state, MoveSelectionUp())         # -> first source AAPL

    assert state.edit.source_pointer_index == 0
    assert state.edit.buffer == "AAPL"


def test_down_past_last_source_restores_buffer_and_returns_to_token_input(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AT":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveSelectionDown())       # first source AAPL
    state = reduce(state, MoveSelectionDown())       # second source APPLE
    state = reduce(state, MoveSelectionDown())       # past last -> restore

    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert state.edit.source_pointer_index is None
    assert state.edit.source_entry_buffer is None
    assert state.edit.buffer == "AT"                 # restored pre-nav buffer
    assert state.edit.cursor == 2


def test_up_past_first_source_restores_buffer_and_returns_to_token_input(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "AT":
        state = reduce(state, InsertChar(ch))
    state = reduce(state, MoveSelectionDown())       # first source AAPL
    state = reduce(state, MoveSelectionUp())         # above first -> restore

    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert state.edit.source_pointer_index is None
    assert state.edit.source_entry_buffer is None
    assert state.edit.buffer == "AT"


def test_typing_in_source_list_exits_navigation_and_edits_autofill(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, MoveSelectionDown())       # source list, buffer AAPL
    state = reduce(state, InsertChar("X"))

    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert state.edit.source_pointer_index is None
    assert state.edit.source_entry_buffer is None
    assert state.edit.buffer == "AAPLX"              # char applied to autofill
    assert state.edit.validation.status == "VALID"


def test_backspace_in_source_list_exits_navigation_and_deletes_from_autofill(browsing):
    state = _edit_ordinal(browsing, 1)
    state = reduce(state, MoveSelectionUp())         # source list, buffer APPLE
    state = reduce(state, Backspace())

    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert state.edit.source_pointer_index is None
    assert state.edit.buffer == "APPL"
    # The default-source ghost reappears now that the buffer is a prefix again.
    assert select_ghost_suffix(state, _mapping(state, 1)) == "E"


def test_single_source_mapping_cycles_through_token_input(browsing):
    # A mapping with one active source: ↓ enters the list, ↓ again steps below the
    # only source and returns to the token input (spec §7.4).
    state = _edit_ordinal(browsing, 5)               # GOOGL, single cmdty_id source
    entered = reduce(state, MoveSelectionDown())
    assert entered.edit.source_pointer_index == 0
    assert entered.edit.buffer == "GOOGL"

    exited = reduce(entered, MoveSelectionDown())
    assert exited.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert exited.edit.source_pointer_index is None
    assert exited.edit.buffer == ""                  # restored empty entry buffer


# ── submit (Enter): commit + accept-confirmation gate (spec §4.2 / FR22–FR23) ─

def _resolve_at_t(state):
    """Commit ordinal 3 to ``ATT``, leaving the dataset collision-free."""
    return replace(
        state,
        mappings=[
            replace(m, target_value="ATT") if m.ordinal == 3 else m
            for m in state.mappings
        ],
    )


def test_submit_commits_the_buffer_literally_to_the_target(browsing):
    # Editing the collision row (ordinal 3) with a valid non-empty buffer and
    # pressing Enter writes the buffer verbatim to mapping.target_value (FR22).
    state = _edit_ordinal(browsing, 3)
    for ch in "ATT":
        state = reduce(state, InsertChar(ch))
    submitted = reduce(state, AcceptLine())

    assert _mapping(submitted, 3).target_value == "ATT"
    assert submitted.edit is None


def test_submit_resolving_final_collision_enters_accept_confirmation(browsing):
    # The AT-T collision is the only one; resolving it on submit brings the count
    # to zero, so the app enters CONFIRMING with kind ACCEPT and choice NO (FR23).
    state = _edit_ordinal(browsing, 3)
    for ch in "ATT":
        state = reduce(state, InsertChar(ch))
    submitted = reduce(state, AcceptLine())

    assert submitted.mode == Mode.CONFIRMING
    assert submitted.confirmation.kind == ConfirmationKind.ACCEPT
    assert submitted.confirmation.choice == ConfirmationChoice.NO
    assert submitted.selection.scroll_offset == 0


def test_submit_leaving_collisions_returns_to_browsing(browsing):
    # Editing a non-collision row (ordinal 1) and submitting leaves the AT-T
    # collision unresolved, so the app returns to BROWSING (FR16), keeping the
    # selection on the edited row.
    state = _edit_ordinal(browsing, 1)
    for ch in "APPL":
        state = reduce(state, InsertChar(ch))
    submitted = reduce(state, AcceptLine())

    assert submitted.mode == Mode.BROWSING
    assert submitted.confirmation.kind == ConfirmationKind.NONE
    assert _mapping(submitted, 1).target_value == "APPL"
    assert submitted.selection.selected_ordinal == 1


def test_submit_over_collision_free_dataset_returns_to_browsing(browsing):
    # When no collision existed before the commit, a valid submit does not enter
    # accept confirmation (nothing "became zero because of the commit", spec §9);
    # it returns to BROWSING. Accept confirmation is reached manually via ctrl+s.
    state = _edit_ordinal(_resolve_at_t(browsing), 1)
    for ch in "APPL":
        state = reduce(state, InsertChar(ch))
    submitted = reduce(state, AcceptLine())

    assert submitted.mode == Mode.BROWSING
    assert _mapping(submitted, 1).target_value == "APPL"


def test_submit_preserves_the_active_filter(browsing):
    # A valid submit that returns to BROWSING keeps the pre-edit filter intact.
    state = reduce(browsing, InsertChar("1"))  # filter.raw "1", row 1 selected
    state = reduce(state, AcceptLine())        # enter EDITING on ordinal 1
    for ch in "APPL":
        state = reduce(state, InsertChar(ch))
    submitted = reduce(state, AcceptLine())

    assert submitted.mode == Mode.BROWSING
    assert submitted.filter.raw == "1"
    assert submitted.filter.cursor == 1


def test_submit_is_gated_off_for_an_invalid_buffer(browsing):
    # Enter with an INVALID buffer is a no-op: no commit, the mode stays EDITING,
    # and the same state object is returned (FR18).
    state = _edit_ordinal(browsing, 1)
    for ch in "44PL":
        state = reduce(state, InsertChar(ch))
    assert state.edit.validation.status == "INVALID"

    assert reduce(state, AcceptLine()) is state


def test_submit_is_gated_off_for_an_empty_buffer(browsing):
    # Enter with an empty (ghost-only) buffer is a no-op: no commit (FR18/FR22).
    state = _edit_ordinal(browsing, 1)
    assert state.edit.buffer == ""

    assert reduce(state, AcceptLine()) is state


# ── cancel (Esc / ctrl+c): discard + browsing restore (spec §4.2 / FR16) ─────

def test_cancel_discards_the_buffer_and_returns_to_browsing(browsing):
    state = _edit_ordinal(browsing, 1)
    for ch in "XYZ":
        state = reduce(state, InsertChar(ch))
    cancelled = reduce(state, ClearFilter())

    assert cancelled.mode == Mode.BROWSING
    assert cancelled.edit is None
    assert _mapping(cancelled, 1).target_value is None  # buffer never committed


def test_cancel_preserves_filter_and_selection(browsing):
    state = reduce(browsing, InsertChar("1"))  # filter.raw "1", row 1 selected
    state = reduce(state, AcceptLine())        # enter EDITING on ordinal 1
    for ch in "XYZ":
        state = reduce(state, InsertChar(ch))
    cancelled = reduce(state, ClearFilter())

    assert cancelled.mode == Mode.BROWSING
    assert cancelled.filter.raw == "1"
    assert cancelled.filter.cursor == 1
    assert cancelled.selection.selected_ordinal == 1
