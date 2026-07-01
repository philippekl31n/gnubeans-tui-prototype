"""
Reducer module: pure state transitions and application initialization.
"""



from dataclasses import replace
from typing import Optional
import shutil

from mapping_resolution_tui.actions import (
    Action,
    AutocompleteBang,
    Backspace,
    BackwardKillWord,
    Escape,
    AcceptLine,
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
    select_body_capacity,
    select_collision_ghost_visible,
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
    FilterState,
    Mapping,
    Mode,
    ResultState,
    SelectionState,
    TerminalState,
)

# ASCII word characters for word-wise kill operations (spec S5.1).
_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789_-"
)

_FLASH_DURATION = 0.150


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


def _validate_edit(state: AppState, edit: EditState, new_buffer: str) -> EditState:
    from mapping_resolution_tui.state import TargetValidationContext
    from mapping_resolution_tui.selectors import select_default_source_value
    mapping = next(m for m in state.mappings if m.ordinal == edit.mapping_ordinal)
    
    effective_text = new_buffer
    if mapping.target_value is None:
        default_val = select_default_source_value(mapping)
        if default_val.startswith(new_buffer):
            effective_text = default_val
        
    is_empty_target = mapping.target_value is None and new_buffer == ""
    context = TargetValidationContext(
        is_concrete_buffer=not is_empty_target,
        is_ghost_only_default=is_empty_target,
        mapping=mapping,
    )
    validation = state.config.target_policy.validate(effective_text, context)
    return replace(edit, buffer=new_buffer, validation=validation, max_length_flash_until=None)

def _reduce_insert_char(state: AppState, action: InsertChar, now: Optional[float] = None) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        from mapping_resolution_tui.state import FocusRegion, TargetValidationContext
        new_buffer = edit.buffer[:edit.cursor] + action.char + edit.buffer[edit.cursor:]
        if len(new_buffer) > state.config.target_policy.max_token_length:
            mapping = next(m for m in state.mappings if m.ordinal == edit.mapping_ordinal)
            context = TargetValidationContext(
                is_concrete_buffer=True,
                is_ghost_only_default=False,
                mapping=mapping,
            )
            validation = state.config.target_policy.validate(new_buffer, context)
            import time
            current_time = time.time() if now is None else now
            flash_until = current_time + _FLASH_DURATION
            return replace(
                state,
                edit=replace(
                    edit,
                    validation=validation,
                    max_length_flash_until=flash_until,
                ),
            )
            
        new_edit = replace(
            edit,
            cursor=edit.cursor + len(action.char),
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
            max_length_flash_until=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    raw = state.filter.raw
    new_raw = raw[:cursor] + action.char + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor + len(action.char))


def _reduce_move_cursor_left(state: AppState, action: MoveCursorLeft) -> AppState:
    if state.mode == Mode.EDITING:
        return replace(state, edit=replace(state.edit, cursor=max(0, state.edit.cursor - 1)))
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor - 1)


def _reduce_move_cursor_right(state: AppState, action: MoveCursorRight) -> AppState:
    if state.mode == Mode.EDITING:
        return replace(state, edit=replace(state.edit, cursor=min(len(state.edit.buffer), state.edit.cursor + 1)))
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor + 1)


def _reduce_move_cursor_home(state: AppState, action: MoveCursorHome) -> AppState:
    if state.mode == Mode.EDITING:
        return replace(state, edit=replace(state.edit, cursor=0))
    return _with_filter(state, raw=state.filter.raw, cursor=0)


def _reduce_move_cursor_end(state: AppState, action: MoveCursorEnd) -> AppState:
    if state.mode == Mode.EDITING:
        return replace(state, edit=replace(state.edit, cursor=len(state.edit.buffer)))
    return _with_filter(state, raw=state.filter.raw, cursor=len(state.filter.raw))


def _reduce_backspace(state: AppState, action: Backspace) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        if edit.cursor == 0:
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[:edit.cursor - 1] + edit.buffer[edit.cursor:]
        new_edit = replace(
            edit,
            cursor=edit.cursor - 1,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor == 0:
        return state  # no-op at the start of the line
    new_raw = raw[: cursor - 1] + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor - 1)


def _reduce_delete_char(state: AppState, action: DeleteChar) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        if edit.cursor >= len(edit.buffer):
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[:edit.cursor] + edit.buffer[edit.cursor + 1:]
        new_edit = replace(
            edit,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor >= len(raw):
        return state  # no-op at the end of the line
    new_raw = raw[:cursor] + raw[cursor + 1:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_kill_line(state: AppState, action: KillLine) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        if edit.cursor >= len(edit.buffer):
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[:edit.cursor]
        new_edit = replace(
            edit,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    if cursor >= len(state.filter.raw):
        return state  # no-op: nothing after the cursor to kill
    return _with_filter(state, raw=state.filter.raw[:cursor], cursor=cursor)


def _reduce_unix_line_discard(state: AppState, action: UnixLineDiscard) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        if edit.cursor == 0:
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[edit.cursor:]
        new_edit = replace(
            edit,
            cursor=0,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    if cursor == 0:
        return state  # no-op: nothing before the cursor to discard
    return _with_filter(state, raw=state.filter.raw[cursor:], cursor=0)


def _reduce_kill_word(state: AppState, action: KillWord) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        end = _forward_word_end(edit.buffer, edit.cursor)
        if end == edit.cursor:
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[:edit.cursor] + edit.buffer[end:]
        new_edit = replace(
            edit,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
    cursor = state.filter.cursor
    raw = state.filter.raw
    end = _forward_word_end(raw, cursor)
    if end == cursor:
        return state  # no-op: no word ahead of the cursor
    new_raw = raw[:cursor] + raw[end:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_backward_kill_word(state: AppState, action: BackwardKillWord) -> AppState:
    if state.mode == Mode.EDITING:
        edit = state.edit
        start = _backward_word_start(edit.buffer, edit.cursor)
        if start == edit.cursor:
            return state
        from mapping_resolution_tui.state import FocusRegion
        new_buffer = edit.buffer[:start] + edit.buffer[edit.cursor:]
        new_edit = replace(
            edit,
            cursor=start,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
        )
        return replace(state, edit=_validate_edit(state, new_edit, new_buffer))
        
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


def _reduce_escape(state: AppState, action: Escape) -> AppState:
    if state.mode == Mode.EDITING:
        # Cancel edit
        return replace(state, mode=Mode.BROWSING, edit=None)
        
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


def _reduce_accept_line(state: AppState, action: AcceptLine) -> AppState:
    if state.mode == Mode.BROWSING:
        visible = select_visible_rows(state)
        if not visible:
            return state
            
        selected_ordinal = state.selection.selected_ordinal
        mapping = next((m for m in visible if m.ordinal == selected_ordinal), None)
        if not mapping:
            return state
            
        from mapping_resolution_tui.state import EditState, FocusRegion, TargetValidationContext
        from mapping_resolution_tui.selectors import select_ghost_suffix
        # Initialize edit state with current target_value or empty string
        buffer_val = mapping.target_value if mapping.target_value is not None else ""
        
        from mapping_resolution_tui.selectors import select_default_source_value
        is_empty_target = mapping.target_value is None and buffer_val == ""
        effective_text = buffer_val
        if is_empty_target:
            effective_text = select_default_source_value(mapping)
            
        context = TargetValidationContext(
            is_concrete_buffer=not is_empty_target,
            is_ghost_only_default=is_empty_target,
            mapping=mapping,
        )
        validation = state.config.target_policy.validate(effective_text, context)
        
        return replace(
            state,
            mode=Mode.EDITING,
            edit=EditState(
                mapping_ordinal=selected_ordinal,
                buffer=buffer_val,
                cursor=len(buffer_val),
                focus_region=FocusRegion.TOKEN_INPUT,
                source_pointer_index=None,
                source_entry_buffer=None,
                validation=validation,
                max_length_flash_until=None,
            )
        )
    elif state.mode == Mode.EDITING:
        # Just validate for now, actual submit comes later
        return state
        
    return state


def _reduce_move_selection_up(state: AppState, action: MoveSelectionUp) -> AppState:
    return _move_selection(state, -1)


def _reduce_move_selection_down(state: AppState, action: MoveSelectionDown) -> AppState:
    return _move_selection(state, 1)


def _reduce_page_up(state: AppState, action: PageUp) -> AppState:
    return _page_selection(state, -1)


def _reduce_page_down(state: AppState, action: PageDown) -> AppState:
    return _page_selection(state, 1)


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
    Escape: _reduce_escape,
    AcceptLine: _reduce_accept_line,
    MoveSelectionUp: _reduce_move_selection_up,
    MoveSelectionDown: _reduce_move_selection_down,
    PageUp: _reduce_page_up,
    PageDown: _reduce_page_down,
}


def reduce(state: AppState, action: Action, now: Optional[float] = None) -> AppState:
    """Pure dispatch: route ``action`` to its handler, returning new state.

    Every handler returns a fresh frozen :class:`AppState`; the input ``state``
    is never mutated. An unrecognised action is a no-op and the same state is
    returned unchanged (FR30).
    """
    handler = _HANDLERS.get(type(action))
    if handler is None:
        return state
    if type(action) is InsertChar:
        return handler(state, action, now=now)
    return handler(state, action)
