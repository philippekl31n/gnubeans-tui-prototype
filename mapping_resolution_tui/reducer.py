"""
Reducer module: pure state transitions and application initialization.
"""



from dataclasses import replace
from typing import Optional
import shutil

from mapping_resolution_tui.actions import (
    Action,
    ClearFilter,
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.selectors import sort_mappings_for_initial_display
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


# ── filter helpers ──────────────────────────────────────────────────────────


def _with_filter(
    state: AppState,
    *,
    text: str,
    collision_only: bool,
    cursor: int,
) -> AppState:
    """Return a new state whose filter has the given fields.

    ``filter.cursor`` is clamped into ``[0, len(text)]`` and ``filter.raw`` is
    kept in sync as ``("!" if collision_only else "") + text`` on every
    mutation, as the filter prompt rendering depends on it.

    Selection re-clamping (keeping ``selection.selected_ordinal`` on a visible
    row when a filter change hides it) is deliberately *not* done here: that is
    TASK-004's responsibility. TASK-001 keeps the reducer scoped to pure filter
    state so the dispatch foundation carries no selection policy.
    """
    cursor = max(0, min(cursor, len(text)))
    raw = ("!" if collision_only else "") + text
    new_filter = FilterState(
        raw=raw,
        collision_only=collision_only,
        text=text,
        cursor=cursor,
    )
    return replace(state, filter=new_filter)


# ── per-action handlers ─────────────────────────────────────────────────────


def _reduce_insert_char(state: AppState, action: InsertChar) -> AppState:
    cursor = state.filter.cursor
    text = state.filter.text
    new_text = text[:cursor] + action.char + text[cursor:]
    return _with_filter(
        state,
        text=new_text,
        collision_only=state.filter.collision_only,
        cursor=cursor + len(action.char),
    )


def _reduce_move_cursor_left(state: AppState, action: MoveCursorLeft) -> AppState:
    return _with_filter(
        state,
        text=state.filter.text,
        collision_only=state.filter.collision_only,
        cursor=state.filter.cursor - 1,
    )


def _reduce_move_cursor_right(state: AppState, action: MoveCursorRight) -> AppState:
    return _with_filter(
        state,
        text=state.filter.text,
        collision_only=state.filter.collision_only,
        cursor=state.filter.cursor + 1,
    )


def _reduce_toggle_collision_only(
    state: AppState, action: ToggleCollisionOnly
) -> AppState:
    return _with_filter(
        state,
        text=state.filter.text,
        collision_only=not state.filter.collision_only,
        cursor=state.filter.cursor,
    )


def _reduce_clear_filter(state: AppState, action: ClearFilter) -> AppState:
    return _with_filter(state, text="", collision_only=False, cursor=0)


_HANDLERS = {
    InsertChar: _reduce_insert_char,
    MoveCursorLeft: _reduce_move_cursor_left,
    MoveCursorRight: _reduce_move_cursor_right,
    ToggleCollisionOnly: _reduce_toggle_collision_only,
    ClearFilter: _reduce_clear_filter,
}


def reduce(state: AppState, action: Action) -> AppState:
    """Pure dispatch: route ``action`` to its handler, returning new state.

    Every handler returns a fresh frozen :class:`AppState`; the input ``state``
    is never mutated. An unrecognised action is a no-op and the same state is
    returned unchanged (FR30).
    """
    handler = _HANDLERS.get(type(action))
    if handler is None:
        return state
    return handler(state, action)
