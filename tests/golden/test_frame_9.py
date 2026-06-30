from pathlib import Path

def test_frame_9_matches_snapshot(frame_9_screen, assert_snapshot):
    assert_snapshot(frame_9_screen, Path(__file__).parent / "snapshots" / "frame_9.txt")
