"""
Unit tests for the blocking event loop and unified input layer (TASK-001/002).

A single table-driven ``key_to_action`` normalises every keypress — named escape
sequences via ``Keystroke.name`` and readline control chords / meta sequences via
the raw key text — directly into an action (FR29). Unsupported keys and the no-op
readline families return ``None`` so the loop leaves state and output unchanged
(FR30). The loop is driven through its injectable ``keys``/``render`` seams, with
``Key`` standing in for a blessed ``Keystroke`` (a str carrying a ``.name``).
"""

import pytest

from mapping_resolution_tui import loop
from mapping_resolution_tui.actions import (
    AcceptLine,
    AutocompleteBang,
    Backspace,
    BackwardKillWord,
    ClearFilter,
    DeleteChar,
    InsertChar,
    KillLine,
    KillWord,
    MoveCursorEnd,
    MoveCursorHome,
    MoveCursorLeft,
    MoveCursorRight,
    Redraw,
    UnixLineDiscard,
)
from tests.fixtures.storyboard import make_config, make_mappings


class Key(str):
    """Minimal stand-in for a blessed Keystroke: a str carrying a ``.name``."""

    def __new__(cls, text="", name=""):
        obj = super().__new__(cls, text)
        obj.name = name
        return obj


# Raw control bytes / sequences, named for readability.
CTRL_A, CTRL_B, CTRL_D, CTRL_E, CTRL_F = "\x01", "\x02", "\x04", "\x05", "\x06"
CTRL_H, CTRL_K, CTRL_L, CTRL_U, CTRL_W = "\x08", "\x0b", "\x0c", "\x15", "\x17"
CTRL_C, DEL, ESC, TAB = "\x03", "\x7f", "\x1b", "\t"
CTRL_J, CTRL_M = "\x0a", "\x0d"  # accept-line aliases (Enter)
META_D, META_BS = "\x1bd", "\x1b\x7f"
# No-op readline families (abort, quoted-insert, undo, transpose, yank, search).
CTRL_G, CTRL_Q, CTRL_V, CTRL_R, CTRL_T, CTRL_Y, CTRL_US = (
    "\x07", "\x11", "\x16", "\x12", "\x14", "\x19", "\x1f",
)
CTRL_X = "\x18"


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


# ── quit-key detection ────────────────────────────────────────────────────────

def test_is_quit_key_accepts_raw_ctrl_c_and_readable_token():
    assert loop.is_quit_key(CTRL_C) is True
    assert loop.is_quit_key("ctrl+c") is True
    assert loop.is_quit_key("a") is False
    assert loop.is_quit_key(Key(name="KEY_LEFT")) is False


# ── key -> action mapping (one unified, table-driven function) ────────────────

@pytest.mark.parametrize(
    "key, expected",
    [
        # named escape sequences via Keystroke.name
        (Key(name="KEY_LEFT"), MoveCursorLeft()),
        (Key(name="KEY_RIGHT"), MoveCursorRight()),
        (Key(name="KEY_HOME"), MoveCursorHome()),
        (Key(name="KEY_END"), MoveCursorEnd()),
        (Key(name="KEY_BACKSPACE"), Backspace()),
        (Key(name="KEY_DELETE"), DeleteChar()),
        (Key(name="KEY_ESCAPE"), ClearFilter()),
        # readline control chords via raw text
        (CTRL_A, MoveCursorHome()),
        (CTRL_E, MoveCursorEnd()),
        (CTRL_B, MoveCursorLeft()),
        (CTRL_F, MoveCursorRight()),
        (CTRL_D, DeleteChar()),
        (CTRL_H, Backspace()),
        (DEL, Backspace()),
        (CTRL_K, KillLine()),
        (CTRL_U, UnixLineDiscard()),
        (CTRL_W, BackwardKillWord()),
        (CTRL_L, Redraw()),
        (ESC, ClearFilter()),
        # meta / Alt word kills
        (META_D, KillWord()),
        (META_BS, BackwardKillWord()),
        # Tab / ctrl+i -> bang autocomplete (the reducer applies the ghost gate)
        (Key(name="KEY_TAB"), AutocompleteBang()),
        (TAB, AutocompleteBang()),
        # Enter / ctrl+j / ctrl+m -> accept-line (edit selected / submit)
        (Key(name="KEY_ENTER"), AcceptLine()),
        (CTRL_M, AcceptLine()),
        (CTRL_J, AcceptLine()),
        # printable insertion (incl. a literal bang)
        ("a", InsertChar("a")),
        ("3", InsertChar("3")),
        ("!", InsertChar("!")),
    ],
)
def test_key_to_action_maps_supported_keys(key, expected):
    assert loop.key_to_action(key) == expected


@pytest.mark.parametrize(
    "key",
    [
        CTRL_X,
        CTRL_C,                  # quit is handled by is_quit_key, not key_to_action
        # no-op readline families:
        CTRL_G, CTRL_Q, CTRL_V, CTRL_US, CTRL_T, CTRL_Y, CTRL_R,
    ],
)
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


def test_bang_inserts_a_literal_character_via_loop():
    _, frames = run_keys(["!"])
    assert "Filter: !" in filter_line(frames[-1])


def test_readline_alias_moves_cursor_end_to_end():
    # type "a", then ctrl+b (backward-char) should move the cursor left.
    _, frames = run_keys(["a", CTRL_B])
    assert len(frames) == 3  # initial + insert + cursor move


def test_ctrl_w_deletes_previous_word_via_loop():
    _, frames = run_keys(["a", "b", " ", "c", CTRL_W])
    assert "Filter: ab " in filter_line(frames[-1])


def test_named_arrow_key_moves_cursor_via_loop():
    # A blessed-style named keystroke drives the same action as ctrl+b.
    _, frames = run_keys(["a", Key(name="KEY_LEFT")])
    assert len(frames) == 3  # initial + insert + cursor move


def test_unsupported_keys_do_not_rerender():
    # FR30: an unsupported key produces no new frame and no state change.
    _, frames = run_keys([CTRL_X, CTRL_G])
    assert len(frames) == 1  # only the initial frame


@pytest.mark.parametrize(
    "family_key",
    [CTRL_G, CTRL_Q, CTRL_V, CTRL_US, CTRL_T, CTRL_Y, CTRL_R],
)
def test_noop_readline_families_leave_state_and_output_unchanged(family_key):
    # Establish a non-trivial filter, then fire the no-op key: no new frame.
    _, frames = run_keys(["a", "b", family_key])
    assert len(frames) == 3  # initial + 2 inserts; the no-op adds none
    assert "Filter: ab" in filter_line(frames[-1])


# ── Tab / ctrl+i bang autocomplete (gated by the reducer) ────────────────────

@pytest.mark.parametrize("tab_key", [Key(name="KEY_TAB"), TAB])
def test_tab_autocompletes_the_metafilter_when_the_ghost_is_visible(tab_key):
    # Fresh storyboard: empty filter, one unresolved collision -> the ghost is
    # visible, so Tab (and ctrl+i, the same \t byte) autocompletes a leading !.
    _, frames = run_keys([tab_key])
    assert len(frames) == 2  # initial + the autocomplete repaint
    assert "Filter: !" in filter_line(frames[-1])


def test_second_tab_does_not_clear_the_inserted_bang():
    # The first Tab inserts !; the second is a no-op against the now-non-empty
    # buffer and must not clear it (no extra frame).
    _, frames = run_keys([TAB, TAB])
    assert len(frames) == 2  # initial + first Tab only
    assert "Filter: !" in filter_line(frames[-1])


def test_tab_does_not_autocomplete_when_the_filter_is_non_empty():
    # With text already typed the ghost is gone, so Tab is a no-op: no new frame.
    _, frames = run_keys(["a", TAB])
    assert len(frames) == 2  # initial + the "a" insert; Tab adds none
    assert "Filter: a" in filter_line(frames[-1])


def test_ctrl_l_rerenders_only_without_mutating_state():
    # ctrl+l re-renders (a new identical frame) but never mutates state.
    _, frames = run_keys(["a", "b", CTRL_L])
    assert len(frames) == 4  # initial + 2 inserts + 1 redraw
    assert frames[-1] == frames[-2]  # redraw produced an identical frame


def test_recognised_noop_action_does_not_rerender():
    # Esc clears the filter, but on an already-empty filter that mutation is a
    # no-op (the reducer returns the same state object), so the loop must not
    # repaint — only the initial frame is produced.
    _, frames = run_keys([ESC])
    assert len(frames) == 1


def test_redundant_clear_after_typing_still_rerenders_once_then_skips():
    # First esc clears the typed text (a real change → repaint); a second esc is
    # a no-op on the now-empty filter and produces no further frame.
    _, frames = run_keys(["a", ESC, ESC])
    assert len(frames) == 3  # initial + insert + first (effective) clear


def test_quit_key_exits_cleanly_with_none():
    result, frames = run_keys(["a", CTRL_C, "b"])
    assert result is None
    # the trailing "b" after the quit key is never processed
    assert len(frames) == 2  # initial + the "a" insert


# ── max-length flash burst: bounded-timeout read + tick (TASK-009, §7.6/§12.1) ─

def test_flash_timeout_blocks_when_no_burst_is_pending():
    from mapping_resolution_tui.reducer import make_initial_state
    from tests.fixtures.storyboard import make_config, make_mappings

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    # No edit -> no burst -> a plain blocking read (None), never a poll.
    assert loop._flash_timeout(state, 0.0) is None


def test_flash_timeout_is_the_remaining_burst_window():
    from tests.conftest import _build_frame_11_state

    state = _build_frame_11_state()  # flash armed at now=0.0 -> deadline 0.150
    assert loop._flash_timeout(state, 0.10) == pytest.approx(0.05)


def test_flash_timeout_blocks_once_the_deadline_has_passed():
    from tests.conftest import _build_frame_11_state

    state = _build_frame_11_state()
    assert loop._flash_timeout(state, 0.20) is None


def test_burst_wakes_and_rerenders_the_held_frame_without_a_keypress():
    """A timed-out read mid-burst re-renders the burst-to-held transition (§7.6).

    Drives the event loop directly from a burst-armed state with a scripted
    reader and clock: the read while the burst is pending uses the finite
    remaining window, a timed-out read (``None``) re-renders without mutating
    state, and the subsequent read once the deadline has passed blocks (``None``
    timeout — no polling).
    """
    from tests.conftest import _build_frame_11_state, make_pyte_screen
    from mapping_resolution_tui.reducer import _BURST_DURATION

    state = _build_frame_11_state()
    deadline = _BURST_DURATION  # armed at now=0.0
    now = [deadline - 0.05]     # start mid-burst
    seen_timeouts = []
    steps = iter(["tick", "eof"])

    def read(timeout):
        seen_timeouts.append(timeout)
        step = next(steps)
        if step == "tick":
            now[0] = deadline + 0.05  # advance past the deadline before re-render
            return None               # a re-render tick
        return loop._EOF

    frames = []
    loop._event_loop(state, read, frames.append, lambda: now[0])

    # initial render (mid-burst) + one tick re-render (post-deadline); no reduce.
    assert len(frames) == 2
    # the burst read used the finite remaining window; the read after it blocked.
    assert seen_timeouts[0] == pytest.approx(0.05)
    assert seen_timeouts[1] is None
    # burst -> held: capped icon reverse-video in the first frame, plain in the next.
    assert make_pyte_screen(frames[0]).buffer[4][32].reverse is True
    assert make_pyte_screen(frames[1]).buffer[4][32].reverse is False
