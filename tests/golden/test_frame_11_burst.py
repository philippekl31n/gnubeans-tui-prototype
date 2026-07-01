from pathlib import Path

def test_frame_11_burst_matches_snapshot(frame_11_burst_screen, assert_snapshot):
    assert_snapshot(frame_11_burst_screen, Path(__file__).parent / "snapshots" / "frame_11_burst.txt")
