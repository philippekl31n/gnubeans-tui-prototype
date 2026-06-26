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
)
from mapping_resolution_tui.selectors import parse_filter, sort_mappings_for_initial_display
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
    return state


_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def _with_raw(state: AppState, raw: str, cursor: int) -> AppState:
    """Return ``state`` with a new ``FilterState`` derived from ``raw``.

    ``filter.raw`` is the single editable buffer (spec §3.3): ``cursor`` is
    clamped to ``[0, len(raw)]`` and ``collision_only`` / ``text`` are re-derived
    from ``raw`` on every mutation.
    """
    cursor = max(0, min(cursor, len(raw)))
    collision_only, text = parse_filter(raw)
    new_filter = FilterState(
        raw=raw,
        collision_only=collision_only,
        text=text,
        cursor=cursor,
    )
    return replace(state, filter=new_filter)


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
