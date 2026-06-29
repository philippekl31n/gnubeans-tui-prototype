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
    ClearFilter,
    DeleteChar,
    InsertChar,
    KillLine,
    KillWord,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    Redraw,
    UnixLineDiscard,
)
from mapping_resolution_tui.selectors import (
    parse_filter,
    select_body_capacity,
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
    ``text``), the visible rows are recomputed, and the selection is clamped so
    it never points at a row the new filter hides — keeping the row cursor on a
    visible row (e.g. engaging the collision metafilter from frame 1a moves the
    selection to the first collision row, frame 2).
    """
    interim = replace(state, filter=_derive_filter(raw=raw, cursor=cursor))
    selection = _clamp_selection(interim)
    if selection is interim.selection:
        return interim
    return replace(interim, selection=selection)


def _clamp_selection(state: AppState) -> SelectionState:
    """Clamp the selection onto the visible rows for ``state`` (spec §3.4 / S8.2).

    ``selected_ordinal`` is left unchanged when it is still visible; otherwise it
    snaps to the first visible row, or to ``None`` when no rows match. The scroll
    window is then *anchored* so the selected row is always rendered (S8.2): a
    selection above the window pulls ``scroll_offset`` up to it, one below pushes
    it down to the last visible line. Finally ``scroll_offset`` is clamped into
    ``[0, max(0, len(visible) - capacity)]``. Returns the existing
    :class:`SelectionState` object unchanged when nothing moves, so the loop's
    identity-based no-op check still holds.
    """
    selection = state.selection
    visible = select_visible_rows(state)

    if not visible:
        selected = None
    elif any(m.ordinal == selection.selected_ordinal for m in visible):
        selected = selection.selected_ordinal
    else:
        selected = visible[0].ordinal

    capacity = select_body_capacity(state.terminal.height)
    scroll = selection.scroll_offset
    if selected is not None and capacity > 0:
        # Anchored body allocation: keep the selected row inside the window so
        # widening the result set never scrolls the row cursor off-screen.
        index = next(i for i, m in enumerate(visible) if m.ordinal == selected)
        if index < scroll:
            scroll = index
        elif index >= scroll + capacity:
            scroll = index - capacity + 1
    scroll = min(max(0, scroll), max(0, len(visible) - capacity))

    if selected == selection.selected_ordinal and scroll == selection.scroll_offset:
        return selection
    return replace(selection, selected_ordinal=selected, scroll_offset=scroll)


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
    if state.filter.raw != "":
        return state
    if select_unresolved_collision_count(state.mappings) == 0:
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
