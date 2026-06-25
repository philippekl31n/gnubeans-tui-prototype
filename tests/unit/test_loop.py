"""
Unit tests for the input layer: readline alias normalisation (FR29),
unsupported-key no-ops (FR30), and the configured quit key.
"""

from blessed.keyboard import Keystroke

from mapping_resolution_tui.actions import (
    ClearFilter,
    DeleteBackward,
    InsertCharacter,
    MoveCursorLeft,
    MoveCursorRight,
    ToggleCollisionOnly,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.loop import is_quit_key, key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce


def _initial_state():
    from tests.fixtures.storyboard import make_config, make_mappings

    return make_initial_state(make_config(), make_mappings(), frame_height=15)


# ── printable insertion and metafilter keys ────────────────────────────────────

def test_printable_character_maps_to_insert():
    assert key_to_action("a") == InsertCharacter("a")


def test_digit_maps_to_insert():
    assert key_to_action("3") == InsertCharacter("3")


def test_space_maps_to_insert():
    assert key_to_action(" ") == InsertCharacter(" ")


def test_bang_toggles_collision_only_not_insert():
    assert key_to_action("!") == ToggleCollisionOnly()


def test_tab_toggles_collision_only():
    assert key_to_action("\t") == ToggleCollisionOnly()


# ── readline aliases (FR29) ────────────────────────────────────────────────────

def test_ctrl_b_maps_to_cursor_left():
    assert key_to_action("\x02") == MoveCursorLeft()


def test_ctrl_f_maps_to_cursor_right():
    assert key_to_action("\x06") == MoveCursorRight()


def test_ctrl_h_maps_to_backspace():
    assert key_to_action("\x08") == DeleteBackward()


def test_del_maps_to_backspace():
    assert key_to_action("\x7f") == DeleteBackward()


def test_esc_maps_to_clear_filter():
    assert key_to_action("\x1b") == ClearFilter()


# ── named escape sequences resolved by blessed ─────────────────────────────────

def test_left_arrow_keystroke_maps_to_cursor_left():
    key = Keystroke("\x1b[D", code=260, name="KEY_LEFT")
    assert key_to_action(key) == MoveCursorLeft()


def test_right_arrow_keystroke_maps_to_cursor_right():
    key = Keystroke("\x1b[C", code=261, name="KEY_RIGHT")
    assert key_to_action(key) == MoveCursorRight()


def test_backspace_keystroke_maps_to_backspace():
    key = Keystroke("\x7f", code=263, name="KEY_BACKSPACE")
    assert key_to_action(key) == DeleteBackward()


def test_escape_keystroke_maps_to_clear_filter():
    key = Keystroke("\x1b", code=361, name="KEY_ESCAPE")
    assert key_to_action(key) == ClearFilter()


# ── unsupported keys are no-ops (FR30) ─────────────────────────────────────────

def test_unsupported_control_char_is_ignored():
    assert key_to_action("\x07") is None  # ctrl+g / abort


def test_unsupported_named_sequence_is_ignored():
    key = Keystroke("\x1b[2~", code=331, name="KEY_INSERT")
    assert key_to_action(key) is None


def test_quit_key_is_not_a_filter_action():
    assert key_to_action(QUIT_KEY) is None


def test_unsupported_key_dispatch_leaves_state_unchanged():
    state = _initial_state()
    action = key_to_action("\x07")
    assert action is None
    # The loop skips dispatch entirely for None actions; state stays identical.
    assert state is state


# ── configured quit key ────────────────────────────────────────────────────────

def test_is_quit_key_true_for_configured_key():
    assert is_quit_key(QUIT_KEY) is True


def test_is_quit_key_true_for_keystroke():
    assert is_quit_key(Keystroke(QUIT_KEY)) is True


def test_is_quit_key_false_for_other_keys():
    assert is_quit_key("a") is False
    assert is_quit_key("\x1b") is False


# ── normalise → dispatch integration ───────────────────────────────────────────

def _drive(state, keys):
    for raw in keys:
        action = key_to_action(raw)
        if action is not None:
            state = reduce(state, action)
    return state


def test_typing_then_cursor_move_then_insert():
    state = _drive(_initial_state(), ["a", "b", "\x02", "c"])
    assert state.filter.text == "acb"
    assert state.filter.cursor == 2


def test_bang_then_text_builds_metafiltered_query():
    state = _drive(_initial_state(), ["!", "3"])
    assert state.filter.collision_only is True
    assert state.filter.text == "3"
    assert state.filter.raw == "!3"


def test_unsupported_keys_do_not_change_filter():
    state = _drive(_initial_state(), ["\x07", "\x10", "\x1b[Z"])
    assert state.filter.text == ""
    assert state.filter.collision_only is False
