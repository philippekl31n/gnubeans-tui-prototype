from pathlib import Path

def test_frame_10_matches_snapshot(frame_10_screen, assert_snapshot):
    assert_snapshot(frame_10_screen, Path(__file__).parent / "snapshots" / "frame_10.txt")
