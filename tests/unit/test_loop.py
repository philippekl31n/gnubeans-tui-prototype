"""
Unit tests for the input layer: readline alias normalisation (FR29), the
no-op families (spec §5.1), unsupported-key no-ops (FR30), and the quit key.
"""

from blessed.keyboard import Keystroke

from mapping_resolution_tui.actions import (
    ClearFilter,
    DeleteBackward,
    DeleteForward,
    DeleteWordBackward,
    DeleteWordForward,
    InsertCharacter,
    KillToEnd,
    KillToStart,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
)
from mapping_resolution_tui.config import QUIT_KEY
from mapping_resolution_tui.loop import is_quit_key, key_to_action
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines


def _initial_state():
    from tests.fixtures.storyboard import make_config, make_mappings

    return make_initial_state(make_config(), make_mappings(), frame_height=15)


# ── printable insertion; `!` is now ordinary text, Tab is a no-op ───────────────

def test_printable_character_maps_to_insert():
    assert key_to_action("a") == InsertCharacter("a")


def test_digit_maps_to_insert():
    assert key_to_action("3") == InsertCharacter("3")


def test_space_maps_to_insert():
    assert key_to_action(" ") == InsertCharacter(" ")


def test_bang_maps_to_literal_insert_not_a_toggle():
    # `!` is an ordinary printable character (spec §3.3); it inserts literally.
    assert key_to_action("!") == InsertCharacter("!")


def test_tab_is_a_noop_reserved_for_bang_autocomplete():
    # Tab/ctrl+i is reserved for the TASK-003 bang-autocomplete; no-op until then.
    assert key_to_action("\t") is None
    assert key_to_action(Keystroke("\t", code=512, name="KEY_TAB")) is None


# ── readline line-editing aliases (FR29 / spec §5.1) ────────────────────────────

def test_ctrl_a_maps_to_cursor_home():
    assert key_to_action("\x01") == MoveCursorHome()


def test_ctrl_e_maps_to_cursor_end():
    assert key_to_action("\x05") == MoveCursorEnd()


def test_ctrl_b_maps_to_cursor_left():
    assert key_to_action("\x02") == MoveCursorLeft()


def test_ctrl_f_maps_to_cursor_right():
    assert key_to_action("\x06") == MoveCursorRight()


def test_ctrl_h_maps_to_backspace():
    assert key_to_action("\x08") == DeleteBackward()


def test_del_maps_to_backspace():
    assert key_to_action("\x7f") == DeleteBackward()


def test_ctrl_d_maps_to_forward_delete():
    assert key_to_action("\x04") == DeleteForward()


def test_ctrl_k_maps_to_kill_to_end():
    assert key_to_action("\x0b") == KillToEnd()


def test_ctrl_u_maps_to_kill_to_start():
    assert key_to_action("\x15") == KillToStart()


def test_ctrl_w_maps_to_delete_word_backward():
    assert key_to_action("\x17") == DeleteWordBackward()


def test_meta_d_maps_to_delete_word_forward():
    assert key_to_action("\x1bd") == DeleteWordForward()


def test_meta_backspace_maps_to_delete_word_backward():
    assert key_to_action("\x1b\x7f") == DeleteWordBackward()
    assert key_to_action("\x1b\x08") == DeleteWordBackward()


def test_esc_maps_to_clear_filter():
    assert key_to_action("\x1b") == ClearFilter()


# ── named escape sequences resolved by blessed ─────────────────────────────────

def test_left_arrow_keystroke_maps_to_cursor_left():
    key = Keystroke("\x1b[D", code=260, name="KEY_LEFT")
    assert key_to_action(key) == MoveCursorLeft()


def test_right_arrow_keystroke_maps_to_cursor_right():
    key = Keystroke("\x1b[C", code=261, name="KEY_RIGHT")
    assert key_to_action(key) == MoveCursorRight()


def test_home_and_end_keystrokes_map_to_cursor_boundaries():
    assert key_to_action(Keystroke("\x1b[H", code=262, name="KEY_HOME")) == MoveCursorHome()
    assert key_to_action(Keystroke("\x1b[F", code=360, name="KEY_END")) == MoveCursorEnd()


def test_backspace_keystroke_maps_to_backspace():
    key = Keystroke("\x7f", code=263, name="KEY_BACKSPACE")
    assert key_to_action(key) == DeleteBackward()


def test_delete_keystroke_maps_to_forward_delete():
    key = Keystroke("\x1b[3~", code=330, name="KEY_DELETE")
    assert key_to_action(key) == DeleteForward()


def test_escape_keystroke_maps_to_clear_filter():
    key = Keystroke("\x1b", code=361, name="KEY_ESCAPE")
    assert key_to_action(key) == ClearFilter()


# ── no-op readline families: each is ignored (spec §5.1) ────────────────────────

def test_noop_readline_families_are_ignored():
    assert key_to_action("\x07") is None  # abort (ctrl+g)
    assert key_to_action("\x11") is None  # quoted-insert (ctrl+q)
    assert key_to_action("\x16") is None  # quoted-insert (ctrl+v)
    assert key_to_action("\x12") is None  # reverse-search-history (ctrl+r)
    assert key_to_action("\x14") is None  # transpose-chars (ctrl+t)
    assert key_to_action("\x19") is None  # yank (ctrl+y)
    assert key_to_action("\x1f") is None  # undo (ctrl+_)
    assert key_to_action("\x0c") is None  # clear-screen (ctrl+l): no state mutation


def test_noop_family_dispatch_leaves_state_and_render_unchanged():
    state = _initial_state()
    before_lines = render_lines(state)
    for raw in ("\x07", "\x11", "\x12", "\x14", "\x19", "\x1f", "\x0c"):
        action = key_to_action(raw)
        assert action is None
        # The loop skips dispatch entirely for None actions; nothing changes.
    assert render_lines(state) == before_lines


# ── unsupported keys are no-ops (FR30) ─────────────────────────────────────────

def test_unsupported_named_sequence_is_ignored():
    key = Keystroke("\x1b[2~", code=331, name="KEY_INSERT")
    assert key_to_action(key) is None


def test_quit_key_is_not_a_filter_action():
    assert key_to_action(QUIT_KEY) is None


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
    assert state.filter.raw == "acb"
    assert state.filter.cursor == 2


def test_bang_then_text_builds_metafiltered_query():
    state = _drive(_initial_state(), ["!", "3"])
    assert state.filter.collision_only is True
    assert state.filter.text == "3"
    assert state.filter.raw == "!3"


def test_ctrl_u_then_retype_via_input_layer():
    state = _drive(_initial_state(), ["a", "b", "c", "\x15", "x"])
    assert state.filter.raw == "x"
    assert state.filter.cursor == 1


def test_unsupported_keys_do_not_change_filter():
    state = _drive(_initial_state(), ["\x07", "\x1c", "\x1b[Z"])
    assert state.filter.raw == ""
    assert state.filter.collision_only is False
