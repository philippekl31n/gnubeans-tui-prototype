"""
TASK-008 — golden render test for a valid submit that leaves collisions (spec §9 / FR16).

Over the fresh dataset (the AT-T collision on ordinals 2/3 still stands) the
reviewer edits ordinal 1 and submits ``APPL``. The commit writes ``APPL`` to the
mapping target literally, but the AT-T collision remains unresolved, so
``select_unresolved_collision_count`` stays positive and the app returns to
``BROWSING`` rather than entering the accept confirmation. The rendered frame
recomputes the collision markers from the committed mappings: ordinal 1 now
displays ``APPL`` with no marker, while ordinals 2/3 stay flagged. Geometry uses
pyte ``screen.display``.
"""
from pathlib import Path

import pytest


@pytest.fixture
def display(frame_submit_no_resolution_screen):
    return frame_submit_no_resolution_screen.display


# ── returns to browsing (not confirming) ─────────────────────────────────────

def test_frame_is_browsing_with_the_full_body(frame_submit_no_resolution_lines):
    # header, prompt, blank, table header, 9 body rows, blank separator, footer.
    assert len(frame_submit_no_resolution_lines) == 15


def test_prompt_is_the_browsing_filter_ghost(display):
    # Back in BROWSING with an empty filter and collisions present, the prompt
    # shows the "Tab to view collisions" ghost — never an editing prompt.
    assert "Tab to view collisions" in display[1]
    assert "Editing mapping" not in display[1]


def test_footer_is_the_browsing_edit_footer(display):
    footer = display[14]
    assert "edit selected" in footer
    assert "submit" not in footer  # not the editing submit affordance
    assert "cancel" not in footer


# ── the edited row's target value is updated ─────────────────────────────────

def test_edited_row_shows_the_committed_value(display):
    row = display[4]
    assert row.startswith("▸")          # selection stays on the edited row (FR16)
    assert row.split()[1] == "1"
    assert row.split()[2] == "APPL"     # committed literal, was APPLE by default
    assert row[6] == " "                # ordinal 1 carries no collision marker


# ── collision indicators recalculated: the AT-T pair stays flagged ───────────

def test_header_still_reports_the_remaining_collision(display):
    assert "1 unresolved collision" in display[0]


def test_at_t_rows_keep_their_collision_markers(display):
    assert display[5].split()[0] == "2"
    assert display[5][6] == "!"
    assert display[6].split()[0] == "3"
    assert display[6][6] == "!"


# ── snapshot ─────────────────────────────────────────────────────────────────

def test_frame_submit_no_resolution_matches_snapshot(
    frame_submit_no_resolution_screen, assert_snapshot
):
    assert_snapshot(
        frame_submit_no_resolution_screen,
        Path(__file__).parent / "snapshots" / "frame_submit_no_resolution.txt",
    )
