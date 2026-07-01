from pathlib import Path

def test_frame_12a_matches_snapshot(frame_12a_screen, assert_snapshot):
    assert_snapshot(frame_12a_screen, Path(__file__).parent / "snapshots" / "frame_12a.txt")
