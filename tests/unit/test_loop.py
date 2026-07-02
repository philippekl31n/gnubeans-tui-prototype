"""
Unit tests for the blocking event loop and unified input layer (TASK-001/002).

A single table-driven ``key_to_event`` normalises every keypress — named escape
sequences via ``Keystroke.name`` and readline control chords / meta sequences via
the raw key text — into a mode-neutral :class:`~mapping_resolution_tui.events.KeyEvent`
or a bare ``str`` for printable characters (FR29). Unsupported keys and the no-op
readline families return ``None`` so the loop leaves state and output unchanged
(FR30). The loop is driven through its injectable ``keys``/``render`` seams, with
``Key`` standing in for a blessed ``Keystroke`` (a str carrying a ``.name``).
"""

import pytest

from mapping_resolution_tui import loop
from mapping_resolution_tui.events import KeyEvent
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
CTRL_S = "\x13"
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


@pytest.fixture
def sigint_sends(monkeypatch):
    """Stub the loop's SIGINT seam, returning the list of recorded sends.

    Any test driving the second-ctrl+c force-exit needs this so the real
    interrupt never reaches the test process.
    """
    sends: list[bool] = []
    monkeypatch.setattr(loop, "_send_sigint", lambda: sends.append(True))
    return sends


# ── quit-key normalisation ───────────────────────────────────────────────────

def test_key_to_event_maps_ctrl_c_and_readable_token_to_quit():
    # ctrl+c is an ordinary mode-dispatched event (spec §4.2 has a ctrl+c row
    # per mode), normalised like every other key: the raw control byte from a
    # live blessed keystroke and the readable config token from headless
    # drivers both collapse onto KeyEvent.QUIT.
    assert loop.key_to_event(CTRL_C) is KeyEvent.QUIT
    assert loop.key_to_event("ctrl+c") is KeyEvent.QUIT


# ── key -> event mapping (one unified, table-driven function) ─────────────────

@pytest.mark.parametrize(
    "key, expected",
    [
        # named escape sequences via Keystroke.name
        (Key(name="KEY_LEFT"),      KeyEvent.CURSOR_LEFT),
        (Key(name="KEY_RIGHT"),     KeyEvent.CURSOR_RIGHT),
        (Key(name="KEY_HOME"),      KeyEvent.CURSOR_HOME),
        (Key(name="KEY_END"),       KeyEvent.CURSOR_END),
        (Key(name="KEY_BACKSPACE"), KeyEvent.BACKSPACE),
        (Key(name="KEY_DELETE"),    KeyEvent.DELETE_CHAR),
        (Key(name="KEY_ESCAPE"),    KeyEvent.ESCAPE),
        (Key(name="KEY_ENTER"),     KeyEvent.ENTER),
        (Key(name="KEY_UP"),        KeyEvent.SELECTION_UP),
        # readline control chords via raw text
        (CTRL_A, KeyEvent.CURSOR_HOME),
        (CTRL_E, KeyEvent.CURSOR_END),
        (CTRL_B, KeyEvent.CURSOR_LEFT),
        (CTRL_F, KeyEvent.CURSOR_RIGHT),
        (CTRL_D, KeyEvent.DELETE_CHAR),
        (CTRL_H, KeyEvent.BACKSPACE),
        (DEL,    KeyEvent.BACKSPACE),
        (CTRL_K, KeyEvent.KILL_LINE),
        (CTRL_U, KeyEvent.UNIX_LINE_DISCARD),
        (CTRL_W, KeyEvent.BACKWARD_KILL_WORD),
        (CTRL_L, KeyEvent.REDRAW),
        (ESC,    KeyEvent.ESCAPE),
        ("\r",   KeyEvent.ENTER),
        ("\n",   KeyEvent.ENTER),
        # meta / Alt word kills
        (META_D,  KeyEvent.KILL_WORD),
        (META_BS, KeyEvent.BACKWARD_KILL_WORD),
        # Tab / ctrl+i -> bang autocomplete (the reducer applies the ghost gate)
        (Key(name="KEY_TAB"), KeyEvent.TAB),
        (TAB,                 KeyEvent.TAB),
        # ctrl+s -> SUBMIT (the reducer applies the zero-collision gate)
        (CTRL_S, KeyEvent.SUBMIT),
        # printable insertion (incl. a literal bang) — returned as bare str
        ("a", "a"),
        ("3", "3"),
        ("!", "!"),
    ],
)
def test_key_to_event_maps_supported_keys(key, expected):
    assert loop.key_to_event(key) == expected


@pytest.mark.parametrize(
    "key",
    [
        CTRL_X,
        # no-op readline families:
        CTRL_G, CTRL_Q, CTRL_V, CTRL_US, CTRL_T, CTRL_Y, CTRL_R,
    ],
)
def test_key_to_event_returns_none_for_unsupported_keys(key):
    assert loop.key_to_event(key) is None


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
    # A blessed-style named keystroke drives the same event as ctrl+b.
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


def test_double_ctrl_c_exits_with_none(sigint_sends):
    # TASK-012: the first ctrl+c opens the exit confirmation (frame 1b); the
    # second force-exits, and the trailing key is never processed.
    result, frames = run_keys(["a", CTRL_C, CTRL_C, "b"])
    assert result is None
    assert len(frames) == 3  # initial + the "a" insert + the exit prompt


# ── ctrl+c during EDITING cancels the edit (TASK-008, spec §4.2 / FR16) ──────

def test_ctrl_c_during_editing_cancels_the_edit_instead_of_quitting():
    # Enter edit on the selected row, type into the buffer, then ctrl+c: the
    # edit is discarded like Esc and the loop keeps consuming input — the
    # trailing "3" still reaches the filter and the run ends cleanly.
    result, frames = run_keys([Key(name="KEY_ENTER"), "X", CTRL_C, "3"])

    assert result is not None  # clean end-of-input exit, not a quit
    assert "Filter: 3" in filter_line(frames[-1])
    assert all(m.target_value is None for m in result)  # buffer discarded


def test_ctrl_c_cancel_rerenders_the_restored_browsing_frame():
    _, frames = run_keys([Key(name="KEY_ENTER"), CTRL_C])
    # initial + edit entry + cancel repaint
    assert len(frames) == 3
    assert "Filter:" in filter_line(frames[-1])  # back to the browsing prompt


def test_ctrl_c_in_browsing_opens_the_exit_prompt():
    result, frames = run_keys(["3", CTRL_C])
    # The run is still live: the exit prompt is painted and end-of-input ends
    # the loop with the mappings as they stand.
    assert result is not None
    assert any("Skip adding commodities?" in line for line in frames[-1])


def test_confirming_the_exit_prompt_skips_with_none():
    # ctrl+c, then y and Enter: a clean skip that adds no commodities.
    result, frames = run_keys(["3", CTRL_C, "y", Key(name="KEY_ENTER"), "4"])
    assert result is None
    # The trailing "4" never ran; the last frame is still the exit prompt.
    assert any("Skip adding commodities?" in line for line in frames[-1])
    assert not any("Filter: 34" in line for line in frames[-1])


def test_ctrl_c_in_confirming_opens_the_exit_prompt_and_a_second_forces_out(
    sigint_sends,
):
    # Resolve the final collision (ordinal 3 -> "ATT") to land in CONFIRMING,
    # then ctrl+c: the accept prompt becomes the exit confirmation (TASK-012,
    # spec §4.2); a second ctrl+c force-exits and the trailing key never runs.
    result, frames = run_keys(
        [Key(name="KEY_DOWN"), Key(name="KEY_DOWN"), Key(name="KEY_ENTER"),
         "A", "T", "T", Key(name="KEY_ENTER"), CTRL_C, CTRL_C, "3"]
    )
    assert result is None
    # The last frame is the exit prompt (no Filter line renders in CONFIRMING),
    # and the trailing "3" was never consumed into the filter.
    assert any("Skip adding commodities?" in line for line in frames[-1])
    assert not any("Filter: 3" in line for line in frames[-1])


def test_quit_does_not_render_a_terminal_frame(sigint_sends):
    # Force-exiting paints no §6.7 result frame: the last rendered frame is
    # the exit prompt the first ctrl+c opened.
    _, frames = run_keys(["3", CTRL_C, CTRL_C])
    assert len(frames) == 3  # initial + the "3" insert + the exit prompt


# ── the second ctrl+c sends a real SIGINT (TASK-012, spec §4.2/§6.7) ─────────


def test_second_ctrl_c_sends_sigint(sigint_sends):
    # The force-exit re-raises the interrupt through the _send_sigint seam,
    # stubbed by the fixture so the test process survives; the loop then
    # returns None.
    result, _ = run_keys(["3", CTRL_C, CTRL_C])
    assert result is None
    assert len(sigint_sends) == 1


def test_enter_on_yes_exit_skips_without_sigint(sigint_sends):
    # Enter on the YES exit confirmation is a clean skip: SKIPPED, no signal
    # (spec §4.1/§4.2 reserve SIGINT for the second ctrl+c).
    result, _ = run_keys([CTRL_C, "y", Key(name="KEY_ENTER")])
    assert result is None
    assert sigint_sends == []


def test_send_sigint_interrupts_this_process(monkeypatch):
    # The default seam delivers SIGINT to the running process; os.kill is
    # stubbed so the interrupt is observed rather than raised.
    import os
    import signal

    kills = []
    monkeypatch.setattr(loop.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    loop._send_sigint()
    assert kills == [(os.getpid(), signal.SIGINT)]


# ── accept confirmation produces output (TASK-010, spec §6.7) ─────────────────

_ACCEPT_KEYS = [
    # Resolve the final collision (ordinal 3 -> "ATT"): FR23 auto-enters the
    # accept confirmation; y then Enter commits every mapping.
    Key(name="KEY_DOWN"), Key(name="KEY_DOWN"), Key(name="KEY_ENTER"),
    "A", "T", "T", Key(name="KEY_ENTER"), "y", Key(name="KEY_ENTER"),
]


def test_accepting_returns_the_resolved_mappings():
    result, _ = run_keys(_ACCEPT_KEYS)
    assert result is not None
    assert next(m for m in result if m.ordinal == 3).target_value == "ATT"


def test_accepting_paints_the_terminal_result_frame():
    _, frames = run_keys(_ACCEPT_KEYS)
    assert frames[-1] == ["11 commodities created.", "❯"]


def test_ctrl_s_reentry_accept_flow_returns_the_resolved_mappings():
    # Enter on NO returns to BROWSING; ctrl+s re-enters (frame 14) and the
    # accept then completes exactly as the auto-entered confirmation does.
    keys = [
        Key(name="KEY_DOWN"), Key(name="KEY_DOWN"), Key(name="KEY_ENTER"),
        "A", "T", "T", Key(name="KEY_ENTER"),          # auto-entry, choice NO
        Key(name="KEY_ENTER"),                          # NO -> back to BROWSING
        "\x13", "y", Key(name="KEY_ENTER"),             # ctrl+s re-entry, accept
    ]
    result, frames = run_keys(keys)
    assert result is not None
    assert next(m for m in result if m.ordinal == 3).target_value == "ATT"
    assert frames[-1] == ["11 commodities created.", "❯"]
