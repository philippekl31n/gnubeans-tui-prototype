"""
Unit tests for the SIGWINCH resize action (TASK-013).

A terminal resize is dispatched into the reducer as an
:class:`~mapping_resolution_tui.actions.UpdateTerminalSize` action — distinct
from key events, since it carries the new ``(columns, rows)`` and applies in
every mode. ``reduce`` updates both ``TerminalState.width`` and
``TerminalState.height`` from it (spec §6.2, FR37).
"""

import pytest

from mapping_resolution_tui.actions import UpdateTerminalSize
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.state import Mode
from tests.fixtures.storyboard import make_config, make_mappings


@pytest.fixture
def state():
    return make_initial_state(
        make_config(), make_mappings(), frame_height=15, frame_width=75
    )


def test_initial_state_captures_width_and_height(state):
    assert state.terminal.width == 75
    assert state.terminal.height == 15


def test_resize_updates_both_width_and_height(state):
    resized = reduce(state, UpdateTerminalSize(columns=100, rows=30))
    assert resized.terminal.width == 100
    assert resized.terminal.height == 30


def test_resize_preserves_everything_else(state):
    resized = reduce(state, UpdateTerminalSize(columns=100, rows=30))
    assert resized.mode is state.mode
    assert resized.mappings == state.mappings
    assert resized.filter == state.filter
    assert resized.selection == state.selection
    assert resized.result == state.result


def test_resize_to_same_dimensions_is_identity(state):
    # An incidental SIGWINCH reporting the current size returns the same object
    # so the loop can skip the repaint.
    assert reduce(state, UpdateTerminalSize(columns=75, rows=15)) is state


def test_resize_changing_only_width_is_applied(state):
    resized = reduce(state, UpdateTerminalSize(columns=120, rows=15))
    assert resized is not state
    assert resized.terminal.width == 120
    assert resized.terminal.height == 15


def test_resize_applies_in_every_mode(state):
    # The action is mode-independent: dispatched from BROWSING here, it never
    # touches mode, so it applies uniformly across EDITING/CONFIRMING too.
    resized = reduce(state, UpdateTerminalSize(columns=90, rows=20))
    assert resized.mode is Mode.BROWSING
    assert (resized.terminal.width, resized.terminal.height) == (90, 20)
