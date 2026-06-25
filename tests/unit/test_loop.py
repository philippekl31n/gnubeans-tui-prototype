"""
Unit tests for the blocking event loop and input layer (TASK-001).

Covers readline alias normalisation (FR29), key->action mapping, the
read -> normalise -> dispatch -> render cycle, clean quit, and the FR30
guarantee that unsupported keys leave state and rendered output unchanged.
The loop is driven through its injectable ``keys``/``render`` seams so no
real TTY is required.
"""

import pytest

from mapping_resolution_tui import loop
from mapping_resolution_tui.actions import (
    ClearFilter,
    InsertChar,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from tests.fixtures.storyboard import make_config, make_mappings


def run_keys(keys):
    """Run the loop over a fixed key sequence, returning (result, frames)."""
    frames: list[list[str]] = []
    result = loop.run(
        make_config(),
        make_mappings(),
        keys=keys,
        render=frames.append,
    )
    return result, frames


def filter_line(frame):
    return next(line for line in frame if "Filter:" in line)


# ── normalisation (FR29) ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "alias, canonical",
    [
        ("ctrl+b", "left"),
        ("ctrl+f", "right"),
        ("ctrl+i", "tab"),
        ("ctrl+h", "backspace"),
    ],
)
def test_normalise_key_collapses_readline_aliases(alias, canonical):
    assert loop.normalise_key(alias) == canonical


def test_normalise_key_passes_through_unknown_tokens():
    assert loop.normalise_key("left") == "left"
    assert loop.normalise_key("a") == "a"
    assert loop.normalise_key("f1") == "f1"


# ── key -> action mapping ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "key, expected",
    [
        ("tab", ToggleCollisionOnly()),
        ("!", ToggleCollisionOnly()),
        ("left", MoveCursorLeft()),
        ("right", MoveCursorRight()),
        ("esc", ClearFilter()),
        ("a", InsertChar("a")),
        ("3", InsertChar("3")),
    ],
)
def test_key_to_action_maps_supported_keys(key, expected):
    assert loop.key_to_action(key) == expected


@pytest.mark.parametrize("key", ["up", "down", "enter", "backspace", "f1", "ctrl+x"])
def test_key_to_action_returns_none_for_unsupported_keys(key):
    assert loop.key_to_action(key) is None


# ── event loop cycle ─────────────────────────────────────────────────────────

def test_loop_renders_initial_frame_before_consuming_input():
    _, frames = run_keys([])
    assert len(frames) == 1
    assert "Filter:" in filter_line(frames[0])


def test_typing_a_character_dispatches_and_rerenders():
    result, frames = run_keys(["3"])
    # initial frame + one redraw after the insert
    assert len(frames) == 2
    assert "Filter: 3" in filter_line(frames[-1])
    assert result is not None  # clean end-of-input exit


def test_bang_toggles_collision_metafilter_via_loop():
    _, frames = run_keys(["!"])
    assert filter_line(frames[-1]).count("!") >= 1


def test_readline_alias_moves_cursor_end_to_end():
    # type "a", then ctrl+b (backward-char) should move the cursor left.
    _, frames = run_keys(["a", "ctrl+b"])
    assert len(frames) == 3  # initial + insert + cursor move


def test_unsupported_keys_do_not_rerender():
    # FR30: an unsupported key produces no new frame and no state change.
    _, frames = run_keys(["up", "f1", "ctrl+x"])
    assert len(frames) == 1  # only the initial frame


def test_quit_key_exits_cleanly_with_none():
    result, frames = run_keys(["a", "ctrl+c", "b"])
    assert result is None
    # the trailing "b" after the quit key is never processed
    assert len(frames) == 2  # initial + the "a" insert
