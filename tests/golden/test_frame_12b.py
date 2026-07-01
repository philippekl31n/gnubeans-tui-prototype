from pathlib import Path

def test_frame_12b_matches_snapshot(frame_12b_screen, assert_snapshot):
    assert_snapshot(frame_12b_screen, Path(__file__).parent / "snapshots" / "frame_12b.txt")
