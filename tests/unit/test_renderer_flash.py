"""
Unit tests for the max-length flash burst/held phases (TASK-009, spec §7.6).

The flash is a two-phase "pop-then-hold" micro-animation over the held-error
behavior of §7.5: while ``now < edit.max_length_flash_until`` the capped
validation icon and footer error render reverse-video (burst); once the deadline
passes they render in the ordinary INVALID style (held). ``_max_length_phase``
derives the phase from frozen state and an injected render-time ``now``; the
styling is asserted through pyte cell reverse attributes on a static frame.
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.reducer import _BURST_DURATION, make_initial_state
from mapping_resolution_tui.renderer import (
    _FlashPhase,
    _max_length_phase,
    render_lines,
)
from mapping_resolution_tui.state import ValidationState
from tests.conftest import _build_frame_11_state, make_pyte_screen
from tests.fixtures.storyboard import make_config, make_mappings

# _build_frame_11_state arms the flash at now=0.0, so the burst deadline is here:
DEADLINE = 0.0 + _BURST_DURATION


# ── phase derivation ─────────────────────────────────────────────────────────

def test_phase_is_burst_before_the_deadline():
    state = _build_frame_11_state()
    assert _max_length_phase(state.edit, state.config, DEADLINE - 0.01) is _FlashPhase.BURST


def test_phase_is_held_at_and_after_the_deadline():
    state = _build_frame_11_state()
    assert _max_length_phase(state.edit, state.config, DEADLINE) is _FlashPhase.HELD
    assert _max_length_phase(state.edit, state.config, DEADLINE + 5.0) is _FlashPhase.HELD


def test_phase_is_held_when_deadline_cleared_but_still_invalid_at_max():
    # A stale/absent deadline must never resurrect the burst; while the buffer is
    # still INVALID at the cap the icon holds in the ordinary style (spec §2.1).
    state = _build_frame_11_state()
    edit = replace(state.edit, max_length_flash_until=None)
    assert _max_length_phase(edit, state.config, 0.0) is _FlashPhase.HELD


def test_phase_is_none_when_buffer_below_cap():
    state = _build_frame_11_state()
    edit = replace(
        state.edit,
        buffer="AAPL",
        max_length_flash_until=None,
        validation=ValidationState(status="VALID", icon="✓", error_message=None),
    )
    assert _max_length_phase(edit, state.config, 0.0) is _FlashPhase.NONE


def test_phase_is_none_without_an_edit():
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    assert _max_length_phase(state.edit, state.config, 0.0) is _FlashPhase.NONE


# ── burst vs held rendering (reverse-video is an attribute, not geometry) ─────

def _screen(now):
    return make_pyte_screen(render_lines(_build_frame_11_state(), now=now))


def test_capped_icon_renders_reverse_video_during_burst():
    screen = _screen(DEADLINE - 0.01)
    assert screen.display[4][32] == "✗"  # capped icon column (col 33, spec §6.3)
    assert screen.buffer[4][32].reverse is True


def test_capped_icon_renders_plain_when_held():
    screen = _screen(DEADLINE + 5.0)
    assert screen.display[4][32] == "✗"
    assert screen.buffer[4][32].reverse is False


def test_footer_error_renders_reverse_video_during_burst():
    screen = _screen(DEADLINE - 0.01)
    footer = screen.display[10]
    assert "Error: 24 chars max" in footer
    start = footer.index("Error:")
    message = "Error: 24 chars max"
    assert all(
        screen.buffer[10][start + k].reverse for k in range(len(message))
    )


def test_footer_error_renders_plain_when_held():
    screen = _screen(DEADLINE + 5.0)
    footer = screen.display[10]
    start = footer.index("Error:")
    assert screen.buffer[10][start].reverse is False
