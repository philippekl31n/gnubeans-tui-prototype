from pathlib import Path

def test_frame_11_matches_snapshot(frame_11_screen, assert_snapshot):
    assert_snapshot(frame_11_screen, Path(__file__).parent / "snapshots" / "frame_11.txt")
