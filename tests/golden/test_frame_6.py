from pathlib import Path

def test_frame_6_matches_snapshot(frame_6_screen, assert_snapshot):
    assert_snapshot(frame_6_screen, Path(__file__).parent / "snapshots" / "frame_6.txt")

def test_frame_6_footer(frame_6_screen):
    footer = frame_6_screen.display[-1]
    assert "↵ edit mappings" in footer
    assert "↵ submit" not in footer
