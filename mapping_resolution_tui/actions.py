"""
Actions module.

Redux-style action objects for BROWSING-mode filter operations. Actions are
plain frozen dataclasses describing *what happened*; they carry no behaviour.
The reducer (see :mod:`mapping_resolution_tui.reducer`) interprets them into
new immutable :class:`~mapping_resolution_tui.state.AppState` values.

``filter.raw`` is the single editable buffer and the source of truth; every
mutating action edits ``filter.raw`` and the reducer re-derives ``collision_only``
(raw begins with ``!``) and ``text`` (raw minus a single leading ``!``) after the
edit (spec S3.2/S5.1). There is no collision-only toggle: ``!`` is an ordinary
editable character.

The input layer (see :mod:`mapping_resolution_tui.loop`) is responsible for
normalising readline-style key aliases (FR29) and constructing the appropriate
action before dispatch. Keys that map to no action leave state unchanged (FR30).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InsertChar:
    """Insert a printable character into ``filter.raw`` at the cursor."""

    char: str


@dataclass(frozen=True)
class MoveCursorLeft:
    """Move ``filter.cursor`` left by one, clamped at 0 (readline backward-char)."""


@dataclass(frozen=True)
class MoveCursorRight:
    """Move ``filter.cursor`` right by one, clamped at ``len(filter.raw)``."""


@dataclass(frozen=True)
class MoveCursorHome:
    """Move ``filter.cursor`` to 0 (readline beginning-of-line, Home / ctrl+a)."""


@dataclass(frozen=True)
class MoveCursorEnd:
    """Move ``filter.cursor`` to ``len(filter.raw)`` (end-of-line, End / ctrl+e)."""


@dataclass(frozen=True)
class Backspace:
    """Delete the character before ``filter.cursor`` (backward-delete-char)."""


@dataclass(frozen=True)
class DeleteChar:
    """Delete the character at ``filter.cursor`` (forward delete-char, Del / ctrl+d)."""


@dataclass(frozen=True)
class KillLine:
    """Delete from ``filter.cursor`` through end of ``filter.raw`` (ctrl+k)."""


@dataclass(frozen=True)
class UnixLineDiscard:
    """Delete from start through ``filter.cursor`` and reset cursor to 0 (ctrl+u)."""


@dataclass(frozen=True)
class KillWord:
    """Delete the next word from ``filter.cursor`` (meta+d)."""


@dataclass(frozen=True)
class BackwardKillWord:
    """Delete the previous word before ``filter.cursor`` (ctrl+w / meta+backspace)."""


@dataclass(frozen=True)
class AutocompleteBang:
    """Autocomplete a leading ``!`` into ``filter.raw`` (Tab / ctrl+i).

    The reducer applies this only when the ``Tab to view collisions`` ghost is
    visible — ``filter.raw`` is empty and at least one unresolved collision
    exists — inserting ``!`` at index 0 and setting ``filter.cursor = 1``. In
    every other situation it is a no-op; in particular a second Tab never clears
    the inserted ``!`` (spec §3.3). The gate lives in the reducer, against
    application state, not in the input layer.
    """


@dataclass(frozen=True)
class AcceptLine:
    """Accept the current input line (Enter / ctrl+j / ctrl+m, readline ``accept-line``).

    In ``BROWSING`` this edits the selected row, transitioning to ``EDITING`` when
    a row is selected (spec §4.2 / §7.1). In ``EDITING`` it submits the edit when
    validation is ``VALID`` (spec §4.2; the submit path is owned by TASK-008).
    """


@dataclass(frozen=True)
class Redraw:
    """Re-render the current state without mutating it (ctrl+l)."""


@dataclass(frozen=True)
class ClearFilter:
    """Clear ``filter.raw`` and reset ``filter.cursor`` to 0 (Esc)."""


@dataclass(frozen=True)
class MoveSelectionUp:
    """Move selection up by one row."""


@dataclass(frozen=True)
class MoveSelectionDown:
    """Move selection down by one row."""


@dataclass(frozen=True)
class PageUp:
    """Page selection up."""


@dataclass(frozen=True)
class PageDown:
    """Page selection down."""


# Discriminated union of every action the reducer understands (PEP 604).
Action = (
    InsertChar
    | MoveCursorLeft
    | MoveCursorRight
    | MoveCursorHome
    | MoveCursorEnd
    | Backspace
    | DeleteChar
    | KillLine
    | UnixLineDiscard
    | KillWord
    | BackwardKillWord
    | AutocompleteBang
    | AcceptLine
    | Redraw
    | ClearFilter
    | MoveSelectionUp
    | MoveSelectionDown
    | PageUp
    | PageDown
)
