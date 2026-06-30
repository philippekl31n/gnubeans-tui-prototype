from pathlib import Path

def test_frame_5_matches_snapshot(frame_5_screen, assert_snapshot):
    assert_snapshot(frame_5_screen, Path(__file__).parent / "snapshots" / "frame_5.txt")
