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
from typing import Union


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
class Redraw:
    """Re-render the current state without mutating it (ctrl+l)."""


@dataclass(frozen=True)
class ClearFilter:
    """Clear ``filter.raw`` and reset ``filter.cursor`` to 0 (Esc)."""


# Discriminated union of every action the reducer understands.
Action = Union[
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    MoveCursorHome,
    MoveCursorEnd,
    Backspace,
    DeleteChar,
    KillLine,
    UnixLineDiscard,
    KillWord,
    BackwardKillWord,
    Redraw,
    ClearFilter,
]
