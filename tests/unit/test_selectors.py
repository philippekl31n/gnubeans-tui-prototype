import pytest

from mapping_resolution_tui.state import AppConfig, Mapping, Source


def _story_1_4_mappings() -> list[Mapping]:
    return [
        Mapping(
            ordinal=1,
            sources=[
                Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
                Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
            ],
            default_source_label="user_symbol",
            target_value=None,
        ),
        Mapping(
            ordinal=2,
            sources=[
                Source(label="cmdty_id", original_value="AT&T", sanitized_value="AT-T"),
            ],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            ordinal=3,
            sources=[
                Source(label="cmdty_id", original_value="AT-T", sanitized_value=None),
            ],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            ordinal=4,
            sources=[
                Source(label="cmdty_id", original_value="100-F", sanitized_value="C100-F"),
            ],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            ordinal=5,
            sources=[Source(label="cmdty_id", original_value="MSFT", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
    ]


def test_effective_source_value_prefers_sanitized_value_without_mutating_source():
    from mapping_resolution_tui.selectors import select_source_effective_value

    source = Source(
        label="cmdty_id",
        original_value="100-F",
        sanitized_value="C100-F",
    )

    assert select_source_effective_value(source) == "C100-F"
    assert source.original_value == "100-F"
    assert source.sanitized_value == "C100-F"


def test_effective_source_value_falls_back_to_original_value():
    from mapping_resolution_tui.selectors import select_source_effective_value

    source = Source(
        label="cmdty_id",
        original_value="AAPL",
        sanitized_value=None,
    )

    assert select_source_effective_value(source) == "AAPL"


def test_source_display_shows_label_and_arrow_when_sanitized():
    from mapping_resolution_tui.selectors import select_source_display

    source = Source(
        label="cmdty_id",
        original_value="100-F",
        sanitized_value="C100-F",
    )

    assert select_source_display(source) == 'cmdty_id: "100-F" → "C100-F"'


def test_source_display_shows_label_and_single_value_when_unsanitized():
    from mapping_resolution_tui.selectors import select_source_display

    source = Source(
        label="cmdty_id",
        original_value="GOOGL",
        sanitized_value=None,
    )

    assert select_source_display(source) == 'cmdty_id: "GOOGL"'


def test_source_display_marks_missing_value_as_not_set():
    from mapping_resolution_tui.selectors import select_source_display

    source = Source(
        label="cmdty_id",
        original_value=None,
        sanitized_value=None,
    )

    assert select_source_display(source) == "cmdty_id: (not set)"


def test_default_source_and_default_source_value_are_derived_from_label():
    from mapping_resolution_tui.selectors import (
        select_default_source,
        select_default_source_value,
    )

    mapping = Mapping(
        ordinal=1,
        sources=[
            Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
            Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
        ],
        default_source_label="user_symbol",
        target_value=None,
    )

    default_source = select_default_source(mapping)

    assert default_source == mapping.sources[1]
    assert select_default_source_value(mapping) == "APPLE"


def test_current_target_value_uses_default_when_target_is_missing():
    from mapping_resolution_tui.selectors import select_current_target_value

    mapping = Mapping(
        ordinal=4,
        sources=[Source(label="cmdty_id", original_value="100-F", sanitized_value="C100-F")],
        default_source_label="cmdty_id",
        target_value=None,
    )

    assert select_current_target_value(mapping) == "C100-F"


def test_current_target_value_preserves_literal_target_even_when_equal_to_default():
    from mapping_resolution_tui.selectors import select_current_target_value

    mapping = Mapping(
        ordinal=1,
        sources=[Source(label="cmdty_id", original_value="AAPL", sanitized_value=None)],
        default_source_label="cmdty_id",
        target_value="AAPL",
    )

    assert select_current_target_value(mapping) == "AAPL"
    assert mapping.target_value == "AAPL"


def test_active_sources_excludes_missing_effective_values_and_preserves_order():
    from mapping_resolution_tui.selectors import select_active_sources

    mapping = Mapping(
        ordinal=1,
        sources=[
            Source(label="cmdty_id", original_value=None, sanitized_value=None),
            Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
            Source(label="isin", original_value="US0378331005", sanitized_value=None),
        ],
        default_source_label="user_symbol",
        target_value=None,
    )

    assert select_active_sources(mapping) == [mapping.sources[1], mapping.sources[2]]


@pytest.mark.parametrize(
    ("config", "mapping", "expected_message"),
    [
        (
            AppConfig(
                entity_name_singular="commodity",
                entity_name_plural="commodities",
                mapping_noun_singular="mapping",
                mapping_noun_plural="mappings",
                target_column_label="Beancount Token",
                source_column_label="GnuCash Source",
                accept_prompt="Accept all?",
                exit_prompt="Skip adding commodities?",
                created_message=lambda count: f"{count} commodities created.",
                source_labels=["cmdty_id"],
                target_policy=None,
            ),
            Mapping(
                ordinal=1,
                sources=[
                    Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
                    Source(label="cmdty_id", original_value="APPLE", sanitized_value=None),
                ],
                default_source_label="cmdty_id",
                target_value=None,
            ),
            "duplicate source label",
        ),
        (
            AppConfig(
                entity_name_singular="commodity",
                entity_name_plural="commodities",
                mapping_noun_singular="mapping",
                mapping_noun_plural="mappings",
                target_column_label="Beancount Token",
                source_column_label="GnuCash Source",
                accept_prompt="Accept all?",
                exit_prompt="Skip adding commodities?",
                created_message=lambda count: f"{count} commodities created.",
                source_labels=["cmdty_id"],
                target_policy=None,
            ),
            Mapping(
                ordinal=1,
                sources=[Source(label="unknown", original_value="AAPL", sanitized_value=None)],
                default_source_label="unknown",
                target_value=None,
            ),
            "unknown source label",
        ),
        (
            AppConfig(
                entity_name_singular="commodity",
                entity_name_plural="commodities",
                mapping_noun_singular="mapping",
                mapping_noun_plural="mappings",
                target_column_label="Beancount Token",
                source_column_label="GnuCash Source",
                accept_prompt="Accept all?",
                exit_prompt="Skip adding commodities?",
                created_message=lambda count: f"{count} commodities created.",
                source_labels=["cmdty_id"],
                target_policy=None,
            ),
            Mapping(
                ordinal=1,
                sources=[Source(label="cmdty_id", original_value="AAPL", sanitized_value=None)],
                default_source_label="unknown",
                target_value=None,
            ),
            "unknown default source label",
        ),
        (
            AppConfig(
                entity_name_singular="commodity",
                entity_name_plural="commodities",
                mapping_noun_singular="mapping",
                mapping_noun_plural="mappings",
                target_column_label="Beancount Token",
                source_column_label="GnuCash Source",
                accept_prompt="Accept all?",
                exit_prompt="Skip adding commodities?",
                created_message=lambda count: f"{count} commodities created.",
                source_labels=["cmdty_id"],
                target_policy=None,
            ),
            Mapping(
                ordinal=1,
                sources=[Source(label="cmdty_id", original_value=None, sanitized_value=None)],
                default_source_label="cmdty_id",
                target_value=None,
            ),
            "missing default source value",
        ),
        (
            AppConfig(
                entity_name_singular="commodity",
                entity_name_plural="commodities",
                mapping_noun_singular="mapping",
                mapping_noun_plural="mappings",
                target_column_label="Beancount Token",
                source_column_label="GnuCash Source",
                accept_prompt="Accept all?",
                exit_prompt="Skip adding commodities?",
                created_message=lambda count: f"{count} commodities created.",
                source_labels=["cmdty_id"],
                target_policy=None,
            ),
            Mapping(
                ordinal=1,
                sources=[Source(label="cmdty_id", original_value=None, sanitized_value="AAPL")],
                default_source_label="cmdty_id",
                target_value=None,
            ),
            "sanitized value without original value",
        ),
    ],
)
def test_mapping_invariant_validation_reports_invalid_fixture_data_deterministically(
    config,
    mapping,
    expected_message,
):
    from mapping_resolution_tui.selectors import validate_mapping_invariants

    with pytest.raises(ValueError, match=expected_message):
        validate_mapping_invariants(config, mapping)


def test_initial_display_sort_orders_by_default_value_original_value_then_ordinal():
    from mapping_resolution_tui.selectors import sort_mappings_for_initial_display

    mappings = list(reversed(_story_1_4_mappings()))

    assert [mapping.ordinal for mapping in sort_mappings_for_initial_display(mappings)] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_collision_groups_and_count_detect_initial_at_t_collision():
    from mapping_resolution_tui.selectors import (
        select_collision_groups,
        select_unresolved_collision_count,
    )

    groups = select_collision_groups(_story_1_4_mappings())

    assert groups == (("AT-T", (2, 3)),)
    assert select_unresolved_collision_count(_story_1_4_mappings()) == 1


def test_unresolved_collision_ordinals_include_only_collision_group_members():
    from mapping_resolution_tui.selectors import (
        select_row_collision_metadata,
        select_unresolved_collision_ordinals,
    )

    ordinals = select_unresolved_collision_ordinals(_story_1_4_mappings())

    assert ordinals == frozenset({2, 3})
    assert select_row_collision_metadata(_story_1_4_mappings(), 2).is_unresolved is True
    assert select_row_collision_metadata(_story_1_4_mappings(), 3).is_unresolved is True
    assert select_row_collision_metadata(_story_1_4_mappings(), 1).is_unresolved is False
    assert select_row_collision_metadata(_story_1_4_mappings(), 4).is_unresolved is False
    assert select_row_collision_metadata(_story_1_4_mappings(), 5).is_unresolved is False


def test_initial_display_sort_uses_default_sources_not_literal_target_values():
    from dataclasses import replace

    from mapping_resolution_tui.selectors import sort_mappings_for_initial_display

    mappings = _story_1_4_mappings()
    target_overridden_mappings = [
        replace(mapping, target_value="ZZZ") if mapping.ordinal == 2 else mapping
        for mapping in mappings
    ]

    assert [mapping.ordinal for mapping in sort_mappings_for_initial_display(target_overridden_mappings)] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_collision_selectors_are_repeatable_and_do_not_store_state_on_mappings():
    from mapping_resolution_tui.selectors import (
        select_collision_groups,
        select_unresolved_collision_count,
        select_unresolved_collision_ordinals,
    )

    mappings = _story_1_4_mappings()

    assert select_collision_groups(mappings) == select_collision_groups(mappings)
    assert select_unresolved_collision_count(mappings) == 1
    assert select_unresolved_collision_count(mappings) == 1
    assert select_unresolved_collision_ordinals(mappings) == frozenset({2, 3})
    assert all(not hasattr(mapping, "collision_groups") for mapping in mappings)
    assert all(not hasattr(mapping, "unresolved_collisions") for mapping in mappings)
    assert all(not hasattr(mapping, "unresolved_collision_count") for mapping in mappings)


# ── filter parse / highlight selectors (TASK-002, spec §3.3) ─────────────────


def test_parse_filter_empty():
    from mapping_resolution_tui.selectors import parse_filter

    assert parse_filter("") == (False, "")


def test_parse_filter_leading_bang_is_collision_only():
    from mapping_resolution_tui.selectors import parse_filter

    assert parse_filter("!") == (True, "")
    assert parse_filter("!3") == (True, "3")


def test_parse_filter_non_leading_bang_is_ordinary_text():
    from mapping_resolution_tui.selectors import parse_filter

    assert parse_filter("a!") == (False, "a!")


def test_match_spans_finds_query_in_text():
    # Signature is (text, query); the "1" inside the C100-F token.
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("C100-F", "1") == ((1, 2),)


def test_match_spans_reports_every_non_overlapping_match():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("11", "1") == ((0, 1), (1, 2))


def test_match_spans_is_case_insensitive():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("APPLE", "appl") == ((0, 4),)


def test_match_spans_empty_query_matches_nothing():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("APPLE", "") == ()


def test_ordinal_spans_shift_by_the_right_align_pad():
    # "1" right-justified in width 2 is " 1"; the digit match (0,1) shifts to (1,2).
    from mapping_resolution_tui.selectors import select_ordinal_match_spans

    assert select_ordinal_match_spans(1, "1", 2) == ((1, 2),)


def test_ordinal_spans_two_digit_no_pad():
    from mapping_resolution_tui.selectors import select_ordinal_match_spans

    assert select_ordinal_match_spans(10, "1", 2) == ((0, 1),)
    assert select_ordinal_match_spans(11, "1", 2) == ((0, 1), (1, 2))


def test_ordinal_spans_no_match_or_empty_query():
    from mapping_resolution_tui.selectors import select_ordinal_match_spans

    assert select_ordinal_match_spans(4, "1", 2) == ()
    assert select_ordinal_match_spans(1, "", 2) == ()


# ── edit-mode selectors (TASK-005, spec §7) ──────────────────────────────────


def _editing_state(
    buffer,
    cursor,
    *,
    ordinal=1,
    focus_region=None,
    source_pointer_index=None,
    source_entry_buffer=None,
    validation=None,
):
    """Build an EDITING AppState with an injected EditState for ``ordinal``.

    Follows the recommended pattern: bootstrap a deterministic initial state via
    ``make_initial_state`` (ordinals are assigned after the bootstrap sort, so
    ordinal 1 is always the ``APPLE`` mapping) then ``replace`` an EditState in.
    """
    from dataclasses import replace

    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.state import (
        EditState,
        FocusRegion,
        Mode,
        ValidationState,
    )
    from tests.fixtures.storyboard import make_config, make_mappings

    if focus_region is None:
        focus_region = FocusRegion.TOKEN_INPUT
    if validation is None:
        validation = ValidationState(status="EMPTY", icon=None, error_message=None)

    base = make_initial_state(make_config(), make_mappings(), frame_height=15)
    edit = EditState(
        mapping_ordinal=ordinal,
        buffer=buffer,
        cursor=cursor,
        focus_region=focus_region,
        source_pointer_index=source_pointer_index,
        source_entry_buffer=source_entry_buffer,
        validation=validation,
        max_length_flash_until=None,
    )
    return replace(base, mode=Mode.EDITING, edit=edit)


def _mapping(state, ordinal):
    return next(m for m in state.mappings if m.ordinal == ordinal)


def test_ghost_suffix_empty_buffer_is_full_default_source_value():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="", cursor=0)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == "APPLE"


def test_ghost_suffix_prefix_buffer_returns_remaining_suffix():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="AP", cursor=2)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == "PLE"


def test_ghost_suffix_is_empty_when_buffer_equals_full_default():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="APPLE", cursor=5)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == ""


def test_ghost_suffix_is_empty_when_buffer_is_not_a_prefix():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="AX", cursor=2)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == ""


def test_ghost_suffix_is_empty_when_cursor_not_at_end_of_buffer():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="AP", cursor=1)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == ""


def test_ghost_suffix_is_case_sensitive():
    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="ap", cursor=2)
    mapping = _mapping(state, 1)

    assert select_ghost_suffix(state, mapping) == ""


def test_ghost_suffix_is_empty_when_literal_target_override_exists():
    from dataclasses import replace

    from mapping_resolution_tui.selectors import select_ghost_suffix

    state = _editing_state(buffer="A", cursor=1)
    mapping = replace(_mapping(state, 1), target_value="A")

    # "A" is a prefix of the default "APPLE", but a literal target override
    # suppresses ghost text entirely (FR17, spec §7.1).
    assert select_ghost_suffix(state, mapping) == ""


def test_concrete_value_uses_buffer_when_non_empty():
    from mapping_resolution_tui.selectors import select_concrete_value

    state = _editing_state(buffer="ATT", cursor=3)
    mapping = _mapping(state, 1)

    assert select_concrete_value(state, mapping) == "ATT"


def test_concrete_value_falls_back_to_default_source_value_when_buffer_empty():
    from mapping_resolution_tui.selectors import select_concrete_value

    state = _editing_state(buffer="", cursor=0)
    mapping = _mapping(state, 1)

    assert select_concrete_value(state, mapping) == "APPLE"


def test_concrete_value_empty_buffer_ignores_literal_target_override():
    from dataclasses import replace

    from mapping_resolution_tui.selectors import select_concrete_value

    state = _editing_state(buffer="", cursor=0)
    mapping = replace(_mapping(state, 1), target_value="ZZZ")

    # The fallback is the default source effective value, not target_value:
    # select_concrete_value is buffer-or-default and is the single source of
    # truth (FR22).
    assert select_concrete_value(state, mapping) == "APPLE"


def test_source_pointer_value_is_none_when_index_is_none():
    from mapping_resolution_tui.selectors import select_source_pointer_value

    state = _editing_state(buffer="APPLE", cursor=5, source_pointer_index=None)
    mapping = _mapping(state, 1)

    assert select_source_pointer_value(state, mapping) is None


def test_source_pointer_value_resolves_against_active_sources():
    from mapping_resolution_tui.selectors import select_source_pointer_value

    first = _editing_state(
        buffer="AAPL",
        cursor=4,
        focus_region=None,
        source_pointer_index=0,
    )
    second = _editing_state(
        buffer="APPLE",
        cursor=5,
        source_pointer_index=1,
    )
    mapping = _mapping(first, 1)

    assert select_source_pointer_value(first, mapping) == "AAPL"
    assert select_source_pointer_value(second, mapping) == "APPLE"


def test_source_pointer_value_skips_inactive_sources():
    from dataclasses import replace

    from mapping_resolution_tui.selectors import select_source_pointer_value

    state = _editing_state(buffer="APPLE", cursor=5, source_pointer_index=0)
    # First raw source has no effective value, so index 0 of the active list is
    # the second raw source (delegated to select_active_sources, FR21).
    mapping = replace(
        _mapping(state, 1),
        sources=[
            Source(label="cmdty_id", original_value=None, sanitized_value=None),
            Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
        ],
        default_source_label="user_symbol",
    )

    assert select_source_pointer_value(state, mapping) == "APPLE"


def test_edit_render_row_bundles_token_input_view():
    from mapping_resolution_tui.selectors import EditSourceRow, select_edit_render_row
    from mapping_resolution_tui.state import FocusRegion

    state = _editing_state(buffer="", cursor=0)
    mapping = _mapping(state, 1)

    row = select_edit_render_row(state, mapping)

    assert row.buffer == ""
    assert row.ghost_suffix == "APPLE"
    assert row.cursor == 0
    assert row.focus_region is FocusRegion.TOKEN_INPUT
    assert row.validation_icon is None
    assert row.validation_error is None
    assert row.sources == (
        EditSourceRow(display='cmdty_id: "AAPL"', is_pointer=False),
        EditSourceRow(display='user_symbol: "APPLE"', is_pointer=False),
    )


def test_edit_render_row_marks_pointer_in_source_list():
    from mapping_resolution_tui.selectors import select_edit_render_row
    from mapping_resolution_tui.state import FocusRegion

    state = _editing_state(
        buffer="AAPL",
        cursor=4,
        focus_region=FocusRegion.SOURCE_LIST,
        source_pointer_index=0,
        source_entry_buffer="",
    )
    mapping = _mapping(state, 1)

    row = select_edit_render_row(state, mapping)

    assert row.focus_region is FocusRegion.SOURCE_LIST
    assert row.ghost_suffix == ""
    assert [source.is_pointer for source in row.sources] == [True, False]


def test_edit_render_row_surfaces_policy_validation_result():
    from mapping_resolution_tui.selectors import select_edit_render_row
    from mapping_resolution_tui.state import ValidationState

    state = _editing_state(
        buffer="44PL",
        cursor=4,
        validation=ValidationState(
            status="INVALID", icon="✗", error_message="must start with A-Z"
        ),
    )
    mapping = _mapping(state, 1)

    row = select_edit_render_row(state, mapping)

    assert row.buffer == "44PL"
    assert row.validation_icon == "✗"
    assert row.validation_error == "must start with A-Z"
    assert row.ghost_suffix == ""


# ── live collision recompute for rendering (TASK-006, spec §3.2 / FR8) ────────


def test_render_collision_ordinals_browsing_matches_committed():
    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.selectors import (
        select_render_collision_ordinals,
        select_unresolved_collision_ordinals,
    )
    from tests.fixtures.storyboard import make_config, make_mappings

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)

    assert select_render_collision_ordinals(state) == frozenset({2, 3})
    assert select_render_collision_ordinals(state) == (
        select_unresolved_collision_ordinals(state.mappings)
    )


def test_render_collision_ordinals_substitutes_live_buffer():
    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    # Editing the AT-T collision row (ordinal 3) with buffer "ATT" resolves the
    # collision live: both AT-T markers disappear.
    state = _editing_state(buffer="ATT", cursor=3, ordinal=3)

    assert select_render_collision_ordinals(state) == frozenset()


def test_render_collision_ordinals_empty_buffer_is_treated_as_unresolved():
    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    # An empty buffer is treated as unresolved: no live value is substituted, so
    # ordinal 3 keeps its committed "AT-T" target and the AT-T pair stays flagged
    # (FR8). The empty buffer never "resolves" the collision.
    state = _editing_state(buffer="", cursor=0, ordinal=3)

    assert select_render_collision_ordinals(state) == frozenset({2, 3})


def test_render_collision_ordinals_empty_buffer_keeps_a_literal_target_collision():
    from dataclasses import replace

    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    # Ordinals 2 and 3 both carry a literal target "ZZZ" (differing from their
    # "AT-T" default), so they collide on "ZZZ". Editing ordinal 3 down to an
    # empty buffer must NOT fall back to the default source value (which would
    # split the pair and falsely resolve the collision); the empty buffer stays
    # unresolved and both rows remain flagged (FR8).
    state = _editing_state(buffer="", cursor=0, ordinal=3)
    state = replace(
        state,
        mappings=[
            replace(m, target_value="ZZZ") if m.ordinal in (2, 3) else m
            for m in state.mappings
        ],
    )

    assert select_render_collision_ordinals(state) == frozenset({2, 3})


# ── EDITING footer submit-gating + error (TASK-006, spec §6.6) ───────────────


def test_footer_editing_valid_buffer_offers_submit():
    from mapping_resolution_tui.selectors import select_footer_content
    from mapping_resolution_tui.state import FooterHint, ValidationState

    state = _editing_state(
        buffer="ATT",
        cursor=3,
        validation=ValidationState(status="VALID", icon="✓", error_message=None),
    )

    footer = select_footer_content(state)

    assert footer.hints == (
        FooterHint.TYPE_TO_EDIT,
        FooterHint.SELECT_SOURCE,
        FooterHint.SUBMIT,
        FooterHint.CANCEL,
    )
    assert footer.error is None


def test_footer_editing_empty_buffer_omits_submit():
    from mapping_resolution_tui.selectors import select_footer_content
    from mapping_resolution_tui.state import FooterHint

    state = _editing_state(buffer="", cursor=0)  # default validation is EMPTY

    footer = select_footer_content(state)

    assert footer.hints == (
        FooterHint.TYPE_TO_EDIT,
        FooterHint.SELECT_SOURCE,
        FooterHint.CANCEL,
    )
    assert footer.error is None


def test_footer_editing_invalid_buffer_leads_with_error():
    from mapping_resolution_tui.selectors import select_footer_content
    from mapping_resolution_tui.state import FooterHint, ValidationState

    state = _editing_state(
        buffer="44PL",
        cursor=4,
        validation=ValidationState(
            status="INVALID", icon="✗", error_message="must start with A-Z"
        ),
    )

    footer = select_footer_content(state)

    assert footer.hints == (FooterHint.SELECT_SOURCE, FooterHint.CANCEL)
    assert footer.error == "must start with A-Z"
    assert FooterHint.SUBMIT not in footer.hints
    assert FooterHint.TYPE_TO_EDIT not in footer.hints
