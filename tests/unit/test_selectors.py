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


def test_select_match_spans_finds_every_non_overlapping_match():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("11", "1") == ((0, 1), (1, 2))
    assert select_match_spans("10", "1") == ((0, 1),)
    assert select_match_spans("C100-F", "1") == ((1, 2),)


def test_select_match_spans_is_ascii_case_insensitive():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("APPLE", "appl") == ((0, 4),)
    assert select_match_spans("apple", "APPL") == ((0, 4),)


def test_select_match_spans_empty_query_or_no_match_returns_no_spans():
    from mapping_resolution_tui.selectors import select_match_spans

    assert select_match_spans("APPLE", "") == ()
    assert select_match_spans("APPLE", "z") == ()


def test_select_ordinal_match_spans_offsets_for_right_aligned_padding():
    from mapping_resolution_tui.selectors import select_ordinal_match_spans

    # ordinal 1 padded to width 2 -> " 1"; the matched digit sits at index 1.
    assert select_ordinal_match_spans(1, "1", 2) == ((1, 2),)
    # ordinal 10 -> "10"; only the leading "1" matches.
    assert select_ordinal_match_spans(10, "1", 2) == ((0, 1),)
    # ordinal 11 -> "11"; every non-overlapping match is reported.
    assert select_ordinal_match_spans(11, "1", 2) == ((0, 1), (1, 2))


def test_select_visible_rows_matches_ordinal_and_token_only_excluding_sources():
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.selectors import select_visible_rows

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)

    # "1" matches ordinals 1/10/11 and the "1" inside token "C100-F" (ordinal 4).
    state_one = replace(state, filter=replace(state.filter, text="1", raw="1", cursor=1))
    assert [m.ordinal for m in select_visible_rows(state_one)] == [1, 4, 10, 11]

    # "AAPL" is only the cmdty_id source value of ordinal 1 (token "APPLE"); the
    # source must not be matched, so the filter yields no rows.
    state_src = replace(state, filter=replace(state.filter, text="AAPL", raw="AAPL", cursor=4))
    assert select_visible_rows(state_src) == []


def test_collision_ghost_visible_only_with_empty_filter_and_collisions():
    from dataclasses import replace

    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    from mapping_resolution_tui.selectors import select_collision_ghost_visible

    state = make_initial_state(make_config(), make_mappings(), frame_height=15)

    # Empty filter with one unresolved collision: the ghost is visible.
    assert select_collision_ghost_visible(state) is True

    # Any filter text hides the ghost (and the Tab autocomplete it gates).
    state_text = replace(state, filter=replace(state.filter, raw="a", text="a", cursor=1))
    assert select_collision_ghost_visible(state_text) is False

    # Resolving the only collision hides the ghost even with an empty filter.
    resolved = replace(
        state,
        mappings=[
            replace(m, target_value="ATT") if m.ordinal == 3 else m
            for m in state.mappings
        ],
    )
    assert select_collision_ghost_visible(resolved) is False


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
