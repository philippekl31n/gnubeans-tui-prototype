"""
Reducer module: pure state transitions and application initialization.
"""



from dataclasses import replace
from typing import Optional
import shutil

from mapping_resolution_tui.actions import (
    Action,
    ClearFilter,
    DeleteBackward,
    InsertCharacter,
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


def reduce(state: AppState, action: Action) -> AppState:
    """Dispatch ``action`` to its handler and return a new immutable state.

    Unrecognised actions leave the state unchanged so that the caller may treat
    the returned object identity as "no transition occurred".
    """
    if isinstance(action, InsertCharacter):
        return _insert_character(state, action.char)
    if isinstance(action, MoveCursorLeft):
        return _move_cursor_left(state)
    if isinstance(action, MoveCursorRight):
        return _move_cursor_right(state)
    if isinstance(action, ToggleCollisionOnly):
        return _toggle_collision_only(state)
    if isinstance(action, DeleteBackward):
        return _delete_backward(state)
    if isinstance(action, ClearFilter):
        return _clear_filter(state)
    return state


def _with_filter(
    state: AppState,
    *,
    collision_only: Optional[bool] = None,
    text: Optional[str] = None,
    cursor: Optional[int] = None,
) -> AppState:
    """Return ``state`` with a new ``FilterState``, keeping ``raw`` in sync.

    ``filter.raw`` is always re-derived as ``("!" if collision_only else "") +
    text`` and ``cursor`` is clamped to ``[0, len(text)]`` on every mutation.
    """
    current = state.filter
    collision_only = current.collision_only if collision_only is None else collision_only
    text = current.text if text is None else text
    cursor = current.cursor if cursor is None else cursor
    cursor = max(0, min(cursor, len(text)))
    raw = ("!" if collision_only else "") + text
    new_filter = FilterState(
        raw=raw,
        collision_only=collision_only,
        text=text,
        cursor=cursor,
    )
    return replace(state, filter=new_filter)


def _insert_character(state: AppState, char: str) -> AppState:
    f = state.filter
    text = f.text[: f.cursor] + char + f.text[f.cursor :]
    return _with_filter(state, text=text, cursor=f.cursor + len(char))


def _move_cursor_left(state: AppState) -> AppState:
    return _with_filter(state, cursor=state.filter.cursor - 1)


def _move_cursor_right(state: AppState) -> AppState:
    return _with_filter(state, cursor=state.filter.cursor + 1)


def _toggle_collision_only(state: AppState) -> AppState:
    return _with_filter(state, collision_only=not state.filter.collision_only)


def _clear_filter(state: AppState) -> AppState:
    return _with_filter(state, collision_only=False, text="", cursor=0)


def _delete_backward(state: AppState) -> AppState:
    f = state.filter
    if f.cursor > 0:
        text = f.text[: f.cursor - 1] + f.text[f.cursor :]
        return _with_filter(state, text=text, cursor=f.cursor - 1)
    # At the start of an empty query, Backspace clears the metafilter (FR10/FR13).
    if f.text == "" and f.collision_only:
        return _with_filter(state, collision_only=False)
    return state
