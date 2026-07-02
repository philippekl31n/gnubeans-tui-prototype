from pathlib import Path

def test_frame_14_matches_snapshot(frame_14_screen, assert_snapshot):
    assert_snapshot(frame_14_screen, Path(__file__).parent / "snapshots" / "frame_14.txt")

def test_frame_14_matches_frame_6(frame_14_screen, frame_6_screen):
    assert frame_14_screen.display == frame_6_screen.display
