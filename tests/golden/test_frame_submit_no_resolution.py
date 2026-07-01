from pathlib import Path

def test_frame_submit_no_resolution_matches_snapshot(frame_submit_no_resolution_screen, assert_snapshot):
    assert_snapshot(frame_submit_no_resolution_screen, Path(__file__).parent / "snapshots" / "frame_submit_no_resolution.txt")
