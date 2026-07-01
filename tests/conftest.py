from pathlib import Path

import pytest
import pyte

SCREEN_COLS = 80


def make_pyte_screen(lines: list[str]) -> pyte.Screen:
    screen = pyte.Screen(SCREEN_COLS, len(lines))
    stream = pyte.Stream(screen)
    # Join with \r\n but no trailing newline — a final \r\n would scroll the last
    # line off the top in a screen sized exactly to len(lines).
    stream.feed("\r\n".join(lines))
    return screen


def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False)


@pytest.fixture(scope="session")
def update_snapshots(request):
    return request.config.getoption("--update-snapshots")


@pytest.fixture
def frame_1a_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.renderer import render_lines
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    return render_lines(state)


@pytest.fixture
def frame_1a_screen(frame_1a_lines):
    return make_pyte_screen(frame_1a_lines)


@pytest.fixture
def frame_2_lines():
    """Frame 2: Tab autocompletes a leading ``!`` collision metafilter from 1a.

    From the initial browsing state the reviewer presses Tab; the ``Tab to view
    collisions`` ghost is visible, so the bang autocompletes (``filter.raw='!'``,
    ``filter.cursor=1``, ``collision_only`` derived True). Visible rows narrow to
    the AT-T collision pair (ordinals 2 and 3) and selection clamps to row 2.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AutocompleteBang
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, AutocompleteBang())
    return render_lines(state)


@pytest.fixture
def frame_2_screen(frame_2_lines):
    return make_pyte_screen(frame_2_lines)


@pytest.fixture
def frame_esc_clear_lines():
    """Esc-clear frame: pressing Esc from a filtered state restores frame 1a.

    The reviewer types a ``1`` text filter (row 1 stays selected and visible)
    and then presses Esc; ``filter.raw`` is cleared, the cursor resets to 0, and
    all rows are restored, so the frame is bit-identical to frame 1a.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import ClearFilter, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, InsertChar("1"))
    state = reduce(state, ClearFilter())
    return render_lines(state)


@pytest.fixture
def frame_esc_clear_screen(frame_esc_clear_lines):
    return make_pyte_screen(frame_esc_clear_lines)


@pytest.fixture
def frame_8_lines():
    """Frame 8: single-character text filter '1' over a collision-free dataset.

    The AT-T collision (ordinal 3) is resolved to 'ATT' as the storyboard does
    before frame 8, then the reviewer types '1'. Visible rows narrow to ordinals
    1, 4 (token C100-F), 10, and 11.
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, InsertChar("1"))
    return render_lines(state)


@pytest.fixture
def frame_8_screen(frame_8_lines):
    return make_pyte_screen(frame_8_lines)


@pytest.fixture
def frame_3_lines():
    """Frame 3: collision metafilter plus the text filter ``3``.

    From the initial browsing state the reviewer presses Tab (autocompleting the
    leading ``!``) and then types ``3``: ``filter.raw='!3'``, ``collision_only``
    derives True and ``text='3'``. The only collision row whose ordinal/token
    matches ``3`` is ordinal 3, so the visible list narrows to it and the
    selection clamps from ordinal 2 to ordinal 3 (spec §3.4 / §10.1 frame 3).
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AutocompleteBang, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, AutocompleteBang())
    state = reduce(state, InsertChar("3"))
    return render_lines(state)


@pytest.fixture
def frame_3_screen(frame_3_lines):
    return make_pyte_screen(frame_3_lines)


@pytest.fixture
def frame_13_lines():
    """Frame 13: a text filter that matches no rows (empty result).

    The AT-T collision (ordinal 3) is resolved to 'ATT' as the storyboard does
    before frame 13, then the reviewer types '12'. No ordinal or target token
    contains '12', so ``visibleRows`` is empty, ``selectedOrdinal`` is None, and
    the body renders a single blank row with the error footer (spec §3.4 / §6.6;
    storyboard frame 13).
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, InsertChar("1"))
    state = reduce(state, InsertChar("2"))
    return render_lines(state)


@pytest.fixture
def frame_13_screen(frame_13_lines):
    return make_pyte_screen(frame_13_lines)


# ── EDITING golden frames (TASK-006, spec §7) ────────────────────────────────
#
# These build EDITING states by dispatching real actions through the loop's
# reducer, mirroring the storyboard transitions. ``make_mappings`` is randomized,
# but ordinals are assigned 1..11 after the deterministic bootstrap sort, so
# ordinal 1 is always the APPLE mapping and ordinals 2/3 the AT-T collision pair.


def _build_frame_4_state():
    """Frame 4: enter edit on the filtered AT-T collision row (ordinal 3).

    From the metafilter ``!3`` the reviewer backspaces to ``!`` (selection clamps
    to ordinal 2), arrows down to ordinal 3, and presses Enter — entering EDITING
    with an empty buffer and the ghost suffix ``AT-T`` (its ``target_value`` is
    null).
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import (
        AcceptLine,
        AutocompleteBang,
        Backspace,
        InsertChar,
        MoveSelectionDown,
    )
    from mapping_resolution_tui.reducer import make_initial_state, reduce

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, AutocompleteBang())   # filter.raw "!"
    state = reduce(state, InsertChar("3"))       # filter.raw "!3", row 3 selected
    state = reduce(state, Backspace())           # filter.raw "!", clamps to row 2
    state = reduce(state, MoveSelectionDown())   # select row 3
    state = reduce(state, AcceptLine())          # enter EDITING on row 3
    return state


def _build_frame_5_state():
    """Frame 5: type ``A``, ``T``, ``T`` over the ghost, yielding buffer ``ATT``."""
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import reduce

    state = _build_frame_4_state()
    for ch in "ATT":
        state = reduce(state, InsertChar(ch))
    return state


def _build_frame_9_state():
    """Frame 9: enter edit on the APPLE mapping (ordinal 1) over a collision-free set.

    The AT-T collision (ordinal 3) is resolved to ``ATT`` first (as the storyboard
    does before frame 8), the reviewer filters to ``1`` (rows 1, 4, 10, 11), then
    presses Enter on ordinal 1 — EDITING with an empty buffer and ghost ``APPLE``.
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, InsertChar("1"))   # filter.raw "1"
    state = reduce(state, AcceptLine())      # enter EDITING on row 1
    return state


def _build_frame_10_state():
    """Frame 10: type ``4``, ``4``, ``P``, ``L`` — invalid buffer ``44PL``."""
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import reduce

    state = _build_frame_9_state()
    for ch in "44PL":
        state = reduce(state, InsertChar(ch))
    return state


def _build_frame_11_state():
    """Frame 11: fill the buffer to the 24-char cap, then discard a 25th character.

    From ``44PL`` the reviewer types 20 more digits (reaching the 24-column cap),
    then one further digit that is discarded and arms the max-length flash
    ``24 chars max`` (FR20). ``now`` is pinned so the flash timestamp is
    deterministic; only the immediate render is asserted.
    """
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import reduce

    state = _build_frame_10_state()
    for ch in "56789012345678901234":  # 20 digits -> 24-char buffer
        state = reduce(state, InsertChar(ch), now=0.0)
    state = reduce(state, InsertChar("5"), now=0.0)  # 25th char discarded -> flash
    return state


def _build_frame_12a_state():
    """Frame 12a: ``↓`` from frame 9 points at the first source and autofills ``AAPL``.

    From the empty-buffer edit on the APPLE mapping (frame 9) the reviewer presses
    ``↓``: the token buffer is saved to ``source_entry_buffer``, focus moves to the
    source list at the first active source (``cmdty_id: "AAPL"``), and the buffer
    autofills to ``AAPL`` — a valid token, so the ``✓`` icon renders (spec §7.4 /
    FR21).
    """
    from mapping_resolution_tui.actions import MoveSelectionDown
    from mapping_resolution_tui.reducer import reduce

    return reduce(_build_frame_9_state(), MoveSelectionDown())


def _build_frame_12b_state():
    """Frame 12b: ``↑`` from frame 9 wraps to the last source and autofills ``APPLE``.

    From frame 9 the reviewer presses ``↑``: focus moves to the source list at the
    last active source (``user_symbol: "APPLE"``) and the buffer autofills to
    ``APPLE`` — valid, ``✓`` icon (spec §7.4 / FR21).
    """
    from mapping_resolution_tui.actions import MoveSelectionUp
    from mapping_resolution_tui.reducer import reduce

    return reduce(_build_frame_9_state(), MoveSelectionUp())


@pytest.fixture
def frame_4_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_4_state())


@pytest.fixture
def frame_4_screen(frame_4_lines):
    return make_pyte_screen(frame_4_lines)


@pytest.fixture
def frame_5_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_5_state())


@pytest.fixture
def frame_5_screen(frame_5_lines):
    return make_pyte_screen(frame_5_lines)


@pytest.fixture
def frame_9_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_9_state())


@pytest.fixture
def frame_9_screen(frame_9_lines):
    return make_pyte_screen(frame_9_lines)


@pytest.fixture
def frame_10_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_10_state())


@pytest.fixture
def frame_10_screen(frame_10_lines):
    return make_pyte_screen(frame_10_lines)


@pytest.fixture
def frame_11_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_11_state())


@pytest.fixture
def frame_11_screen(frame_11_lines):
    return make_pyte_screen(frame_11_lines)


@pytest.fixture
def frame_11_burst_lines():
    """Frame 11, burst phase: the same over-limit state rendered mid-burst.

    ``_build_frame_11_state`` arms the flash at ``now=0.0`` (deadline 150ms), so
    rendering at half the window puts the capped icon and footer error in the
    reverse-video burst style (spec §7.6). Geometry is identical to frame 11.
    """
    from mapping_resolution_tui.reducer import _BURST_DURATION
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_11_state(), now=_BURST_DURATION / 2)


@pytest.fixture
def frame_11_burst_screen(frame_11_burst_lines):
    return make_pyte_screen(frame_11_burst_lines)


@pytest.fixture
def frame_12a_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_12a_state())


@pytest.fixture
def frame_12a_screen(frame_12a_lines):
    return make_pyte_screen(frame_12a_lines)


@pytest.fixture
def frame_12b_lines():
    from mapping_resolution_tui.renderer import render_lines
    return render_lines(_build_frame_12b_state())


@pytest.fixture
def frame_12b_screen(frame_12b_lines):
    return make_pyte_screen(frame_12b_lines)


@pytest.fixture
def assert_snapshot(update_snapshots):
    def _check(screen: pyte.Screen, snapshot_path: Path):
        actual = "\n".join(row.rstrip() for row in screen.display) + "\n"
        if update_snapshots:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(actual, encoding="utf-8")
        else:
            expected = snapshot_path.read_text(encoding="utf-8")
            assert actual == expected, (
                f"Snapshot mismatch: {snapshot_path}\n"
                "Run with --update-snapshots to regenerate."
            )
    return _check
