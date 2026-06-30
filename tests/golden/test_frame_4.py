from pathlib import Path

def test_frame_4_matches_snapshot(frame_4_screen, assert_snapshot):
    assert_snapshot(frame_4_screen, Path(__file__).parent / "snapshots" / "frame_4.txt")
