"""
Story 1.5 — unit tests for initial review state.
These tests must FAIL before production code is added.
"""


def _make_state(frame_height: int = 15):
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    return make_initial_state(make_config(), make_mappings(), frame_height=frame_height)


# ── AC1: root state fields ────────────────────────────────────────────────────

def test_initial_state_is_browsing_mode():
    from mapping_resolution_tui.state import Mode
    state = _make_state()
    assert state.mode == Mode.BROWSING


def test_initial_state_filter_is_empty():
    state = _make_state()
    assert state.filter.text == ""
    assert state.filter.collision_only is False
    assert state.filter.cursor == 0
    assert state.filter.raw == ""


def test_initial_state_selected_ordinal_is_1_scroll_offset_is_0():
    state = _make_state()
    assert state.selection.selected_ordinal == 1
    assert state.selection.scroll_offset == 0


def test_initial_state_result_is_running():
    state = _make_state()
    assert state.result.status == "RUNNING"


def test_initial_state_edit_is_none():
    state = _make_state()
    assert state.edit is None


# ── AC2: visible rows in 15-row terminal ─────────────────────────────────────

def test_initial_visible_rows_contains_all_11_mappings():
    from mapping_resolution_tui.selectors import select_visible_rows
    state = _make_state()
    assert len(select_visible_rows(state)) == 11


def test_initial_body_capacity_for_15_row_frame_is_9():
    from mapping_resolution_tui.selectors import select_body_capacity
    assert select_body_capacity(15) == 9


def test_initial_displayed_rows_cover_ordinals_1_through_9():
    from mapping_resolution_tui.selectors import select_visible_rows, select_body_capacity
    state = _make_state()
    visible = select_visible_rows(state)
    capacity = select_body_capacity(state.terminal.height)
    shown = visible[state.selection.scroll_offset : state.selection.scroll_offset + capacity]
    assert len(shown) == 9
    assert {m.ordinal for m in shown} == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_initial_display_first_row_is_ordinal_1():
    from mapping_resolution_tui.selectors import select_visible_rows
    state = _make_state()
    assert select_visible_rows(state)[0].ordinal == 1


# ── AC3: collision state ──────────────────────────────────────────────────────

def test_initial_unresolved_collision_count_is_1():
    from mapping_resolution_tui.selectors import select_unresolved_collision_count
    state = _make_state()
    assert select_unresolved_collision_count(state) == 1


def test_initial_ordinals_2_and_3_are_marked_unresolved():
    from mapping_resolution_tui.selectors import select_row_collision_metadata
    state = _make_state()
    assert select_row_collision_metadata(state, 2).is_unresolved is True
    assert select_row_collision_metadata(state, 3).is_unresolved is True


def test_initial_ordinal_1_is_not_unresolved():
    from mapping_resolution_tui.selectors import select_row_collision_metadata
    state = _make_state()
    assert select_row_collision_metadata(state, 1).is_unresolved is False


# ── AC4: prompt and footer text ───────────────────────────────────────────────

def test_initial_prompt_communicates_tab_to_view_collisions():
    from mapping_resolution_tui.selectors import select_filter_prompt, select_unresolved_collision_count
    state = _make_state()
    count = select_unresolved_collision_count(state)
    assert select_filter_prompt(state, count).collision_hint_visible is True


def test_initial_footer_communicates_page_movement_and_edit_selected():
    from mapping_resolution_tui.selectors import select_footer_content
    from mapping_resolution_tui.state import FooterHint
    state = _make_state()
    content = select_footer_content(state)
    assert FooterHint.PAGE_SCROLL in content.hints
    assert FooterHint.EDIT_SELECTED in content.hints
