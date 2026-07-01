"""
Unit tests for EDITING-body row allocation against terminal capacity (spec §8.2).

``select_body_rows`` (the plain scroll window used in BROWSING) does not know
that the expanded edit block for the selected mapping can span more than one
line, so using it unmodified while EDITING lets the block's extra source rows
push the frame past ``select_body_capacity(height)`` lines. The edited block
must stay anchored (never scrolled off); whatever capacity is left over after
its rows fills with following context rows first, then preceding rows
(closest first).
"""

from dataclasses import replace

import pytest

from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from mapping_resolution_tui.state import (
    EditState,
    FocusRegion,
    Mode,
    Source,
    ValidationState,
)
from tests.fixtures.storyboard import make_config, _canonical_mappings


def _editing_state(*, frame_height, num_sources, target_index, total=11):
    """Initial state with ``total`` mappings, editing the mapping at position
    ``target_index`` (0-based, in the sorted+ordinal-assigned ``state.mappings``
    order) after widening its sources to ``num_sources`` entries.
    """
    config = make_config()
    pool = _canonical_mappings()
    mappings = [pool[i % len(pool)] for i in range(total)]
    state = make_initial_state(config, mappings, frame_height=frame_height)

    wide_sources = [
        Source(label=f"s{i}", original_value=f"v{i}", sanitized_value=None)
        for i in range(num_sources)
    ]
    widened = [
        replace(m, sources=wide_sources, default_source_label="s0")
        if i == target_index
        else m
        for i, m in enumerate(state.mappings)
    ]
    state = replace(state, mappings=widened)

    edited_ordinal = state.mappings[target_index].ordinal
    state = replace(
        state,
        selection=replace(state.selection, selected_ordinal=edited_ordinal),
        mode=Mode.EDITING,
        edit=EditState(
            mapping_ordinal=edited_ordinal,
            buffer="",
            cursor=0,
            focus_region=FocusRegion.TOKEN_INPUT,
            source_pointer_index=None,
            source_entry_buffer=None,
            validation=ValidationState(status="EMPTY", icon=None, error_message=None),
            max_length_flash_until=None,
        ),
    )
    return state


def _body_lines(lines):
    # [header, prompt, "", table_header, *body, "", footer]
    return lines[4:-2]


def _row_ordinal(line, width):
    return int(strip_ansi(line)[2 : 2 + width])


def test_wide_anchor_block_alone_exceeds_capacity_suppresses_all_context():
    # capacity = 10 - 6 = 4; a 5-source block alone already exceeds it, so no
    # before/after context row should be squeezed in on top of the overflow.
    state = _editing_state(frame_height=10, num_sources=5, target_index=5)
    body = _body_lines(render_lines(state))
    assert len(body) == 5  # 1 token row + 4 extra source rows, no context rows


def test_context_capacity_prefers_following_rows_first():
    # capacity = 13 - 6 = 7; anchor block is 3 rows (indices 0-2 of body), leaving
    # context_capacity=4. 5 rows follow and 5 rows precede the anchor at position
    # 5 of 11, so all 4 context slots should go to "after" rows, none to "before".
    state = _editing_state(frame_height=13, num_sources=3, target_index=5)
    W = len(str(11))
    body = _body_lines(render_lines(state))
    assert len(body) == 7  # exactly packed to capacity, no overflow

    anchor_ordinal = state.edit.mapping_ordinal
    # The anchor's own block occupies body[0:3] (1 token row + 2 source rows);
    # context rows start right after it.
    following = [_row_ordinal(line, W) for line in body[3:7]]
    visible_ordinals = [m.ordinal for m in state.mappings]
    anchor_index = visible_ordinals.index(anchor_ordinal)
    expected_following = visible_ordinals[anchor_index + 1 : anchor_index + 5]
    assert following == expected_following


def test_context_capacity_spills_to_preceding_rows_when_following_run_out():
    # Anchor near the end of the list (position 9 of 11): only 1 row follows,
    # so of the 4 context slots, 1 goes "after" and the remaining 3 spill to
    # the 3 closest preceding rows.
    state = _editing_state(frame_height=13, num_sources=3, target_index=9)
    W = len(str(11))
    body = _body_lines(render_lines(state))
    assert len(body) == 7

    anchor_ordinal = state.edit.mapping_ordinal
    visible_ordinals = [m.ordinal for m in state.mappings]
    anchor_index = visible_ordinals.index(anchor_ordinal)

    preceding = [_row_ordinal(line, W) for line in body[0:3]]
    expected_preceding = visible_ordinals[anchor_index - 3 : anchor_index]
    assert preceding == expected_preceding

    trailing = [_row_ordinal(line, W) for line in body[6:7]]
    expected_trailing = visible_ordinals[anchor_index + 1 : anchor_index + 2]
    assert trailing == expected_trailing


def test_small_anchor_block_with_ample_context_never_exceeds_capacity():
    # Sanity check across every anchor position: total rendered body lines
    # never exceed capacity, and the mapping's own block is never dropped.
    for target_index in range(11):
        state = _editing_state(frame_height=13, num_sources=2, target_index=target_index)
        body = _body_lines(render_lines(state))
        assert len(body) <= 7
        assert len(body) >= 2  # the anchor's own 2-source block is always shown
