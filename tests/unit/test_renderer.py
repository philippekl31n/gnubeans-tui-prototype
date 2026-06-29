"""
Unit tests for the variable-width table grid (TASK-002, spec §6.3).

Two parameters drive the grid: `W = len(str(total))` (ordinal width) and
`M = config.targetPolicy.maxTokenLength` (token field width). Every column after
the ordinal follows it at a fixed gap, and every column after the token follows
it at a fixed gap, so (1-based):

    #   heading   -> column 2 + W   (0-based 1 + W), over the ordinal units digit
    token start   -> column 6 + W   (0-based 5 + W)
    source start  -> column 9 + W + M (0-based 8 + W + M)

A body row is `{cursor}{1sp}{ordinal:>W}{2sp}{!|sp}{token:M}{3sp}{source}`. These
tests assert the grid generalises across the W = 1/2/3 regimes and tracks M (and
that an over-long target label is truncated into the M-wide token field).
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from tests.fixtures.storyboard import make_config, _canonical_mappings


def _state_with(total, M=24):
    """Initial state with ``total`` mappings and token field width ``M``."""
    config = make_config()
    if M != config.target_policy.max_token_length:
        config = replace(
            config, target_policy=replace(config.target_policy, max_token_length=M)
        )
    pool = _canonical_mappings()
    mappings = [pool[i % len(pool)] for i in range(total)]
    # A tall frame so every regime renders without scrolling affecting line 3.
    return make_initial_state(config, mappings, frame_height=max(15, total + 6))


def _table_header(state):
    return strip_ansi(render_lines(state)[3])


def _first_body_row(state):
    return strip_ansi(render_lines(state)[4])


# ── ordinal width (W) drives the # heading and token columns ──────────────────

@pytest.mark.parametrize(
    "total, hash_col, token_col",
    [
        (9, 2, 6),    # W = 1
        (11, 3, 7),   # W = 2 (storyboard)
        (100, 4, 8),  # W = 3
    ],
)
def test_hash_and_token_columns_track_ordinal_width(total, hash_col, token_col):
    label = make_config().target_column_label  # 15 chars < M=24, so not truncated
    header = _table_header(_state_with(total))
    assert header.index("#") == hash_col
    assert header.index(label) == token_col


@pytest.mark.parametrize("total, width", [(9, 1), (11, 2), (100, 3)])
def test_ordinal_is_right_aligned_within_the_variable_width_field(total, width):
    # Ordinal 1 is the first body row; its digit sits at the field's right edge,
    # 0-based column (1 + W), left-padded within the field.
    row = _first_body_row(_state_with(total))
    field = row[2 : 2 + width]
    assert field == "1".rjust(width)


# ── token field width (M) drives the source column ───────────────────────────

@pytest.mark.parametrize("M", [24, 10])
def test_source_column_tracks_max_token_length(M):
    # The token field is M wide and the source begins three columns after it, at
    # 0-based 8 + W + M, in BOTH the header label and the body value.
    total, W = 11, 2
    state = _state_with(total, M)
    header = _table_header(state)
    body = _first_body_row(state)
    source_col = 8 + W + M

    assert header.index(make_config().source_column_label) == source_col
    # Body: the M-wide token field, then exactly three spaces, then the source.
    assert body[5 + W + M : source_col] == "   "
    assert body[source_col] != " "


def test_target_label_is_truncated_into_the_token_field_when_longer_than_M():
    # With M (10) smaller than the 15-char "Beancount Token" label, the header
    # label is truncated with a trailing ellipsis into the M-wide token field so
    # the source label still aligns with the body at 9+W+M.
    total, W, M = 11, 2, 10
    header = _table_header(_state_with(total, M))
    label = make_config().target_column_label
    assert len(label) > M
    assert label not in header          # the full label does not fit
    assert "…" in header                # truncated with a trailing ellipsis
    token_field = header[5 + W : 5 + W + M]
    assert len(token_field) == M and token_field.rstrip().endswith("…")
    assert header.index(make_config().source_column_label) == 8 + W + M
