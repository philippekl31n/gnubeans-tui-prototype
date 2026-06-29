from pathlib import Path
import pytest

@pytest.fixture
def display(frame_3_screen):
    return frame_3_screen.display

def test_frame_is_exactly_7_lines_ending_at_footer(frame_3_lines):
    assert len(frame_3_lines) == 7

def test_frame_ends_at_footer_with_no_trailing_padding(display):
    footer_idx = 6
    assert "clear filter" in display[footer_idx]
    
    for i in range(footer_idx + 1, len(display)):
        assert display[i].strip() == ""

def test_frame_3_matches_snapshot(frame_3_screen, assert_snapshot):
    assert_snapshot(frame_3_screen, Path(__file__).parent / "snapshots" / "frame_3.txt")
