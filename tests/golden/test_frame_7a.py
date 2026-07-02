from pathlib import Path

def test_frame_7a_matches_snapshot(frame_7a_screen, assert_snapshot):
    assert_snapshot(frame_7a_screen, Path(__file__).parent / "snapshots" / "frame_7a.txt")

def test_frame_7a_footer(frame_7a_screen):
    footer = frame_7a_screen.display[-1]
    assert "↵ edit mappings" in footer
    assert "↵ submit" not in footer

def test_frame_7a_prompt(frame_7a_screen):
    prompt = frame_7a_screen.display[1]
    assert "Accept all? [y/N]" in prompt or "Accept all?" in prompt  # Adjust based on the actual text with formatting
