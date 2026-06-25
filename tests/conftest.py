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

    The AT-T collision (ordinal 3) is resolved to 'ATT' as the storyboard does
    before frame 8, then the reviewer types '1'. Visible rows narrow to ordinals
    1, 4 (token C100-F), 10, and 11.
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.actions import InsertCharacter
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, InsertCharacter("1"))
    return render_lines(state)


@pytest.fixture
def frame_8_screen(frame_8_lines):
    return make_pyte_screen(frame_8_lines)


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
