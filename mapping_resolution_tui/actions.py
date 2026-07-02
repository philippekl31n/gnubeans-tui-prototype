"""
Non-key actions dispatched into the reducer.

Key input flows through :mod:`~mapping_resolution_tui.events` (a
:class:`~mapping_resolution_tui.events.KeyEvent` or a bare ``str``). A terminal
resize is not a keypress: it carries the new ``(columns, rows)`` the event loop
reads from the terminal after a SIGWINCH, so it is modelled as its own action
rather than shoehorned into the key-event vocabulary. The loop dispatches this
action through :func:`~mapping_resolution_tui.reducer.reduce`, which updates
``TerminalState.width`` / ``TerminalState.height`` from it (FR37).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTerminalSize:
    """A SIGWINCH-driven resize carrying the terminal's new dimensions."""

    columns: int
    rows: int
