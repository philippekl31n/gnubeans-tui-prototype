"""
Typed action definitions for the Redux-style dispatch pipeline.

Each action is an immutable dataclass describing a single intended state
transition for browsing-mode filtering. The input layer (``loop.py``) normalises
raw keypresses — including readline-style aliases — into one of these actions
before dispatching them through :func:`mapping_resolution_tui.reducer.reduce`.

Actions carry no terminal or ANSI concerns and never reference ``blessed``; they
are plain data passed between the input layer and the pure reducer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InsertCharacter:
    """Insert a single printable character into ``filter.text`` at the cursor."""

    char: str


@dataclass(frozen=True)
class MoveCursorLeft:
    """Move the filter cursor one position toward the start of the text."""


@dataclass(frozen=True)
class MoveCursorRight:
    """Move the filter cursor one position toward the end of the text."""


@dataclass(frozen=True)
class ToggleCollisionOnly:
    """Toggle the collision-only metafilter (``Tab`` or ``!``)."""


@dataclass(frozen=True)
class DeleteBackward:
    """Delete the character before the cursor, or clear the metafilter."""


@dataclass(frozen=True)
class ClearFilter:
    """Clear the active text filter and collision-only metafilter (``Esc``)."""


Action = (
    InsertCharacter
    | MoveCursorLeft
    | MoveCursorRight
    | ToggleCollisionOnly
    | DeleteBackward
    | ClearFilter
)
