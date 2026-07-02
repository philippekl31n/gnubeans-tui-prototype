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
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.TAB)
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
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, "1")
    state = reduce(state, KeyEvent.ESCAPE)
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
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
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
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.TAB)
    state = reduce(state, "3")
    return render_lines(state)


@pytest.fixture
def frame_3_screen(frame_3_lines):
    return make_pyte_screen(frame_3_lines)


@pytest.fixture
def frame_4_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.TAB)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    return render_lines(state)


@pytest.fixture
def frame_4_screen(frame_4_lines):
    return make_pyte_screen(frame_4_lines)


@pytest.fixture
def frame_5_lines():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.TAB)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, "A")
    state = reduce(state, "T")
    state = reduce(state, "T")
    return render_lines(state)


@pytest.fixture
def frame_5_screen(frame_5_lines):
    return make_pyte_screen(frame_5_lines)

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
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, "2")
    return render_lines(state)


@pytest.fixture
def frame_13_screen(frame_13_lines):
    return make_pyte_screen(frame_13_lines)

@pytest.fixture
def frame_9_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    # Assume we cleared collisions and set target for ordinal 3
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)

    # Ordinal 1 is APPLE and selected
    state = reduce(state, KeyEvent.ENTER)
    return render_lines(state)

@pytest.fixture
def frame_9_screen(frame_9_lines):
    return make_pyte_screen(frame_9_lines)

@pytest.fixture
def frame_10_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)

    state = reduce(state, KeyEvent.ENTER)
    for char in "44PL":
        state = reduce(state, char)
    return render_lines(state)

@pytest.fixture
def frame_10_screen(frame_10_lines):
    return make_pyte_screen(frame_10_lines)

@pytest.fixture
def frame_11_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)

    state = reduce(state, KeyEvent.ENTER)
    for char in "44PL56789012345678901234":  # 24 chars, fills the cap
        state = reduce(state, char)
    state = reduce(state, "5", now=0.0)  # 25th char: discarded, arms the flash (FR20)
    return render_lines(state)

@pytest.fixture
def frame_11_screen(frame_11_lines):
    return make_pyte_screen(frame_11_lines)

@pytest.fixture
def frame_12a_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)

    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, KeyEvent.SELECTION_DOWN)  # pointer -> source 0 ("AAPL")
    return render_lines(state)

@pytest.fixture
def frame_12a_screen(frame_12a_lines):
    return make_pyte_screen(frame_12a_lines)

@pytest.fixture
def frame_12b_lines():
    from dataclasses import replace
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [replace(m, target_value="ATT") if m.ordinal == 3 else m for m in state.mappings]
    state = replace(state, mappings=mappings)

    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, KeyEvent.SELECTION_UP)  # pointer -> source 1 ("APPLE")
    return render_lines(state)

@pytest.fixture
def frame_12b_screen(frame_12b_lines):
    return make_pyte_screen(frame_12b_lines)

@pytest.fixture
def frame_esc_from_edit_lines(frame_8_lines):
    """Esc-from-edit frame: cancelling an edit restores the pre-edit frame 8.

    From the frame 8 context (resolved dataset, filter '1', ordinal 1 selected)
    the reviewer enters edit mode, types 'XYZ', and presses Esc. The buffer is
    discarded and the filter, selection, and scroll are preserved exactly, so
    the frame is bit-identical to frame 8 (TASK-008 / FR16).
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, KeyEvent.ENTER)
    for char in "XYZ":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ESCAPE)
    return render_lines(state)


@pytest.fixture
def frame_esc_from_edit_screen(frame_esc_from_edit_lines):
    return make_pyte_screen(frame_esc_from_edit_lines)


@pytest.fixture
def frame_submit_no_resolution_lines():
    """Submit-no-resolution frame: a valid commit that leaves collisions open.

    From the initial browsing state (AT-T collision outstanding, no filter) the
    reviewer edits ordinal 1 (APPLE), types 'APPL', and submits. The commit
    updates row 1's target token, the app returns to BROWSING with the empty
    filter intact, and the AT-T markers on rows 2 and 3 are recalculated and
    remain (TASK-008 / FR8/FR16/FR22).
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.ENTER)
    for char in "APPL":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ENTER)
    return render_lines(state)


@pytest.fixture
def frame_submit_no_resolution_screen(frame_submit_no_resolution_lines):
    return make_pyte_screen(frame_submit_no_resolution_lines)


@pytest.fixture
def frame_6_lines():
    """Frame 6: accept confirmation entered by resolving the last collision.

    From the initial browsing state the reviewer selects the AT-T collision
    (ordinal 3), edits it to ``ATT`` and submits. The post-commit collision
    count is zero, so the app auto-enters the accept confirmation with
    ``choice = NO`` (FR23 / spec §4.2). The full table renders at ``scrollOffset
    = 0`` with no row cursor and the ``Accept all? [y/N]`` prompt (spec §6.4–6.6,
    storyboard frame 6). The footer follows the choice-driven rule, so with
    ``choice = NO`` it renders the ``↵ edit mappings`` hint — identical to frame
    7a and never the obsolete ``↵ confirm`` (spec §6.6 / §10.2).
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    for char in "ATT":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ENTER)
    return render_lines(state)


@pytest.fixture
def frame_6_screen(frame_6_lines):
    return make_pyte_screen(frame_6_lines)


@pytest.fixture
def frame_7a_lines():
    """Frame 7a: one down-arrow scroll of the accept-confirmation table.

    Continues frame 6 (resolve the AT-T collision, submit, auto-enter the accept
    confirmation with ``choice = NO``) with a single ``↓``. In CONFIRMING there is
    no row cursor, so the arrow scrolls the body window only: ``scrollOffset``
    advances from 0 to 1 and the body shows ordinals 2..10 at normal brightness,
    while ``selectedOrdinal`` is unaffected (spec §8.4 / §10.1 frame 7a). The
    ``Accept all? [y/N]`` prompt and the ``↑↓ scroll · shift+↑↓ pageup/dn ·
    ↵ edit mappings`` footer are unchanged from frame 6.
    """
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    for char in "ATT":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ENTER)   # frame 6: CONFIRMING, scrollOffset=0
    state = reduce(state, KeyEvent.SELECTION_DOWN)  # ↓ scrolls the window by one
    return render_lines(state)


@pytest.fixture
def frame_7a_screen(frame_7a_lines):
    return make_pyte_screen(frame_7a_lines)


@pytest.fixture
def frame_14_lines():
    """Frame 14: re-entered accept confirmation over an active filter.

    The AT-T collision (ordinal 3) is resolved to ``ATT`` as the storyboard does
    before frame 14, then the reviewer applies the ``12`` text filter (frame 13,
    no matching rows) and presses ``ctrl+s`` to re-enter the accept confirmation.
    ``ctrl+s`` is accepted because no collision remains (spec §4.2), and the
    confirming table MUST ignore that filter and render the full 11-row list
    windowed at ``scrollOffset = 0`` (spec §8.2 / §10.1 frame 14).
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, "2")  # filter "12" matches no rows (frame 13)
    state = reduce(state, KeyEvent.SUBMIT)  # ctrl+s re-enters the accept confirmation
    return render_lines(state)


@pytest.fixture
def frame_14_screen(frame_14_lines):
    return make_pyte_screen(frame_14_lines)


@pytest.fixture
def frame_15_lines():
    """Frame 15: the terminal accepted-result frame (spec §6.7).

    From the accept confirmation the reviewer toggles ``choice = YES`` and
    confirms, committing all mappings and exiting the TUI. The render collapses
    to the two-row result frame — the created message over a bare prompt glyph
    (storyboard frame 15). The commit is constructed directly because the accept
    transition is a later story (TASK-010).
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines
    from mapping_resolution_tui.state import (
        ConfirmationChoice,
        ConfirmationKind,
        Mode,
        ResultState,
    )

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(
        state,
        mappings=mappings,
        mode=Mode.CONFIRMING,
        confirmation=replace(
            state.confirmation,
            kind=ConfirmationKind.ACCEPT,
            choice=ConfirmationChoice.YES,
        ),
        result=ResultState(status="ACCEPTED"),
    )
    return render_lines(state)


@pytest.fixture
def frame_15_screen(frame_15_lines):
    return make_pyte_screen(frame_15_lines)


@pytest.fixture
def frame_accept_terminal_lines():
    """Accepted terminal frame reached end-to-end through the reducer (spec §6.7).

    Continuing the storyboard frame 13 → 14 → 15 path: with the AT-T collision
    resolved (ordinal 3 -> ``ATT``) and the non-matching ``12`` filter applied,
    ``ctrl+s`` re-enters the accept confirmation (frame 14), ``y`` toggles the
    choice to YES, and ``Enter`` commits every mapping — ``result.status =
    ACCEPTED``. The render collapses to the two-row result frame of the created
    message over a bare prompt glyph (storyboard frame 15). Unlike ``frame_15``,
    the ACCEPTED state here is produced solely by reducer transitions, proving
    the full accept flow.
    """
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.events import KeyEvent
    from mapping_resolution_tui.reducer import make_initial_state, reduce
    from mapping_resolution_tui.renderer import render_lines

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    state = replace(state, mappings=mappings)
    state = reduce(state, "1")
    state = reduce(state, "2")  # filter "12" matches no rows (frame 13)
    state = reduce(state, KeyEvent.SUBMIT)  # ctrl+s re-enters accept confirmation
    state = reduce(state, "y")              # toggle the choice to YES
    state = reduce(state, KeyEvent.ENTER)   # commit -> ACCEPTED
    return render_lines(state)


@pytest.fixture
def frame_accept_terminal_screen(frame_accept_terminal_lines):
    return make_pyte_screen(frame_accept_terminal_lines)


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
