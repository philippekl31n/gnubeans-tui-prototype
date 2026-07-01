"""
TASK-006 — golden render test for frame 11 (max-length cap and flash, FR20).

After filling the buffer to the 24-column cap, a further character is discarded:
the buffer stays at 24 characters, the reverse-video cursor sits at the token
boundary, the ``✗`` icon renders at the capped icon column (breaking the
two-columns-past-the-cursor rule, §6.3), and the transient max-length error
``24 chars max`` renders immediately in the footer (spec §7.5).
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_11_screen):
    return frame_11_screen.display


# ── geometry ──────────────────────────────────────────────────────────────────

def test_frame_is_eleven_lines_ending_at_footer(frame_11_lines):
    assert len(frame_11_lines) == 11


# ── 24-char buffer pinned at the cap ─────────────────────────────────────────

def test_buffer_is_capped_at_twenty_four_characters(display):
    # Token field is M=24 wide (cols 8..31, 1-based; indices 7..30).
    assert display[4][7:31] == "44PL56789012345678901234"


def test_reverse_video_cursor_at_the_token_boundary(frame_11_screen):
    # Cursor at offset 24 -> reverse-video space at col 32 (index 31).
    assert frame_11_screen.display[4][31] == " "
    assert frame_11_screen.buffer[4][31].reverse is True


def test_invalid_icon_at_the_capped_column(display):
    # The icon caps at the token-field end + 2 = col 33 (index 32), one column
    # past the cursor rather than two (spec §6.3 / storyboard frame 11).
    assert display[4][32] == "✗"


def test_max_length_flash_error_renders_immediately(display):
    footer = display[10]
    assert "Error: 24 chars max" in footer
    assert "submit" not in footer


def test_flash_until_is_set_on_the_over_limit_discard():
    from tests.conftest import _build_frame_11_state

    state = _build_frame_11_state()
    assert state.edit.max_length_flash_until is not None
    assert len(state.edit.buffer) == 24


# ── a further over-limit character is still discarded ─────────────────────────

def test_additional_over_limit_character_is_discarded():
    from tests.conftest import _build_frame_11_state
    from mapping_resolution_tui.actions import InsertChar
    from mapping_resolution_tui.reducer import reduce

    from mapping_resolution_tui.reducer import _BURST_DURATION

    state = _build_frame_11_state()
    after = reduce(state, InsertChar("9"), now=5.0)
    assert after.edit.buffer == state.edit.buffer  # unchanged, char discarded
    assert after.edit.max_length_flash_until == 5.0 + _BURST_DURATION


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_11_matches_snapshot(frame_11_screen, assert_snapshot):
    assert_snapshot(frame_11_screen, Path(__file__).parent / "snapshots" / "frame_11.txt")
