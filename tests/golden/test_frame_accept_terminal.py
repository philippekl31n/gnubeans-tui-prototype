from pathlib import Path

def test_frame_accept_terminal_matches_snapshot(frame_accept_terminal_screen, assert_snapshot):
    assert_snapshot(frame_accept_terminal_screen, Path(__file__).parent / "snapshots" / "frame_accept_terminal.txt")

def test_frame_accept_terminal_lines(frame_accept_terminal_screen):
    display = frame_accept_terminal_screen.display
    # Only 2 lines should be visible because everything below is cleared
    # wait, pyte Screen has `display` which returns exactly the number of lines. But our renderer returns 2 lines.
    assert "11 commodities created." in display[0]
    assert "❯" in display[1]
    assert len(display) == 2
