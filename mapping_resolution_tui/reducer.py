"""
Reducer module: pure state transitions and application initialization.
"""



from dataclasses import replace
from typing import Optional
import shutil
import time

from mapping_resolution_tui.actions import (
    AcceptLine,
    Action,
    AutocompleteBang,
    Backspace,
    BackwardKillWord,
    ClearFilter,
    DeleteChar,
    InsertChar,
    KillLine,
    KillWord,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    MoveSelectionDown,
    MoveSelectionUp,
    PageDown,
    PageUp,
    Redraw,
    UnixLineDiscard,
)
from mapping_resolution_tui.selectors import (
    parse_filter,
    select_active_sources,
    select_body_capacity,
    select_collision_ghost_visible,
    select_concrete_value,
    select_source_pointer_value,
    select_unresolved_collision_count,
    select_visible_rows,
    sort_mappings_for_initial_display,
)
from mapping_resolution_tui.state import (
    AppConfig,
    AppState,
    ConfirmationChoice,
    ConfirmationKind,
    ConfirmationState,
    EditState,
    FilterState,
    FocusRegion,
    Mapping,
    Mode,
    ResultState,
    SelectionState,
    TargetValidationContext,
    TerminalState,
    ValidationState,
)

# ASCII word characters for word-wise kill operations (spec S5.1).
_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789_-"
)


def make_initial_state(
    config: AppConfig,
    mappings: list[Mapping],
    frame_height: Optional[int] = None,
) -> AppState:
    if frame_height is None:
        frame_height = shutil.get_terminal_size(fallback=(75, 15)).lines

    sorted_mappings = list(sort_mappings_for_initial_display(mappings))

    # Assign sequential ordinals 1..N after the bootstrap-time sort
    ordered_mappings = []
    for i, mapping in enumerate(sorted_mappings, 1):
        ordered_mappings.append(Mapping(
            ordinal=i,
            sources=mapping.sources,
            default_source_label=mapping.default_source_label,
            target_value=mapping.target_value,
        ))

    return AppState(
        config=config,
        mode=Mode.BROWSING,
        mappings=ordered_mappings,
        filter=_derive_filter(raw="", cursor=0),
        selection=SelectionState(
            selected_ordinal=ordered_mappings[0].ordinal if ordered_mappings else None,
            scroll_offset=0,
        ),
        edit=None,
        confirmation=ConfirmationState(
            kind=ConfirmationKind.NONE,
            choice=ConfirmationChoice.NO,
            second_ctrl_c_armed=False,
        ),
        terminal=TerminalState(height=frame_height),
        result=ResultState(status="RUNNING"),
    )


# ── filter helpers ──────────────────────────────────────────────────────────


def _derive_filter(*, raw: str, cursor: int) -> FilterState:
    """Build a :class:`FilterState` with ``raw`` as the source of truth.

    The post-mutation derivation (spec S5.1): ``filter.cursor`` is clamped into
    ``[0, len(raw)]`` and ``collision_only`` / ``text`` are re-derived from
    ``raw`` — ``collision_only`` is True when ``raw`` begins with ``!`` and
    ``text`` is ``raw`` minus that single leading ``!``. The reducer never
    stores ``collision_only`` or ``text`` independently of ``raw``.
    """
    cursor = max(0, min(cursor, len(raw)))
    collision_only, text = parse_filter(raw)
    return FilterState(
        raw=raw,
        collision_only=collision_only,
        text=text,
        cursor=cursor,
    )


def _with_filter(state: AppState, *, raw: str, cursor: int) -> AppState:
    """Return a new state whose filter is re-derived from ``raw`` and ``cursor``.

    This runs the full post-mutation sequence (spec §3.4 / S5.1): the filter is
    re-derived (clamping ``filter.cursor`` and re-deriving ``collision_only`` /
    ``text``). If the filter text has changed, the visible rows are recomputed,
    and the selection snaps to the first visible row with scroll reset to 0.
    Cursor-only moves pass the same raw and bypass the clamp.
    """
    filter_changed = raw != state.filter.raw
    interim = replace(state, filter=_derive_filter(raw=raw, cursor=cursor))
    
    if not filter_changed:
        return interim

    selection = _clamp_selection(interim)
    if selection is interim.selection:
        return interim
    return replace(interim, selection=selection)


def _clamp_selection(state: AppState) -> SelectionState:
    """Clamp the selection onto the visible rows for ``state`` (spec §3.4 / S8.2).

    Snaps to the first visible row, or to ``None`` when no rows match. The scroll
    window is always reset to 0. Returns the existing :class:`SelectionState`
    object unchanged when nothing moves.
    """
    selection = state.selection
    visible = select_visible_rows(state)

    if not visible:
        selected = None
    else:
        selected = visible[0].ordinal

    scroll = 0

    if selected == selection.selected_ordinal and scroll == selection.scroll_offset:
        return selection
    return replace(selection, selected_ordinal=selected, scroll_offset=scroll)


def _move_selection(state: AppState, delta: int) -> AppState:
    visible = select_visible_rows(state)
    if not visible:
        return state
        
    current = state.selection.selected_ordinal
    if current is None:
        idx = 0
    else:
        try:
            idx = next(i for i, m in enumerate(visible) if m.ordinal == current)
        except StopIteration:
            idx = 0
            
    idx = max(0, min(len(visible) - 1, idx + delta))
    
    capacity = select_body_capacity(state.terminal.height)
    selected_ordinal = visible[idx].ordinal
    scroll = state.selection.scroll_offset
    
    # Anchored body allocation: selected row MUST be visible.
    if idx < scroll:
        scroll = idx
    elif idx >= scroll + capacity:
        scroll = idx - capacity + 1
        
    scroll = max(0, min(scroll, max(0, len(visible) - capacity)))
    
    if selected_ordinal == state.selection.selected_ordinal and scroll == state.selection.scroll_offset:
        return state
        
    selection = replace(state.selection, selected_ordinal=selected_ordinal, scroll_offset=scroll)
    return replace(state, selection=selection)


def _page_selection(state: AppState, direction: int) -> AppState:
    visible = select_visible_rows(state)
    if not visible:
        return state
        
    capacity = select_body_capacity(state.terminal.height)
    max_scroll_offset = max(0, len(visible) - 1)
    
    scroll = state.selection.scroll_offset
    last_idx = len(visible) - 1

    if direction == 1:
        # PgDn: if already on the last page, just move cursor to last row
        if scroll <= last_idx < scroll + capacity:
            new_scroll = scroll
            selected_idx = last_idx
        else:
            new_scroll = max(0, min(scroll + capacity, max_scroll_offset))
            selected_idx = new_scroll
    else:
        # PgUp: if already on the first page, just move cursor to first row
        if scroll == 0:
            new_scroll = 0
            selected_idx = 0
        else:
            new_scroll = max(0, scroll - capacity)
            selected_idx = new_scroll

    selected_ordinal = visible[selected_idx].ordinal
    
    if selected_ordinal == state.selection.selected_ordinal and new_scroll == state.selection.scroll_offset:
        return state
        
    selection = replace(state.selection, selected_ordinal=selected_ordinal, scroll_offset=new_scroll)
    return replace(state, selection=selection)


def _backward_word_start(raw: str, cursor: int) -> int:
    """Index where the word before ``cursor`` begins (ASCII word boundaries)."""
    i = cursor
    while i > 0 and raw[i - 1] not in _WORD_CHARS:
        i -= 1
    while i > 0 and raw[i - 1] in _WORD_CHARS:
        i -= 1
    return i


def _forward_word_end(raw: str, cursor: int) -> int:
    """Index where the word at/after ``cursor`` ends (ASCII word boundaries)."""
    i = cursor
    n = len(raw)
    while i < n and raw[i] not in _WORD_CHARS:
        i += 1
    while i < n and raw[i] in _WORD_CHARS:
        i += 1
    return i


# ── per-action handlers ─────────────────────────────────────────────────────


def _reduce_insert_char(state: AppState, action: InsertChar) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    new_raw = raw[:cursor] + action.char + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor + len(action.char))


def _reduce_move_cursor_left(state: AppState, action: MoveCursorLeft) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor - 1)


def _reduce_move_cursor_right(state: AppState, action: MoveCursorRight) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor + 1)


def _reduce_move_cursor_home(state: AppState, action: MoveCursorHome) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=0)


def _reduce_move_cursor_end(state: AppState, action: MoveCursorEnd) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=len(state.filter.raw))


def _reduce_backspace(state: AppState, action: Backspace) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor == 0:
        return state  # no-op at the start of the line
    new_raw = raw[: cursor - 1] + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor - 1)


def _reduce_delete_char(state: AppState, action: DeleteChar) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor >= len(raw):
        return state  # no-op at the end of the line
    new_raw = raw[:cursor] + raw[cursor + 1:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_kill_line(state: AppState, action: KillLine) -> AppState:
    cursor = state.filter.cursor
    if cursor >= len(state.filter.raw):
        return state  # no-op: nothing after the cursor to kill
    return _with_filter(state, raw=state.filter.raw[:cursor], cursor=cursor)


def _reduce_unix_line_discard(state: AppState, action: UnixLineDiscard) -> AppState:
    cursor = state.filter.cursor
    if cursor == 0:
        return state  # no-op: nothing before the cursor to discard
    return _with_filter(state, raw=state.filter.raw[cursor:], cursor=0)


def _reduce_kill_word(state: AppState, action: KillWord) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    end = _forward_word_end(raw, cursor)
    if end == cursor:
        return state  # no-op: no word ahead of the cursor
    new_raw = raw[:cursor] + raw[end:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_backward_kill_word(state: AppState, action: BackwardKillWord) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    start = _backward_word_start(raw, cursor)
    if start == cursor:
        return state  # no-op: no word behind the cursor
    new_raw = raw[:start] + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=start)


def _reduce_autocomplete_bang(state: AppState, action: AutocompleteBang) -> AppState:
    # Tab / ctrl+i autocompletes a leading ! only while the "Tab to view
    # collisions" ghost is visible: filter.raw empty and at least one unresolved
    # collision exists. Otherwise it is a no-op — a non-empty buffer (incl. a !
    # already inserted by a prior Tab) or a collision-free dataset (spec §3.3).
    if not select_collision_ghost_visible(state):
        return state
    return _with_filter(state, raw="!", cursor=1)


def _reduce_redraw(state: AppState, action: Redraw) -> AppState:
    return state  # ctrl+l re-renders only; never mutates state (spec S5.1)


def _reduce_clear_filter(state: AppState, action: ClearFilter) -> AppState:
    if state.filter.raw == "":
        return state  # no-op: filter already empty (cursor is clamped to 0)
    # Esc clears the filter AND returns the browse view to the top: selection to
    # the first restored row, scroll to 0. This is the deliberate "clear filter"
    # gesture, distinct from incremental backspacing which preserves the place
    # via the anchored clamp in _with_filter.
    cleared = replace(state, filter=_derive_filter(raw="", cursor=0))
    visible = select_visible_rows(cleared)
    first_ordinal = visible[0].ordinal if visible else None
    return replace(
        cleared,
        selection=SelectionState(selected_ordinal=first_ordinal, scroll_offset=0),
    )


def _reduce_move_selection_up(state: AppState, action: MoveSelectionUp) -> AppState:
    return _move_selection(state, -1)


def _reduce_move_selection_down(state: AppState, action: MoveSelectionDown) -> AppState:
    return _move_selection(state, 1)


def _reduce_page_up(state: AppState, action: PageUp) -> AppState:
    return _page_selection(state, -1)


def _reduce_page_down(state: AppState, action: PageDown) -> AppState:
    return _page_selection(state, 1)


def _reduce_accept_line(state: AppState, action: AcceptLine) -> AppState:
    """Enter edit mode on the selected row (BROWSING ``Enter``, spec §7.1 / FR15).

    Initializes ``edit`` for the selected mapping: the buffer seeds with the
    literal ``target_value`` (or empty when there is no override), the cursor
    sits at the buffer end, focus is the token input, and source navigation is
    cleared. With no selected row this is a no-op.
    """
    selected = state.selection.selected_ordinal
    if selected is None:
        return state
    mapping = next(m for m in state.mappings if m.ordinal == selected)
    buffer = "" if mapping.target_value is None else mapping.target_value
    edit = EditState(
        mapping_ordinal=selected,
        buffer=buffer,
        cursor=len(buffer),
        focus_region=FocusRegion.TOKEN_INPUT,
        source_pointer_index=None,
        source_entry_buffer=None,
        validation=_edit_validation(state.config, buffer, mapping),
        max_length_flash_until=None,
    )
    return replace(state, mode=Mode.EDITING, edit=edit)


_HANDLERS = {
    InsertChar: _reduce_insert_char,
    MoveCursorLeft: _reduce_move_cursor_left,
    MoveCursorRight: _reduce_move_cursor_right,
    MoveCursorHome: _reduce_move_cursor_home,
    MoveCursorEnd: _reduce_move_cursor_end,
    Backspace: _reduce_backspace,
    DeleteChar: _reduce_delete_char,
    KillLine: _reduce_kill_line,
    UnixLineDiscard: _reduce_unix_line_discard,
    KillWord: _reduce_kill_word,
    BackwardKillWord: _reduce_backward_kill_word,
    AutocompleteBang: _reduce_autocomplete_bang,
    Redraw: _reduce_redraw,
    ClearFilter: _reduce_clear_filter,
    MoveSelectionUp: _reduce_move_selection_up,
    MoveSelectionDown: _reduce_move_selection_down,
    PageUp: _reduce_page_up,
    PageDown: _reduce_page_down,
    AcceptLine: _reduce_accept_line,
}


# ── EDITING mode: token input, ghost text, validation (spec §7) ───────────────

# Fixed 150ms "burst" window for the max-length flash (spec §7.6). While
# `now < edit.max_length_flash_until` the renderer draws the capped icon and
# footer error reverse-video (burst); afterwards they render in the ordinary
# held INVALID style until the error clears. Not configurable via `config`; the
# deadline is a render-time marker, not a clearing deadline (spec §2.1), and
# `now` is injectable for deterministic tests.
_BURST_DURATION = 0.150


def _edited_mapping(state: AppState) -> Mapping:
    ordinal = state.edit.mapping_ordinal
    return next(m for m in state.mappings if m.ordinal == ordinal)


def _edit_validation(
    config: AppConfig, buffer: str, mapping: Mapping
) -> ValidationState:
    """Policy validation stored for the live edit buffer (spec §7.5 / FR19).

    An empty buffer is ghost-only: it carries no concrete value to validate, so
    it stores ``EMPTY`` (no icon, no error) and never shows the submit affordance
    (frames 4/9). A non-empty buffer is the concrete value
    (:func:`select_concrete_value`) handed to ``config.target_policy.validate``.
    """
    if buffer == "":
        return ValidationState(status="EMPTY", icon=None, error_message=None)
    context = TargetValidationContext(
        is_concrete_buffer=True,
        is_ghost_only_default=False,
        mapping=mapping,
    )
    return config.target_policy.validate(buffer, context)


def _exit_source_list(state: AppState) -> AppState:
    """Return focus to ``TOKEN_INPUT``, clearing source navigation (spec §5.1).

    Every edit-input text mutation made from ``SOURCE_LIST`` first exits source
    navigation. A no-op (same state object) when already in ``TOKEN_INPUT``.
    """
    edit = state.edit
    if edit.focus_region != FocusRegion.SOURCE_LIST:
        return state
    return replace(
        state,
        edit=replace(
            edit,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        ),
    )


def _apply_edit_buffer(
    state: AppState, mapping: Mapping, buffer: str, cursor: int
) -> AppState:
    """Commit an accepted edit-buffer change: clamp cursor, validate, clear flash.

    Shared post-mutation sequence for every accepted token-input edit (spec §5.1
    / §7.2): the cursor is clamped into ``[0, len(buffer)]``, ``edit.validation``
    is recomputed, source navigation is cleared, and ``max_length_flash_until``
    is cleared because an accepted change supersedes the transient flash (FR20).
    """
    edit = state.edit
    cursor = max(0, min(cursor, len(buffer)))
    return replace(
        state,
        edit=replace(
            edit,
            buffer=buffer,
            cursor=cursor,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
            validation=_edit_validation(state.config, buffer, mapping),
            max_length_flash_until=None,
        ),
    )


def _autofill_source_pointer(
    state: AppState,
    mapping: Mapping,
    index: int,
    source_entry_buffer: str,
) -> AppState:
    """Point at active source ``index`` and autofill the buffer from it (spec §7.4 / FR21).

    Enters/stays in ``SOURCE_LIST`` with ``source_pointer_index = index`` and
    ``source_entry_buffer`` preserving the pre-navigation token buffer, then
    autofills ``edit.buffer`` with the pointed source's effective value
    (:func:`select_source_pointer_value`), moves the cursor to the buffer end,
    revalidates, and clears the transient max-length flash (a source-navigation
    event supersedes it, spec §7.5).
    """
    pointer_edit = replace(
        state.edit,
        focus_region=FocusRegion.SOURCE_LIST,
        source_pointer_index=index,
        source_entry_buffer=source_entry_buffer,
    )
    pointed = replace(state, edit=pointer_edit)
    buffer = select_source_pointer_value(pointed, mapping)
    return replace(
        pointed,
        edit=replace(
            pointer_edit,
            buffer=buffer,
            cursor=len(buffer),
            validation=_edit_validation(state.config, buffer, mapping),
            max_length_flash_until=None,
        ),
    )


def _restore_token_input(state: AppState, mapping: Mapping) -> AppState:
    """Leave ``SOURCE_LIST`` above the first / below the last source (spec §7.4 / FR21).

    Restores ``edit.buffer`` from ``source_entry_buffer`` (the value from just
    before source navigation began), clears ``source_pointer_index`` and
    ``source_entry_buffer``, returns focus to ``TOKEN_INPUT``, moves the cursor to
    the buffer end, revalidates, and clears the transient max-length flash.
    """
    edit = state.edit
    buffer = edit.source_entry_buffer or ""
    return replace(
        state,
        edit=replace(
            edit,
            buffer=buffer,
            cursor=len(buffer),
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
            validation=_edit_validation(state.config, buffer, mapping),
            max_length_flash_until=None,
        ),
    )


def _move_source_pointer(state: AppState, direction: int) -> AppState:
    """Move the source pointer up (``-1``) or down (``+1``) per spec §7.4 (FR21).

    From ``TOKEN_INPUT`` this enters ``SOURCE_LIST``: ``↓`` points at the first
    active source, ``↑`` at the last, saving the token buffer into
    ``source_entry_buffer`` first. Within ``SOURCE_LIST`` the pointer steps by one;
    stepping above the first source or below the last restores the token buffer
    and returns focus to ``TOKEN_INPUT``. Every move autofills the buffer from the
    pointed source and revalidates. With no active sources this is a no-op.
    """
    edit = state.edit
    mapping = _edited_mapping(state)
    active = select_active_sources(mapping)
    if not active:
        return state  # nothing navigable

    if edit.focus_region == FocusRegion.TOKEN_INPUT:
        index = 0 if direction > 0 else len(active) - 1
        return _autofill_source_pointer(state, mapping, index, edit.buffer)

    new_index = edit.source_pointer_index + direction
    if new_index < 0 or new_index >= len(active):
        return _restore_token_input(state, mapping)
    return _autofill_source_pointer(state, mapping, new_index, edit.source_entry_buffer)


def _reduce_editing_move_selection_up(
    state: AppState, action: MoveSelectionUp, now: Optional[float]
) -> AppState:
    return _move_source_pointer(state, -1)


def _reduce_editing_move_selection_down(
    state: AppState, action: MoveSelectionDown, now: Optional[float]
) -> AppState:
    return _move_source_pointer(state, 1)


def _reduce_editing_insert_char(
    state: AppState, action: InsertChar, now: Optional[float]
) -> AppState:
    """Streaming insert of a printable character (spec §7.2 / FR18–FR20).

    The character is inserted at the cursor; an over-limit candidate (display
    width beyond ``max_token_length``) is discarded, arms the flash, and stores
    the policy's over-limit error/icon for the immediate render (FR20). Invalid
    but in-bounds characters insert and surface their policy error (FR19).
    """
    state = _exit_source_list(state)
    edit = state.edit
    mapping = _edited_mapping(state)
    cursor = edit.cursor
    buffer = edit.buffer
    candidate = buffer[:cursor] + action.char + buffer[cursor:]

    if len(candidate) > state.config.target_policy.max_token_length:
        context = TargetValidationContext(
            is_concrete_buffer=True,
            is_ghost_only_default=False,
            mapping=mapping,
        )
        validation = state.config.target_policy.validate(candidate, context)
        # Arm the burst: overwrite any prior deadline with a fresh 150ms window
        # (§7.6 — repeated over-limit keystrokes reset rather than stack it).
        flash_until = (time.time() if now is None else now) + _BURST_DURATION
        return replace(
            state,
            edit=replace(
                edit,
                focus_region=FocusRegion.TOKEN_INPUT,
                validation=validation,
                max_length_flash_until=flash_until,
            ),
        )

    return _apply_edit_buffer(state, mapping, candidate, cursor + len(action.char))


def _reduce_editing_backspace(
    state: AppState, action: Backspace, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    if edit.cursor == 0:
        return state  # no-op at the start of the buffer (spec §7.2)
    mapping = _edited_mapping(state)
    cursor = edit.cursor
    new_buffer = edit.buffer[: cursor - 1] + edit.buffer[cursor:]
    return _apply_edit_buffer(state, mapping, new_buffer, cursor - 1)


def _reduce_editing_delete_char(
    state: AppState, action: DeleteChar, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    if edit.cursor >= len(edit.buffer):
        return state  # no-op at the end of the buffer
    mapping = _edited_mapping(state)
    cursor = edit.cursor
    new_buffer = edit.buffer[:cursor] + edit.buffer[cursor + 1:]
    return _apply_edit_buffer(state, mapping, new_buffer, cursor)


def _reduce_editing_kill_line(
    state: AppState, action: KillLine, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    if edit.cursor >= len(edit.buffer):
        return state
    mapping = _edited_mapping(state)
    return _apply_edit_buffer(state, mapping, edit.buffer[: edit.cursor], edit.cursor)


def _reduce_editing_unix_line_discard(
    state: AppState, action: UnixLineDiscard, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    if edit.cursor == 0:
        return state
    mapping = _edited_mapping(state)
    return _apply_edit_buffer(state, mapping, edit.buffer[edit.cursor:], 0)


def _reduce_editing_kill_word(
    state: AppState, action: KillWord, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    end = _forward_word_end(edit.buffer, edit.cursor)
    if end == edit.cursor:
        return state
    mapping = _edited_mapping(state)
    new_buffer = edit.buffer[: edit.cursor] + edit.buffer[end:]
    return _apply_edit_buffer(state, mapping, new_buffer, edit.cursor)


def _reduce_editing_backward_kill_word(
    state: AppState, action: BackwardKillWord, now: Optional[float]
) -> AppState:
    state = _exit_source_list(state)
    edit = state.edit
    start = _backward_word_start(edit.buffer, edit.cursor)
    if start == edit.cursor:
        return state
    mapping = _edited_mapping(state)
    new_buffer = edit.buffer[:start] + edit.buffer[edit.cursor:]
    return _apply_edit_buffer(state, mapping, new_buffer, start)


def _reduce_editing_cursor_left(
    state: AppState, action: MoveCursorLeft, now: Optional[float]
) -> AppState:
    edit = state.edit
    if edit.focus_region != FocusRegion.TOKEN_INPUT or edit.cursor == 0:
        return state  # clamp at 0; no-op in source list (spec §5.1)
    return replace(state, edit=replace(edit, cursor=edit.cursor - 1))


def _reduce_editing_cursor_right(
    state: AppState, action: MoveCursorRight, now: Optional[float]
) -> AppState:
    edit = state.edit
    if edit.focus_region != FocusRegion.TOKEN_INPUT or edit.cursor >= len(edit.buffer):
        return state  # clamp at buffer end; no-op in source list (spec §5.1)
    return replace(state, edit=replace(edit, cursor=edit.cursor + 1))


def _reduce_editing_cursor_home(
    state: AppState, action: MoveCursorHome, now: Optional[float]
) -> AppState:
    edit = state.edit
    if edit.focus_region != FocusRegion.TOKEN_INPUT or edit.cursor == 0:
        return state
    return replace(state, edit=replace(edit, cursor=0))


def _reduce_editing_cursor_end(
    state: AppState, action: MoveCursorEnd, now: Optional[float]
) -> AppState:
    edit = state.edit
    if edit.focus_region != FocusRegion.TOKEN_INPUT or edit.cursor == len(edit.buffer):
        return state
    return replace(state, edit=replace(edit, cursor=len(edit.buffer)))


def _reduce_editing_redraw(
    state: AppState, action: Redraw, now: Optional[float]
) -> AppState:
    return state  # ctrl+l re-renders only; never mutates state (spec §5.1)


def _reduce_editing_accept_line(
    state: AppState, action: AcceptLine, now: Optional[float]
) -> AppState:
    """Submit the edit, committing the buffer to the target (spec §4.2 / FR22–FR23).

    Enter commits only when validation is ``VALID`` and the buffer is non-empty
    (FR18/FR22); otherwise it is a no-op — the mode stays ``EDITING`` and the
    validation error remains visible. On commit the concrete value
    (:func:`select_concrete_value`, the buffer for a non-empty edit) is written
    literally to ``mapping.target_value`` and ``edit`` is cleared.

    If the commit resolves the final outstanding collision — the committed
    collision count was positive before and is zero after — the app enters the
    accept confirmation with ``kind = ACCEPT`` and ``choice = NO`` (FR23, spec
    §9). Submitting over an already collision-free dataset does NOT enter
    confirmation (nothing "became zero because of the commit"); the reviewer
    reaches accept confirmation manually via ``ctrl+s``. Otherwise the app
    returns to ``BROWSING`` (FR16): no editing transition ever mutates
    ``filter.*`` or ``selection.selected_ordinal`` (source navigation moves the
    source pointer, not the row selection), so the pre-edit browsing context —
    filter text and the selection on the edited row — is already intact.
    """
    edit = state.edit
    if edit.validation.status != "VALID" or edit.buffer == "":
        return state  # FR18: no commit; the error stays and the mode is unchanged
    mapping = _edited_mapping(state)
    concrete = select_concrete_value(state, mapping)
    new_mappings = [
        replace(m, target_value=concrete) if m.ordinal == edit.mapping_ordinal else m
        for m in state.mappings
    ]
    pre_count = select_unresolved_collision_count(state.mappings)
    post_count = select_unresolved_collision_count(new_mappings)
    committed = replace(state, mappings=new_mappings, edit=None)

    if pre_count > 0 and post_count == 0:
        return replace(
            committed,
            mode=Mode.CONFIRMING,
            selection=replace(committed.selection, scroll_offset=0),
            confirmation=replace(
                committed.confirmation,
                kind=ConfirmationKind.ACCEPT,
                choice=ConfirmationChoice.NO,
            ),
        )
    return replace(committed, mode=Mode.BROWSING)


def _reduce_editing_clear_filter(
    state: AppState, action: ClearFilter, now: Optional[float]
) -> AppState:
    """Cancel the edit, discarding the buffer and returning to BROWSING (spec §4.2 / FR16).

    Esc — and ctrl+c, which the loop routes here in ``EDITING`` — discards
    ``edit`` entirely and returns to ``BROWSING``. The filter and the selection
    are left untouched because no editing transition ever mutates ``filter.*`` or
    ``selection.selected_ordinal``, so the pre-edit browsing context is restored
    exactly as it was on entry.
    """
    return replace(state, mode=Mode.BROWSING, edit=None)


_EDITING_HANDLERS = {
    InsertChar: _reduce_editing_insert_char,
    MoveSelectionUp: _reduce_editing_move_selection_up,
    MoveSelectionDown: _reduce_editing_move_selection_down,
    Backspace: _reduce_editing_backspace,
    DeleteChar: _reduce_editing_delete_char,
    KillLine: _reduce_editing_kill_line,
    UnixLineDiscard: _reduce_editing_unix_line_discard,
    KillWord: _reduce_editing_kill_word,
    BackwardKillWord: _reduce_editing_backward_kill_word,
    MoveCursorLeft: _reduce_editing_cursor_left,
    MoveCursorRight: _reduce_editing_cursor_right,
    MoveCursorHome: _reduce_editing_cursor_home,
    MoveCursorEnd: _reduce_editing_cursor_end,
    Redraw: _reduce_editing_redraw,
    AcceptLine: _reduce_editing_accept_line,
    ClearFilter: _reduce_editing_clear_filter,
}


def reduce(state: AppState, action: Action, now: Optional[float] = None) -> AppState:
    """Pure dispatch: route ``action`` to its handler, returning new state.

    Dispatch is mode-aware — ``EDITING`` routes to the token-input handlers
    (spec §7), every other mode to the browsing/selection handlers. Every handler
    returns a fresh frozen :class:`AppState`; the input ``state`` is never
    mutated. An unrecognised action (in the active mode) is a no-op and the same
    state is returned unchanged (FR30). ``now`` injects the clock used by the
    over-limit flash (FR20); it defaults to wall-clock time.
    """
    if state.mode == Mode.EDITING and state.edit is not None:
        handler = _EDITING_HANDLERS.get(type(action))
        if handler is None:
            return state
        return handler(state, action, now)
    handler = _HANDLERS.get(type(action))
    if handler is None:
        return state
    return handler(state, action)
