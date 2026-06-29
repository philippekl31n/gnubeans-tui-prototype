from pathlib import Path
import pytest

@pytest.fixture
def display(frame_13_screen):
    return frame_13_screen.display

def test_frame_is_exactly_7_lines_ending_at_footer(frame_13_lines):
    assert len(frame_13_lines) == 7

def test_frame_ends_at_footer_with_no_trailing_padding(display):
    footer_idx = 6
    assert "no matching rows" in display[footer_idx]
    
    for i in range(footer_idx + 1, len(display)):
        assert display[i].strip() == ""

def test_frame_13_matches_snapshot(frame_13_screen, assert_snapshot):
    assert_snapshot(frame_13_screen, Path(__file__).parent / "snapshots" / "frame_13.txt")
