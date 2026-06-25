"""
Actions module.

Redux-style action objects for BROWSING-mode filter operations. Actions are
plain frozen dataclasses describing *what happened*; they carry no behaviour.
The reducer (see :mod:`mapping_resolution_tui.reducer`) interprets them into
new immutable :class:`~mapping_resolution_tui.state.AppState` values.

The input layer (see :mod:`mapping_resolution_tui.loop`) is responsible for
normalising readline-style key aliases (FR29) and constructing the appropriate
action before dispatch. Keys that map to no action leave state unchanged (FR30).
"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class InsertChar:
    """Insert a printable character into ``filter.text`` at the cursor."""

    char: str


@dataclass(frozen=True)
class MoveCursorLeft:
    """Move ``filter.cursor`` left by one, clamped at 0 (readline backward-char)."""


@dataclass(frozen=True)
class MoveCursorRight:
    """Move ``filter.cursor`` right by one, clamped at ``len(filter.text)``."""


@dataclass(frozen=True)
class ToggleCollisionOnly:
    """Toggle the ``filter.collision_only`` metafilter (Tab / ``!``)."""


@dataclass(frozen=True)
class ClearFilter:
    """Clear both ``filter.collision_only`` and ``filter.text`` (Esc)."""


# Discriminated union of every action the reducer understands.
Action = Union[
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
    ClearFilter,
]
