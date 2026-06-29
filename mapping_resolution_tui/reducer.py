"""
Reducer module: pure state transitions and application initialization.
"""



from dataclasses import replace
from typing import Optional
import shutil

from mapping_resolution_tui.actions import (
    Action,
    AutocompleteBang,
    ClearFilter,
    DeleteBackward,
    DeleteForward,
    DeleteWordBackward,
    DeleteWordForward,
    InsertCharacter,
    KillToEnd,
    KillToStart,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    MoveSelectionDown,
    MoveSelectionUp,
    PageDown,
    PageUp,
)
from mapping_resolution_tui.selectors import (
    parse_filter,
    select_body_capacity,
    select_collision_ghost_visible,
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
        filter=FilterState(raw="", collision_only=False, text="", cursor=0),
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


def reduce(state: AppState, action: Action) -> AppState:
    """Dispatch ``action`` to its handler and return a new immutable state.

    Unrecognised actions leave the state unchanged so that the caller may treat
    the returned object identity as "no transition occurred".
    """
    if isinstance(action, InsertCharacter):
        return _insert_character(state, action.char)
    if isinstance(action, MoveCursorLeft):
        return _with_raw(state, state.filter.raw, state.filter.cursor - 1)
    if isinstance(action, MoveCursorRight):
        return _with_raw(state, state.filter.raw, state.filter.cursor + 1)
    if isinstance(action, MoveCursorHome):
        return _with_raw(state, state.filter.raw, 0)
    if isinstance(action, MoveCursorEnd):
        return _with_raw(state, state.filter.raw, len(state.filter.raw))
    if isinstance(action, DeleteBackward):
        return _delete_backward(state)
    if isinstance(action, DeleteForward):
        return _delete_forward(state)
    if isinstance(action, KillToEnd):
        return _kill_to_end(state)
    if isinstance(action, KillToStart):
        return _kill_to_start(state)
    if isinstance(action, DeleteWordBackward):
        return _delete_word_backward(state)
    if isinstance(action, DeleteWordForward):
        return _delete_word_forward(state)
    if isinstance(action, ClearFilter):
        return _clear_filter(state)
    if isinstance(action, AutocompleteBang):
        return _autocomplete_bang(state)
    if isinstance(action, MoveSelectionUp):
        return _move_selection(state, -1)
    if isinstance(action, MoveSelectionDown):
        return _move_selection(state, +1)
    if isinstance(action, PageUp):
        return _page_selection(state, -1)
    if isinstance(action, PageDown):
        return _page_selection(state, +1)
    return state


_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def _with_raw(state: AppState, raw: str, cursor: int) -> AppState:
    """Return ``state`` with a new ``FilterState`` derived from ``raw``.

    ``filter.raw`` is the single editable buffer (spec §3.3): ``cursor`` is
    clamped to ``[0, len(raw)]`` and ``collision_only`` / ``text`` are re-derived
    from ``raw`` on every mutation. Selection and scroll are then clamped so they
    never point at a row the new filter hides (spec §3.4 / §5.1).
    """
    cursor = max(0, min(cursor, len(raw)))
    collision_only, text = parse_filter(raw)
    new_filter = FilterState(
        raw=raw,
        collision_only=collision_only,
        text=text,
        cursor=cursor,
    )
    return _clamp_scroll(_clamp_selection(replace(state, filter=new_filter)))


def _clamp_selection(state: AppState) -> AppState:
    """Clamp ``selection.selected_ordinal`` to the rows the filter leaves visible.

    Per spec §3.4: an empty result clears the selection; otherwise a selected
    ordinal that the filter has hidden clamps to the first visible row, while a
    still-visible selection is left untouched.
    """
    visible = select_visible_rows(state)
    if not visible:
        selected = None
    elif state.selection.selected_ordinal in {m.ordinal for m in visible}:
        selected = state.selection.selected_ordinal
    else:
        selected = visible[0].ordinal

    if selected == state.selection.selected_ordinal:
        return state
    return replace(state, selection=replace(state.selection, selected_ordinal=selected))


def _clamp_scroll(state: AppState) -> AppState:
    """Clamp ``selection.scroll_offset`` to ``[0, max(0, len(visible) - capacity)]``.

    Spec §3.4: ``scrollOffset = clamp(scrollOffset, 0, max(0, visibleRows.length -
    bodyCapacity))``. A filter that shrinks the visible list must never leave the
    scroll window pointing past the end of it.
    """
    visible = select_visible_rows(state)
    capacity = select_body_capacity(state.terminal.height)
    max_offset = max(0, len(visible) - capacity)
    new_offset = max(0, min(state.selection.scroll_offset, max_offset))
    if new_offset == state.selection.scroll_offset:
        return state
    return replace(state, selection=replace(state.selection, scroll_offset=new_offset))


def _move_selection(state: AppState, delta: int) -> AppState:
    """Move ``selected_ordinal`` by ``delta`` rows within ``visibleRows`` (§8.3).

    Movement is clamped at the first and last visible row; with no visible rows
    or at a clamped end the state is returned unchanged so the loop can treat it
    as a no-op transition.
    """
    visible = select_visible_rows(state)
    if not visible:
        return state
    ordinals = [m.ordinal for m in visible]
    try:
        index = ordinals.index(state.selection.selected_ordinal)
    except ValueError:
        index = 0
    new_index = max(0, min(index + delta, len(ordinals) - 1))
    new_ordinal = ordinals[new_index]
    if new_ordinal == state.selection.selected_ordinal:
        return state
    return replace(
        state, selection=replace(state.selection, selected_ordinal=new_ordinal)
    )


def _page_selection(state: AppState, direction: int) -> AppState:
    """Page ``scrollOffset`` by one body capacity and re-anchor selection (§8.5).

    ``PgDn`` clamps ``scrollOffset`` to ``maxOffset`` and ``PgUp`` clamps it to 0;
    after paging the row at the new scroll offset becomes the selected (first
    visible) row. A no-op when no rows are visible or nothing would change.
    """
    visible = select_visible_rows(state)
    if not visible:
        return state
    capacity = select_body_capacity(state.terminal.height)
    page_size = max(1, capacity)
    max_offset = max(0, len(visible) - capacity)
    if direction > 0:
        new_offset = min(state.selection.scroll_offset + page_size, max_offset)
    else:
        new_offset = max(state.selection.scroll_offset - page_size, 0)
    new_ordinal = visible[new_offset].ordinal
    new_selection = SelectionState(
        selected_ordinal=new_ordinal, scroll_offset=new_offset
    )
    if new_selection == state.selection:
        return state
    return replace(state, selection=new_selection)


def _autocomplete_bang(state: AppState) -> AppState:
    """Autocomplete a leading ``!`` collision metafilter (``Tab`` / ``ctrl+i``).

    A no-op unless the ``Tab to view collisions`` ghost is visible — that is,
    ``filter.raw`` is empty and at least one unresolved collision exists. When it
    fires it inserts ``!`` at index 0 and sets ``filter.cursor = 1`` (spec §3.3).
    """
    if not select_collision_ghost_visible(state):
        return state
    return _with_raw(state, "!", 1)


def _insert_character(state: AppState, char: str) -> AppState:
    f = state.filter
    raw = f.raw[: f.cursor] + char + f.raw[f.cursor :]
    return _with_raw(state, raw, f.cursor + len(char))


def _clear_filter(state: AppState) -> AppState:
    if state.filter.raw == "":
        return state
    return _with_raw(state, "", 0)


def _delete_backward(state: AppState) -> AppState:
    f = state.filter
    if f.cursor == 0:
        return state
    raw = f.raw[: f.cursor - 1] + f.raw[f.cursor :]
    return _with_raw(state, raw, f.cursor - 1)


def _delete_forward(state: AppState) -> AppState:
    f = state.filter
    if f.cursor >= len(f.raw):
        return state
    raw = f.raw[: f.cursor] + f.raw[f.cursor + 1 :]
    return _with_raw(state, raw, f.cursor)


def _kill_to_end(state: AppState) -> AppState:
    f = state.filter
    if f.cursor >= len(f.raw):
        return state
    return _with_raw(state, f.raw[: f.cursor], f.cursor)


def _kill_to_start(state: AppState) -> AppState:
    f = state.filter
    if f.cursor == 0:
        return state
    return _with_raw(state, f.raw[f.cursor :], 0)


def _delete_word_backward(state: AppState) -> AppState:
    """Skip non-word chars before the caret, then delete the previous word run."""
    f = state.filter
    raw, cursor = f.raw, f.cursor
    start = cursor
    while start > 0 and raw[start - 1] not in _WORD_CHARS:
        start -= 1
    while start > 0 and raw[start - 1] in _WORD_CHARS:
        start -= 1
    if start == cursor:
        return state
    return _with_raw(state, raw[:start] + raw[cursor:], start)


def _delete_word_forward(state: AppState) -> AppState:
    """Skip non-word chars at/after the caret, then delete the next word run."""
    f = state.filter
    raw, cursor = f.raw, f.cursor
    end = cursor
    while end < len(raw) and raw[end] not in _WORD_CHARS:
        end += 1
    while end < len(raw) and raw[end] in _WORD_CHARS:
        end += 1
    if end == cursor:
        return state
    return _with_raw(state, raw[:cursor] + raw[end:], cursor)
