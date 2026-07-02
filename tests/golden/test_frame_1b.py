from pathlib import Path

def test_frame_1b_matches_snapshot(frame_1b_screen, assert_snapshot):
    assert_snapshot(frame_1b_screen, Path(__file__).parent / "snapshots" / "frame_1b.txt")
