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
    from mapping_resolution_tui.actions import Escape, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, InsertChar("1"))
    state = reduce(state, Escape())
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
def frame_4_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AutocompleteBang, AcceptLine, MoveSelectionDown
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, AutocompleteBang())
    state = reduce(state, MoveSelectionDown())
    state = reduce(state, AcceptLine())
    return render_lines(state)


@pytest.fixture
def frame_4_screen(frame_4_lines):
    return make_pyte_screen(frame_4_lines)


@pytest.fixture
def frame_5_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AutocompleteBang, AcceptLine, MoveSelectionDown, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, AutocompleteBang())
    state = reduce(state, MoveSelectionDown())
    state = reduce(state, AcceptLine())
    state = reduce(state, InsertChar("A"))
    state = reduce(state, InsertChar("T"))
    state = reduce(state, InsertChar("T"))
    return render_lines(state)


@pytest.fixture
def frame_5_screen(frame_5_lines):
    return make_pyte_screen(frame_5_lines)

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

@pytest.fixture
def frame_9_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    # Assume we cleared collisions and set target for ordinal 3
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    # Ordinal 1 is APPLE and selected
    state = reduce(state, AcceptLine())
    return render_lines(state)

@pytest.fixture
def frame_9_screen(frame_9_lines):
    return make_pyte_screen(frame_9_lines)

@pytest.fixture
def frame_12a_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import MoveSelectionDown
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines
    from dataclasses import replace

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    from mapping_resolution_tui.actions import AcceptLine
    state = reduce(state, AcceptLine())
    state = reduce(state, MoveSelectionDown())
    return render_lines(state)

@pytest.fixture
def frame_12a_screen(frame_12a_lines):
    return make_pyte_screen(frame_12a_lines)

@pytest.fixture
def frame_12b_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import MoveSelectionUp
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines
    from dataclasses import replace

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    from mapping_resolution_tui.actions import AcceptLine
    state = reduce(state, AcceptLine())
    state = reduce(state, MoveSelectionUp())
    return render_lines(state)

@pytest.fixture
def frame_12b_screen(frame_12b_lines):
    return make_pyte_screen(frame_12b_lines)

@pytest.fixture
def frame_10_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    state = reduce(state, AcceptLine())
    for char in "44PL":
        state = reduce(state, InsertChar(char))
    return render_lines(state)

@pytest.fixture
def frame_10_screen(frame_10_lines):
    return make_pyte_screen(frame_10_lines)

@pytest.fixture
def frame_11_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    state = reduce(state, AcceptLine())
    for char in "44PL56789012345678901234":
        state = reduce(state, InsertChar(char))
    state = reduce(state, InsertChar("5"), now=0.0)  # 25th char: discarded, arms the flash (FR20)
    return render_lines(state, now=0.2)

@pytest.fixture
def frame_11_burst_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)
    
    state = reduce(state, AcceptLine())
    for char in "44PL56789012345678901234":
        state = reduce(state, InsertChar(char))
    state = reduce(state, InsertChar("5"), now=0.0)  # 25th char: discarded, arms the flash (FR20)
    # Render at exactly 0.0 to capture the start of the burst
    return render_lines(state, now=0.0)

@pytest.fixture
def frame_11_burst_screen(frame_11_burst_lines):
    return make_pyte_screen(frame_11_burst_lines)

@pytest.fixture
def frame_11_screen(frame_11_lines):
    return make_pyte_screen(frame_11_lines)

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

@pytest.fixture
def frame_esc_from_edit_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar, Escape
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    for char in "!AT":
        state = reduce(state, InsertChar(char))
    state = reduce(state, AcceptLine())
    state = reduce(state, InsertChar("X"))
    state = reduce(state, Escape())
    return render_lines(state)

@pytest.fixture
def frame_esc_from_edit_screen(frame_esc_from_edit_lines):
    return make_pyte_screen(frame_esc_from_edit_lines)

@pytest.fixture
def frame_submit_no_resolution_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import AcceptLine, InsertChar, MoveCursorEnd, DeleteChar
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    for char in "APPLE":
        state = reduce(state, InsertChar(char))
    state = reduce(state, AcceptLine())
    # APPLE buffer is empty initially because target is None.
    for char in "GOOGL":
        state = reduce(state, InsertChar(char))
    state = reduce(state, AcceptLine())
    return render_lines(state)

@pytest.fixture
def frame_submit_no_resolution_screen(frame_submit_no_resolution_lines):
    return make_pyte_screen(frame_submit_no_resolution_lines)
