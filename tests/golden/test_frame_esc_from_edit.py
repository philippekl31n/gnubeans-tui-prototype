from pathlib import Path

def test_frame_esc_from_edit_matches_snapshot(frame_esc_from_edit_screen, assert_snapshot):
    assert_snapshot(frame_esc_from_edit_screen, Path(__file__).parent / "snapshots" / "frame_esc_from_edit.txt")
