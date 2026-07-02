import pytest
from dataclasses import replace
from mapping_resolution_tui.state import (
    AppConfig, AppState, Mode, Mapping, EditState, FocusRegion, Source, TargetValidationContext,
)
from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.selectors import select_default_source_value
from tests.fixtures.storyboard import make_config, make_mappings


def _select(state, ordinal):
    return replace(state, selection=replace(state.selection, selected_ordinal=ordinal))


def _with_target_value(state, ordinal, target_value):
    mappings = [
        replace(m, target_value=target_value) if m.ordinal == ordinal else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)

def test_accept_line_enters_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    assert state.mode == Mode.BROWSING

    state = reduce(state, KeyEvent.ENTER)
    assert state.mode == Mode.EDITING
    assert state.edit is not None
    assert state.edit.buffer == ""
    assert state.edit.cursor == 0
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

def test_enter_edit_seeds_ghost_validation_for_empty_target():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    mapping = next(m for m in state.mappings if m.ordinal == state.selection.selected_ordinal)
    assert mapping.target_value is None  # sanity: exercising the ghost-default path
    default_value = select_default_source_value(mapping)
    expected = config.target_policy.validate(
        default_value,
        TargetValidationContext(is_concrete_buffer=False, is_ghost_only_default=True, mapping=mapping),
    )

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == ""
    assert state.edit.validation == expected
    assert state.edit.validation.icon is None  # ghost-only default never shows the checkmark


def test_enter_edit_seeds_concrete_validation_for_valid_target_value():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    ordinal = state.mappings[0].ordinal
    state = _select(_with_target_value(state, ordinal, "AAPL"), ordinal)

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == "AAPL"
    assert state.edit.validation.status == "VALID"
    assert state.edit.validation.icon == "✓"  # concrete buffer, not ghost — checkmark shown


def test_enter_edit_seeds_concrete_validation_for_invalid_target_value():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    ordinal = state.mappings[0].ordinal
    state = _select(_with_target_value(state, ordinal, "aapl"), ordinal)  # lowercase: fails policy

    state = reduce(state, KeyEvent.ENTER)

    assert state.edit.buffer == "aapl"
    assert state.edit.validation.status == "INVALID"
    assert state.edit.validation.error_message == "must start with A-Z"


def test_escape_cancels_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.mode == Mode.EDITING

    state = reduce(state, KeyEvent.ESCAPE)
    assert state.mode == Mode.BROWSING
    assert state.edit is None

def test_insert_char_in_editing_mode():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    state = reduce(state, "A")
    assert state.edit.buffer == "A"
    assert state.edit.cursor == 1

def test_over_limit_character_is_discarded_and_flashes():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":  # 24 valid chars, fills the cap
        state = reduce(state, ch)
    before_buffer = state.edit.buffer
    assert len(before_buffer) == 24

    flashed = reduce(state, "Y", now=100.0)

    assert flashed.edit.buffer == before_buffer  # 25th char discarded
    assert flashed.edit.cursor == 24
    assert flashed.edit.max_length_flash_until == 100.0 + 1.0
    assert flashed.edit.validation.error_message == "24 chars max"
    assert flashed.edit.validation.icon == "✗"

def test_flash_clears_on_next_accepted_edit():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":
        state = reduce(state, ch)
    flashed = reduce(state, "Y", now=100.0)
    assert flashed.edit.max_length_flash_until is not None

    cleared = reduce(flashed, KeyEvent.BACKSPACE)
    assert cleared.edit.max_length_flash_until is None

def _with_source_list_focus(state):
    # No reducer path reaches SOURCE_LIST yet (source-pointer navigation is a
    # future task), so the fixture is hand-built directly on edit.
    return replace(
        state,
        edit=replace(
            state.edit,
            focus_region=FocusRegion.SOURCE_LIST,
            source_pointer_index=0,
            source_entry_buffer="prior text",
        ),
    )

def test_accepted_edit_exits_source_list():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, "A")
    state = _with_source_list_focus(state)
    assert state.edit.focus_region == FocusRegion.SOURCE_LIST

    result = reduce(state, KeyEvent.BACKSPACE)
    assert result.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert result.edit.source_pointer_index is None
    assert result.edit.source_entry_buffer is None

def test_over_limit_reject_exits_source_list():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":  # 24 valid chars, fills the cap
        state = reduce(state, ch)
    state = _with_source_list_focus(state)
    assert state.edit.focus_region == FocusRegion.SOURCE_LIST

    flashed = reduce(state, "Y", now=100.0)
    assert flashed.edit.buffer == state.edit.buffer  # 25th char still discarded
    assert flashed.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert flashed.edit.source_pointer_index is None
    assert flashed.edit.source_entry_buffer is None

def test_repeated_over_limit_rearms_the_flash_window():
    # Each rejected over-limit char re-arms max_length_flash_until from `now`,
    # not just the first one (FR20).
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    for ch in "ABCDEFGHIJKLMNOPQRSTUVWX":
        state = reduce(state, ch)

    first = reduce(state, "Y", now=100.0)
    assert first.edit.max_length_flash_until == 101.0

    second = reduce(first, "Z", now=200.0)
    assert second.edit.max_length_flash_until == 201.0


def test_enter_edit_is_noop_without_a_selection():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = _select(state, None)

    result = reduce(state, KeyEvent.ENTER)

    assert result is state
    assert result.mode == Mode.BROWSING
    assert result.edit is None


def test_enter_edit_preserves_filter_state():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.TAB)  # autocompletes filter.raw = "!"
    assert state.filter.raw == "!"

    state = reduce(state, KeyEvent.ENTER)

    assert state.mode == Mode.EDITING
    assert state.filter.raw == "!"  # entering EDITING never touches the filter


# ── readline aliases (FR18) ───────────────────────────────────────────────────

def _typed(state, text):
    for ch in text:
        state = reduce(state, ch)
    return state

def test_cursor_home_and_end_move_to_buffer_boundaries():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL")
    assert state.edit.cursor == 4

    state = reduce(state, KeyEvent.CURSOR_HOME)
    assert state.edit.cursor == 0

    state = reduce(state, KeyEvent.CURSOR_END)
    assert state.edit.cursor == 4


def test_cursor_left_clamps_at_zero():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.cursor == 0

    state = reduce(state, KeyEvent.CURSOR_LEFT)
    assert state.edit.cursor == 0


def test_cursor_right_clamps_at_buffer_end():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AB")
    assert state.edit.cursor == 2

    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    assert state.edit.cursor == 2


def test_kill_line_clears_after_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 2

    state = reduce(state, KeyEvent.KILL_LINE)

    assert state.edit.buffer == "AB"
    assert state.edit.cursor == 2


def test_unix_line_discard_clears_before_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 2

    state = reduce(state, KeyEvent.UNIX_LINE_DISCARD)

    assert state.edit.buffer == "CD"
    assert state.edit.cursor == 0


def test_kill_word_deletes_the_word_ahead_of_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL XYZ")
    state = reduce(state, KeyEvent.CURSOR_HOME)

    state = reduce(state, KeyEvent.KILL_WORD)

    assert state.edit.buffer == " XYZ"
    assert state.edit.cursor == 0


def test_backward_kill_word_deletes_the_word_behind_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL XYZ")  # cursor already at the end

    state = reduce(state, KeyEvent.BACKWARD_KILL_WORD)

    assert state.edit.buffer == "AAPL "
    assert state.edit.cursor == 5


def test_delete_char_removes_the_character_at_the_cursor():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ABCD")
    state = reduce(state, KeyEvent.CURSOR_HOME)
    state = reduce(state, KeyEvent.CURSOR_RIGHT)  # cursor at 1

    state = reduce(state, KeyEvent.DELETE_CHAR)

    assert state.edit.buffer == "ACD"
    assert state.edit.cursor == 1


def test_delete_char_at_end_of_buffer_is_noop():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AB")

    result = reduce(state, KeyEvent.DELETE_CHAR)

    assert result is state


def test_backspace_on_empty_buffer_is_noop():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.buffer == ""

    result = reduce(state, KeyEvent.BACKSPACE)

    assert result is state


# ── source-list navigation and autofill (TASK-007, FR21) ─────────────────────

def _no_active_sources(state):
    ordinal = state.selection.selected_ordinal
    mappings = [
        replace(
            m,
            sources=[replace(s, original_value=None, sanitized_value=None) for s in m.sources],
            target_value="ZERO",
        ) if m.ordinal == ordinal else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


def test_selection_down_from_token_input_enters_source_list_at_first_source():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.buffer == ""
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result.edit.focus_region == FocusRegion.SOURCE_LIST
    assert result.edit.source_pointer_index == 0
    assert result.edit.source_entry_buffer == ""
    assert result.edit.buffer == "AAPL"
    assert result.edit.cursor == 4
    assert result.edit.validation.status == "VALID"
    assert result.edit.validation.icon == "✓"


def test_selection_up_from_token_input_enters_source_list_at_last_source():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)

    result = reduce(state, KeyEvent.SELECTION_UP)

    assert result.edit.focus_region == FocusRegion.SOURCE_LIST
    assert result.edit.source_pointer_index == 1
    assert result.edit.source_entry_buffer == ""
    assert result.edit.buffer == "APPLE"
    assert result.edit.cursor == 5
    assert result.edit.validation.status == "VALID"
    assert result.edit.validation.icon == "✓"


def test_entering_source_list_saves_the_current_buffer_as_source_entry_buffer():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "Z")
    assert state.edit.buffer == "Z"

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result.edit.source_entry_buffer == "Z"
    assert result.edit.buffer == "AAPL"


def test_selection_down_within_source_list_moves_pointer_and_autofills():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, KeyEvent.SELECTION_DOWN)  # index 0, buffer "AAPL"
    assert state.edit.source_pointer_index == 0

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result.edit.focus_region == FocusRegion.SOURCE_LIST
    assert result.edit.source_pointer_index == 1
    assert result.edit.buffer == "APPLE"
    assert result.edit.cursor == 5
    assert result.edit.source_entry_buffer == ""
    assert result.edit.validation.status == "VALID"
    assert result.edit.validation.icon == "✓"


def test_selection_up_within_source_list_moves_pointer_and_autofills():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, KeyEvent.SELECTION_UP)  # index 1, buffer "APPLE"
    assert state.edit.source_pointer_index == 1

    result = reduce(state, KeyEvent.SELECTION_UP)

    assert result.edit.source_pointer_index == 0
    assert result.edit.buffer == "AAPL"
    assert result.edit.cursor == 4
    assert result.edit.focus_region == FocusRegion.SOURCE_LIST


def test_selection_up_at_first_source_exits_to_token_input_and_restores_buffer():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "Z")
    state = reduce(state, KeyEvent.SELECTION_DOWN)  # enters SOURCE_LIST at index 0
    assert state.edit.source_pointer_index == 0
    assert state.edit.source_entry_buffer == "Z"

    result = reduce(state, KeyEvent.SELECTION_UP)

    assert result.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert result.edit.source_pointer_index is None
    assert result.edit.source_entry_buffer is None
    assert result.edit.buffer == "Z"
    assert result.edit.cursor == 1
    assert result.edit.validation.icon == "✓"


def test_selection_down_at_last_source_exits_to_token_input_and_restores_buffer():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, KeyEvent.SELECTION_UP)  # enters SOURCE_LIST at last index (1)
    assert state.edit.source_pointer_index == 1
    assert state.edit.source_entry_buffer == ""

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result.edit.focus_region == FocusRegion.TOKEN_INPUT
    assert result.edit.source_pointer_index is None
    assert result.edit.source_entry_buffer is None
    assert result.edit.buffer == ""
    assert result.edit.cursor == 0
    assert result.edit.validation.icon is None  # restored empty buffer is ghost-only again


def test_selection_down_is_noop_with_no_active_sources():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = _no_active_sources(state)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result is state


def test_selection_up_is_noop_with_no_active_sources():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = _no_active_sources(state)
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.focus_region == FocusRegion.TOKEN_INPUT

    result = reduce(state, KeyEvent.SELECTION_UP)

    assert result is state


def test_source_navigation_does_not_special_case_a_buffer_matching_a_source_value():
    config = make_config()
    mappings = make_mappings()
    state = make_initial_state(config, mappings)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "AAPL")  # buffer coincidentally equals source[0]'s value
    assert state.edit.buffer == "AAPL"

    result = reduce(state, KeyEvent.SELECTION_DOWN)

    assert result.edit.focus_region == FocusRegion.SOURCE_LIST
    assert result.edit.source_pointer_index == 0
    assert result.edit.source_entry_buffer == "AAPL"
    assert result.edit.buffer == "AAPL"


# ── TASK-008: submit and cancel (FR16/FR18/FR22/FR23) ────────────────────────


def test_submit_commits_buffer_and_returns_to_browsing_when_collisions_remain():
    state = make_initial_state(make_config(), make_mappings())
    state = _typed(state, "1")  # filter to ordinal 1 (APPLE)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "APPL")

    result = reduce(state, KeyEvent.ENTER)

    assert result.mode == Mode.BROWSING
    assert result.edit is None
    committed = next(m for m in result.mappings if m.ordinal == 1)
    assert committed.target_value == "APPL"


def test_submit_preserves_filter_and_selection_exactly():
    state = make_initial_state(make_config(), make_mappings())
    state = _typed(state, "1")
    pre_filter = state.filter
    pre_selected = state.selection.selected_ordinal
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "APPL")

    result = reduce(state, KeyEvent.ENTER)

    assert result.filter == pre_filter  # raw, text, collision_only, cursor (FR16)
    assert result.selection.selected_ordinal == pre_selected


def test_submit_resolving_the_final_collision_enters_accept_confirmation():
    from mapping_resolution_tui.state import ConfirmationChoice, ConfirmationKind

    state = make_initial_state(make_config(), make_mappings())
    state = _select(state, 3)  # the AT-T collision row
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "ATT")

    result = reduce(state, KeyEvent.ENTER)

    assert result.mode == Mode.CONFIRMING
    assert result.confirmation.kind == ConfirmationKind.ACCEPT
    assert result.confirmation.choice == ConfirmationChoice.NO
    assert result.confirmation.second_ctrl_c_armed is False
    assert result.edit is None
    committed = next(m for m in result.mappings if m.ordinal == 3)
    assert committed.target_value == "ATT"


def test_submit_over_an_already_collision_free_dataset_enters_accept_confirmation():
    # Spec §4.2: Enter with VALID validation → "CONFIRMING with ACCEPT if
    # collisions now zero" — the guard is the post-commit count alone, with no
    # requirement that the commit itself resolved anything.
    from mapping_resolution_tui.state import ConfirmationKind

    state = make_initial_state(make_config(), make_mappings())
    state = _with_target_value(state, 3, "ATT")  # resolve the AT-T collision first
    state = _select(state, 1)
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "APPL")

    result = reduce(state, KeyEvent.ENTER)

    assert result.mode == Mode.CONFIRMING
    assert result.confirmation.kind == ConfirmationKind.ACCEPT


def test_submit_with_invalid_buffer_is_a_noop_keeping_the_error_visible():
    state = make_initial_state(make_config(), make_mappings())
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "44PL")
    assert state.edit.validation.status == "INVALID"

    result = reduce(state, KeyEvent.ENTER)

    assert result is state  # no commit, mode unchanged, error remains (FR18)


def test_submit_with_empty_buffer_is_a_noop():
    state = make_initial_state(make_config(), make_mappings())
    state = reduce(state, KeyEvent.ENTER)
    assert state.edit.buffer == ""

    result = reduce(state, KeyEvent.ENTER)

    assert result is state


def test_cancel_discards_the_buffer_and_preserves_the_filter():
    state = make_initial_state(make_config(), make_mappings())
    state = _typed(state, "1")
    pre_filter = state.filter
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "XYZ")

    result = reduce(state, KeyEvent.ESCAPE)

    assert result.mode == Mode.BROWSING
    assert result.edit is None
    assert result.filter == pre_filter  # FR16: intact exactly as on entry
    assert result.selection.selected_ordinal == 1
    untouched = next(m for m in result.mappings if m.ordinal == 1)
    assert untouched.target_value is None


def test_quit_during_editing_cancels_the_edit_not_the_run():
    state = make_initial_state(make_config(), make_mappings())
    state = reduce(state, KeyEvent.ENTER)
    state = _typed(state, "X")

    result = reduce(state, KeyEvent.QUIT)

    assert result.mode == Mode.BROWSING
    assert result.edit is None
    assert result.result.status == "RUNNING"  # the run itself continues
