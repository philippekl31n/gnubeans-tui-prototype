"""
Reducer module: pure state transitions and application initialization.
"""

from dataclasses import replace
from typing import Callable, Optional
import shutil
import time

from mapping_resolution_tui.events import InputEvent, KeyEvent
from mapping_resolution_tui.selectors import (
    parse_filter,
    select_body_capacity,
    select_collision_ghost_visible,
    select_default_source_value,
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


# ── edit helpers ─────────────────────────────────────────────────────────────


def _validate_edit(state: AppState, edit: EditState, new_buffer: str) -> EditState:
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
    return replace(edit, buffer=new_buffer, validation=validation)


# Duration a rejected over-limit character's error stays visible before the
# next accepted edit clears it (FR20). Golden tests never depend on this
# elapsing — only on the immediate post-discard render.
_FLASH_DURATION = 1.0


def _apply_edit_buffer(state: AppState, new_buffer: str, new_cursor: int) -> AppState:
    """Commit an accepted edit-buffer mutation.

    Shared post-mutation sequence for every EDITING handler that changes the
    buffer: clamp the cursor into range, recompute validation, drop any
    in-progress source-list navigation, reset focus to the token input, and
    clear the max-length flash since an accepted change supersedes it (FR20).
    """
    edit = state.edit
    cursor = max(0, min(new_cursor, len(new_buffer)))
    new_edit = replace(
        edit,
        cursor=cursor,
        focus_region=FocusRegion.TOKEN_INPUT,
        source_pointer_index=None,
        source_entry_buffer=None,
        max_length_flash_until=None,
    )
    return replace(state, edit=_validate_edit(state, new_edit, new_buffer))


# ── BROWSING filter handlers ──────────────────────────────────────────────────


def _reduce_filter_insert_char(state: AppState, char: str, now: Optional[float]) -> AppState:
    # `now` is unused here: the filter buffer has no length cap/flash concept
    # (FR20 is EDITING-only). Accepted for signature parity with _MODE_INSERT.
    cursor = state.filter.cursor
    raw = state.filter.raw
    new_raw = raw[:cursor] + char + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor + len(char))


def _reduce_filter_cursor_left(state: AppState) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor - 1)


def _reduce_filter_cursor_right(state: AppState) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=state.filter.cursor + 1)


def _reduce_filter_cursor_home(state: AppState) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=0)


def _reduce_filter_cursor_end(state: AppState) -> AppState:
    return _with_filter(state, raw=state.filter.raw, cursor=len(state.filter.raw))


def _reduce_filter_backspace(state: AppState) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor == 0:
        return state  # no-op at the start of the line
    new_raw = raw[:cursor - 1] + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=cursor - 1)


def _reduce_filter_delete_char(state: AppState) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    if cursor >= len(raw):
        return state  # no-op at the end of the line
    new_raw = raw[:cursor] + raw[cursor + 1:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_filter_clear_after_cursor(state: AppState) -> AppState:
    cursor = state.filter.cursor
    if cursor >= len(state.filter.raw):
        return state  # no-op: nothing after the cursor to kill
    return _with_filter(state, raw=state.filter.raw[:cursor], cursor=cursor)


def _reduce_filter_clear_before_cursor(state: AppState) -> AppState:
    cursor = state.filter.cursor
    if cursor == 0:
        return state  # no-op: nothing before the cursor to discard
    return _with_filter(state, raw=state.filter.raw[cursor:], cursor=0)


def _reduce_filter_delete_next_word(state: AppState) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    end = _forward_word_end(raw, cursor)
    if end == cursor:
        return state  # no-op: no word ahead of the cursor
    new_raw = raw[:cursor] + raw[end:]
    return _with_filter(state, raw=new_raw, cursor=cursor)


def _reduce_filter_delete_prev_word(state: AppState) -> AppState:
    cursor = state.filter.cursor
    raw = state.filter.raw
    start = _backward_word_start(raw, cursor)
    if start == cursor:
        return state  # no-op: no word behind the cursor
    new_raw = raw[:start] + raw[cursor:]
    return _with_filter(state, raw=new_raw, cursor=start)


def _reduce_filter_autocomplete_bang(state: AppState) -> AppState:
    # Tab / ctrl+i autocompletes a leading ! only while the "Tab to view
    # collisions" ghost is visible: filter.raw empty and at least one unresolved
    # collision exists. Otherwise it is a no-op — a non-empty buffer (incl. a !
    # already inserted by a prior Tab) or a collision-free dataset (spec §3.3).
    if not select_collision_ghost_visible(state):
        return state
    return _with_filter(state, raw="!", cursor=1)


def _reduce_clear_filter(state: AppState) -> AppState:
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


def _reduce_enter_edit(state: AppState) -> AppState:
    visible = select_visible_rows(state)
    if not visible:
        return state

    selected_ordinal = state.selection.selected_ordinal
    mapping = next((m for m in visible if m.ordinal == selected_ordinal), None)
    if not mapping:
        return state

    buffer_val = mapping.target_value if mapping.target_value is not None else ""
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


# ── shared handlers ───────────────────────────────────────────────────────────


def _reduce_redraw(state: AppState) -> AppState:
    return state  # ctrl+l re-renders only; never mutates state (spec S5.1)


# ── BROWSING table/navigation handlers ───────────────────────────────────────


def _reduce_table_selection_up(state: AppState) -> AppState:
    return _move_selection(state, -1)


def _reduce_table_selection_down(state: AppState) -> AppState:
    return _move_selection(state, 1)


def _reduce_table_page_up(state: AppState) -> AppState:
    return _page_selection(state, -1)


def _reduce_table_page_down(state: AppState) -> AppState:
    return _page_selection(state, 1)


# ── EDITING token handlers ────────────────────────────────────────────────────


def _reduce_token_insert_char(state: AppState, char: str, now: Optional[float]) -> AppState:
    edit = state.edit
    new_buffer = edit.buffer[:edit.cursor] + char + edit.buffer[edit.cursor:]
    if len(new_buffer) > state.config.target_policy.max_token_length:
        # Over-limit: the character is discarded (buffer/cursor unchanged), but
        # the rejected candidate is still validated so the real policy error
        # ("24 chars max") surfaces immediately, and the flash timer arms (FR20).
        mapping = next(m for m in state.mappings if m.ordinal == edit.mapping_ordinal)
        context = TargetValidationContext(
            is_concrete_buffer=True,
            is_ghost_only_default=False,
            mapping=mapping,
        )
        validation = state.config.target_policy.validate(new_buffer, context)
        flash_until = (time.time() if now is None else now) + _FLASH_DURATION
        return replace(
            state,
            edit=replace(
                edit,
                focus_region=FocusRegion.TOKEN_INPUT,
                validation=validation,
                max_length_flash_until=flash_until,
            ),
        )
    return _apply_edit_buffer(state, new_buffer, edit.cursor + len(char))


def _reduce_token_cursor_left(state: AppState) -> AppState:
    return replace(state, edit=replace(state.edit, cursor=max(0, state.edit.cursor - 1)))


def _reduce_token_cursor_right(state: AppState) -> AppState:
    return replace(state, edit=replace(state.edit, cursor=min(len(state.edit.buffer), state.edit.cursor + 1)))


def _reduce_token_cursor_home(state: AppState) -> AppState:
    return replace(state, edit=replace(state.edit, cursor=0))


def _reduce_token_cursor_end(state: AppState) -> AppState:
    return replace(state, edit=replace(state.edit, cursor=len(state.edit.buffer)))


def _reduce_token_backspace(state: AppState) -> AppState:
    edit = state.edit
    if edit.cursor == 0:
        return state
    new_buffer = edit.buffer[:edit.cursor - 1] + edit.buffer[edit.cursor:]
    return _apply_edit_buffer(state, new_buffer, edit.cursor - 1)


def _reduce_token_delete_char(state: AppState) -> AppState:
    edit = state.edit
    if edit.cursor >= len(edit.buffer):
        return state
    new_buffer = edit.buffer[:edit.cursor] + edit.buffer[edit.cursor + 1:]
    return _apply_edit_buffer(state, new_buffer, edit.cursor)


def _reduce_token_clear_after_cursor(state: AppState) -> AppState:
    edit = state.edit
    if edit.cursor >= len(edit.buffer):
        return state
    return _apply_edit_buffer(state, edit.buffer[:edit.cursor], edit.cursor)


def _reduce_token_clear_before_cursor(state: AppState) -> AppState:
    edit = state.edit
    if edit.cursor == 0:
        return state
    return _apply_edit_buffer(state, edit.buffer[edit.cursor:], 0)


def _reduce_token_delete_next_word(state: AppState) -> AppState:
    edit = state.edit
    end = _forward_word_end(edit.buffer, edit.cursor)
    if end == edit.cursor:
        return state
    new_buffer = edit.buffer[:edit.cursor] + edit.buffer[end:]
    return _apply_edit_buffer(state, new_buffer, edit.cursor)


def _reduce_token_delete_prev_word(state: AppState) -> AppState:
    edit = state.edit
    start = _backward_word_start(edit.buffer, edit.cursor)
    if start == edit.cursor:
        return state
    new_buffer = edit.buffer[:start] + edit.buffer[edit.cursor:]
    return _apply_edit_buffer(state, new_buffer, start)


def _reduce_cancel_edit(state: AppState) -> AppState:
    return replace(state, mode=Mode.BROWSING, edit=None)


def _reduce_submit_edit(state: AppState) -> AppState:
    # TASK-008: submit path not yet implemented
    return state


# ── dispatch tables ───────────────────────────────────────────────────────────


_BROWSING_HANDLERS: dict[KeyEvent, Callable[[AppState], AppState]] = {
    KeyEvent.ESCAPE:             _reduce_clear_filter,
    KeyEvent.ENTER:              _reduce_enter_edit,
    KeyEvent.BACKSPACE:          _reduce_filter_backspace,
    KeyEvent.DELETE_CHAR:        _reduce_filter_delete_char,
    KeyEvent.CURSOR_LEFT:        _reduce_filter_cursor_left,
    KeyEvent.CURSOR_RIGHT:       _reduce_filter_cursor_right,
    KeyEvent.CURSOR_HOME:        _reduce_filter_cursor_home,
    KeyEvent.CURSOR_END:         _reduce_filter_cursor_end,
    KeyEvent.KILL_LINE:          _reduce_filter_clear_after_cursor,
    KeyEvent.UNIX_LINE_DISCARD:  _reduce_filter_clear_before_cursor,
    KeyEvent.KILL_WORD:          _reduce_filter_delete_next_word,
    KeyEvent.BACKWARD_KILL_WORD: _reduce_filter_delete_prev_word,
    KeyEvent.REDRAW:             _reduce_redraw,
    KeyEvent.TAB:                _reduce_filter_autocomplete_bang,
    KeyEvent.PAGE_UP:            _reduce_table_page_up,
    KeyEvent.PAGE_DOWN:          _reduce_table_page_down,
    KeyEvent.SELECTION_UP:       _reduce_table_selection_up,
    KeyEvent.SELECTION_DOWN:     _reduce_table_selection_down,
}

_EDITING_HANDLERS: dict[KeyEvent, Callable[[AppState], AppState]] = {
    KeyEvent.ESCAPE:             _reduce_cancel_edit,
    KeyEvent.ENTER:              _reduce_submit_edit,
    KeyEvent.BACKSPACE:          _reduce_token_backspace,
    KeyEvent.DELETE_CHAR:        _reduce_token_delete_char,
    KeyEvent.CURSOR_LEFT:        _reduce_token_cursor_left,
    KeyEvent.CURSOR_RIGHT:       _reduce_token_cursor_right,
    KeyEvent.CURSOR_HOME:        _reduce_token_cursor_home,
    KeyEvent.CURSOR_END:         _reduce_token_cursor_end,
    KeyEvent.KILL_LINE:          _reduce_token_clear_after_cursor,
    KeyEvent.UNIX_LINE_DISCARD:  _reduce_token_clear_before_cursor,
    KeyEvent.KILL_WORD:          _reduce_token_delete_next_word,
    KeyEvent.BACKWARD_KILL_WORD: _reduce_token_delete_prev_word,
    KeyEvent.REDRAW:             _reduce_redraw,
    # TAB → _reduce_token_autocomplete_suggestion (future)
    # SELECTION_UP/DOWN → source-list navigation (future)
    # PAGE_UP/DOWN → no-op in EDITING for now
}

# Top-level registry: adding CONFIRMING requires only a new dict + one entry here.
_MODE_HANDLERS: dict[Mode, dict[KeyEvent, Callable[[AppState], AppState]]] = {
    Mode.BROWSING: _BROWSING_HANDLERS,
    Mode.EDITING:  _EDITING_HANDLERS,
}

_MODE_INSERT: dict[Mode, Callable[[AppState, str, Optional[float]], AppState]] = {
    Mode.BROWSING: _reduce_filter_insert_char,
    Mode.EDITING:  _reduce_token_insert_char,
}


def reduce(state: AppState, event: InputEvent, now: Optional[float] = None) -> AppState:
    """Pure dispatch: route ``event`` to its handler, returning new state.

    Dispatch is mode-aware via ``_MODE_HANDLERS`` and ``_MODE_INSERT``.
    An unrecognised event (no handler in the active mode's table) is a no-op —
    the same ``state`` object is returned unchanged (FR30). ``now`` injects the
    clock used by the EDITING over-limit flash (FR20); it defaults to
    wall-clock time and is unused outside that one path.
    """
    if isinstance(event, str):
        insert = _MODE_INSERT.get(state.mode)
        return insert(state, event, now) if insert else state
    handler = _MODE_HANDLERS.get(state.mode, {}).get(event)
    return handler(state) if handler else state
