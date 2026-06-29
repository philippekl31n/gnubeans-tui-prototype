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
def frame_8_lines():
    """Frame 8: single-character text filter '1' over a collision-free dataset.

    The AT-T collision on ordinal 3 is resolved to 'ATT' first — as the
    storyboard does before frame 8 — so the dataset is collision-free and the
    header shows the submit affordance (spec §3.2). The reviewer then types '1'
    via a real InsertChar dispatch; visible rows narrow to ordinals 1, 4 (token
    C100-F), 10, and 11.
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
def frame_2_lines():
    """Frame 2: collision metafilter engaged via Tab from frame 1a (TASK-003).

    Drives the real input layer: a Tab keystroke is normalised by
    ``key_to_action`` into ``AutocompleteBang`` and dispatched, autocompleting a
    leading ``!`` (``filter.raw='!'``, ``filter.cursor=1``, collision-only
    derived). Only the two collision rows 2 and 3 remain; the post-mutation clamp
    moves the selection onto row 2. The under-full 2-row frame ends at the footer.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.loop import key_to_action
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, key_to_action("\t"))
    return render_lines(state)


@pytest.fixture
def frame_2_screen(frame_2_lines):
    return make_pyte_screen(frame_2_lines)


@pytest.fixture
def frame_esc_clear_lines():
    """Frame esc-clear: Esc from a filtered state restores every row (TASK-003).

    A text filter ``1`` is typed (keeping ordinal 1 selected and visible), then
    Esc clears ``filter.raw`` and resets ``filter.cursor`` to 0. The result is
    byte-identical to frame 1a: all 11 rows restored, the ``Tab to view
    collisions`` ghost, and row 1 selected.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.loop import key_to_action
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, key_to_action("1"))
    state = reduce(state, key_to_action("\x1b"))
    return render_lines(state)


@pytest.fixture
def frame_esc_clear_screen(frame_esc_clear_lines):
    return make_pyte_screen(frame_esc_clear_lines)


@pytest.fixture
def frame_3_lines():
    """Frame 3: collision-only and text '3' active (TASK-004).

    Drives the input layer: Tab then '3'. Only ordinal 3 remains.
    The selected ordinal is 3.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.loop import key_to_action
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, key_to_action("\t"))
    state = reduce(state, key_to_action("3"))
    return render_lines(state)


@pytest.fixture
def frame_3_screen(frame_3_lines):
    return make_pyte_screen(frame_3_lines)


@pytest.fixture
def frame_13_lines():
    """Frame 13: no match state (TASK-004).

    Filter typed that matches nothing ('999'). Empty body row rendered.
    Footer shows NO_MATCHING_ROWS error.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.loop import key_to_action
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    for c in "999":
        state = reduce(state, key_to_action(c))
    return render_lines(state)


@pytest.fixture
def frame_13_screen(frame_13_lines):
    return make_pyte_screen(frame_13_lines)


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
