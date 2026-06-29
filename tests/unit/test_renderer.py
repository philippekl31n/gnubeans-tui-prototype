"""
Unit tests for the variable-width ordinal grid (TASK-002, spec §6.3).

The ordinal column is right-aligned to a width `W = len(str(total))` — the digit
count of the mapping count — with its left edge anchored at column 3 (1-based).
Every later column (the `#` heading, collision marker, token, source) follows
the ordinal at a fixed gap, so a wider ordinal shifts them all right together:

    #   heading  -> 1-based column 2 + W   (0-based 1 + W), over the units digit
    token start  -> 1-based column 7 + W   (0-based 6 + W)

These tests assert the grid generalises across the W = 1 / 2 / 3 regimes rather
than being pinned to the 11-row (W = 2) storyboard dataset.
"""

import pytest

from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from tests.fixtures.storyboard import make_config, _canonical_mappings


def _state_with(total):
    """Initial state holding exactly ``total`` mappings (content irrelevant here)."""
    pool = _canonical_mappings()
    mappings = [pool[i % len(pool)] for i in range(total)]
    # A tall frame so every regime renders without scrolling affecting line 3.
    return make_initial_state(make_config(), mappings, frame_height=max(15, total + 6))


def _table_header(state):
    return strip_ansi(render_lines(state)[3])


def _first_body_row(state):
    return strip_ansi(render_lines(state)[4])


@pytest.mark.parametrize(
    "total, hash_col, token_col",
    [
        (9, 2, 7),    # W = 1
        (11, 3, 8),   # W = 2 (storyboard)
        (100, 4, 9),  # W = 3
    ],
)
def test_hash_and_token_columns_track_ordinal_width(total, hash_col, token_col):
    label = make_config().target_column_label
    header = _table_header(_state_with(total))
    assert header.index("#") == hash_col
    assert header.index(label) == token_col


@pytest.mark.parametrize(
    "total, width",
    [(9, 1), (11, 2), (100, 3)],
)
def test_ordinal_is_right_aligned_within_the_variable_width_field(total, width):
    # Ordinal 1 is the first body row; its digit sits at the field's right edge,
    # 1-based column (2 + W) i.e. 0-based (1 + W), left-padded within the field.
    row = _first_body_row(_state_with(total))
    field = row[2 : 2 + width]
    assert field == "1".rjust(width)
