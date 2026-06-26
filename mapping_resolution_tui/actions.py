"""
Typed action definitions for the Redux-style dispatch pipeline.

Each action is an immutable dataclass describing a single intended state
transition for browsing-mode filter editing. The input layer (``loop.py``)
normalises raw keypresses — including readline-style aliases — into one of these
actions before dispatching them through
:func:`mapping_resolution_tui.reducer.reduce`.

The filter is a single editable buffer (``filter.raw``) with a caret
(``filter.cursor``); ``filter.collision_only`` and ``filter.text`` are derived
from ``filter.raw`` after every mutation (spec §3.3). Every action below edits
``filter.raw`` or moves the caret within it.

Actions carry no terminal or ANSI concerns and never reference ``blessed``; they
are plain data passed between the input layer and the pure reducer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InsertCharacter:
    """Insert a single printable character into ``filter.raw`` at the cursor.

    ``!`` is an ordinary printable character; inserted at index 0 it becomes the
    collision metafilter purely because ``collision_only`` is derived from
    ``filter.raw`` (spec §3.3).
    """

    char: str


@dataclass(frozen=True)
class MoveCursorLeft:
    """Move the caret one character toward the start of ``filter.raw``."""


@dataclass(frozen=True)
class MoveCursorRight:
    """Move the caret one character toward the end of ``filter.raw``."""


@dataclass(frozen=True)
class MoveCursorHome:
    """Move the caret to the start of ``filter.raw`` (readline beginning-of-line)."""


@dataclass(frozen=True)
class MoveCursorEnd:
    """Move the caret to the end of ``filter.raw`` (readline end-of-line)."""


@dataclass(frozen=True)
class DeleteBackward:
    """Delete the character before the caret (readline backward-delete-char)."""


@dataclass(frozen=True)
class DeleteForward:
    """Delete the character at the caret (readline delete-char)."""


@dataclass(frozen=True)
class KillToEnd:
    """Delete from the caret through the end of ``filter.raw`` (readline kill-line)."""


@dataclass(frozen=True)
class KillToStart:
    """Delete from the start of ``filter.raw`` through the caret (unix-line-discard)."""


@dataclass(frozen=True)
class DeleteWordBackward:
    """Delete the word before the caret (readline backward-kill-word)."""


@dataclass(frozen=True)
class DeleteWordForward:
    """Delete the word at/after the caret (readline kill-word)."""


@dataclass(frozen=True)
class ClearFilter:
    """Clear ``filter.raw`` entirely and reset the caret to 0 (``Esc``)."""


Action = (
    InsertCharacter
    | MoveCursorLeft
    | MoveCursorRight
    | MoveCursorHome
    | MoveCursorEnd
    | DeleteBackward
    | DeleteForward
    | KillToEnd
    | KillToStart
    | DeleteWordBackward
    | DeleteWordForward
    | ClearFilter
)
