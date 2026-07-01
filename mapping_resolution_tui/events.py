"""
Key-event vocabulary for the input→reduce pipeline.

:class:`KeyEvent` is a mode-neutral canonical key identity: the normalisation
layer (:func:`~mapping_resolution_tui.loop.key_to_event`) collapses every
representation of each logical key (named escape sequences, control bytes,
readline aliases) onto a single member.  The reducer interprets members in
mode-context via :data:`~mapping_resolution_tui.reducer._MODE_HANDLERS`.

The only parameterised case — a printable character to insert — is represented
as a bare :class:`str` of length 1.  The union :data:`InputEvent` is the full
type accepted by :func:`~mapping_resolution_tui.reducer.reduce`.
"""

from enum import Enum, auto


class KeyEvent(Enum):
    ESCAPE = auto()
    ENTER = auto()
    BACKSPACE = auto()
    DELETE_CHAR = auto()
    CURSOR_LEFT = auto()
    CURSOR_RIGHT = auto()
    CURSOR_HOME = auto()
    CURSOR_END = auto()
    KILL_LINE = auto()
    UNIX_LINE_DISCARD = auto()
    KILL_WORD = auto()
    BACKWARD_KILL_WORD = auto()
    REDRAW = auto()
    TAB = auto()
    PAGE_UP = auto()
    PAGE_DOWN = auto()
    SELECTION_UP = auto()
    SELECTION_DOWN = auto()


# str branch = single printable character to insert at the active cursor.
InputEvent = KeyEvent | str
