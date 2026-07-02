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


def test_collision_groups_override_substitutes_single_mapping_value():
    from mapping_resolution_tui.selectors import select_collision_groups

    mappings = _story_1_4_mappings()

    # Overriding ordinal 3's live value to "ATT" resolves its collision with 2.
    assert select_collision_groups(mappings, override_ordinal=3, override_value="ATT") == ()

    # Overriding ordinal 1's live value to collide with 5 introduces a new group,
    # while the untouched AT-T collision (2, 3) still stands.
    assert select_collision_groups(mappings, override_ordinal=1, override_value="MSFT") == (
        ("AT-T", (2, 3)),
        ("MSFT", (1, 5)),
    )


def test_render_collision_ordinals_matches_committed_selector_outside_editing():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, Mode
    from mapping_resolution_tui.selectors import (
        select_render_collision_ordinals,
        select_unresolved_collision_ordinals,
    )

    mappings = _story_1_4_mappings()
    state = Mock(spec=AppState)
    state.mode = Mode.BROWSING
    state.edit = None
    state.mappings = mappings

    assert select_render_collision_ordinals(state) == select_unresolved_collision_ordinals(mappings)


def test_render_collision_ordinals_reacts_live_to_edit_buffer():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode
    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    mappings = _story_1_4_mappings()
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 3
    state.edit.buffer = "ATT"

    # Frame 5: typing "ATT" over mapping 3 (default "AT-T") drops both AT-T
    # markers immediately, well before the edit is submitted.
    assert select_render_collision_ordinals(state) == frozenset()


def test_render_collision_ordinals_empty_buffer_never_resolves_a_collision():
    from dataclasses import replace
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode
    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    # Mappings 2 and 3 collide on a committed literal target that differs from
    # both default source values. Clearing the edit buffer must NOT substitute
    # the default source value ("AT-T") for the committed "XCOL" — an empty
    # buffer never resolves a conflict (TASK-008 / FR8).
    mappings = [
        replace(m, target_value="XCOL") if m.ordinal in (2, 3) else m
        for m in _story_1_4_mappings()
    ]
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 3
    state.edit.buffer = ""

    assert select_render_collision_ordinals(state) == frozenset({2, 3})


def test_render_collision_ordinals_empty_buffer_keeps_default_value_collision():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode
    from mapping_resolution_tui.selectors import select_render_collision_ordinals

    # Frame 4: entering edit on the AT-T collision row seeds an empty buffer;
    # both AT-T rows keep their committed markers until the buffer deviates.
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = _story_1_4_mappings()
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 3
    state.edit.buffer = ""

    assert select_render_collision_ordinals(state) == frozenset({2, 3})


def test_edit_is_submittable_false_when_validation_invalid():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode, ValidationState
    from mapping_resolution_tui.selectors import select_edit_is_submittable

    mappings = _story_1_4_mappings()
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 1
    state.edit.buffer = "APPLE2"
    state.edit.validation = ValidationState(status="INVALID", icon=None, error_message="bad token")

    assert select_edit_is_submittable(state, state.edit) is False


def test_edit_is_submittable_false_when_effective_value_unchanged():
    from dataclasses import replace
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode, ValidationState
    from mapping_resolution_tui.selectors import select_edit_is_submittable

    # Mapping 5 already has a committed target of "MSFT"; retyping the same
    # value is valid and non-colliding but is not a change, so it must not
    # be submittable.
    mappings = [
        replace(m, target_value="MSFT") if m.ordinal == 5 else m
        for m in _story_1_4_mappings()
    ]
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 5
    state.edit.buffer = "MSFT"
    state.edit.validation = ValidationState(status="VALID", icon="✓", error_message=None)

    assert select_edit_is_submittable(state, state.edit) is False


def test_edit_is_submittable_false_when_result_collides():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode, ValidationState
    from mapping_resolution_tui.selectors import select_edit_is_submittable

    # Mapping 3's default "AT-T" already collides with mapping 2's effective
    # "AT-T"; retyping that same colliding value must not be submittable.
    mappings = _story_1_4_mappings()
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 3
    state.edit.buffer = "AT-T"
    state.edit.validation = ValidationState(status="VALID", icon="✓", error_message=None)

    assert select_edit_is_submittable(state, state.edit) is False


def test_edit_is_submittable_true_when_valid_changed_and_non_colliding():
    from unittest.mock import Mock

    from mapping_resolution_tui.state import AppState, EditState, Mode, ValidationState
    from mapping_resolution_tui.selectors import select_edit_is_submittable

    mappings = _story_1_4_mappings()
    state = Mock(spec=AppState)
    state.mode = Mode.EDITING
    state.mappings = mappings
    state.edit = Mock(spec=EditState)
    state.edit.mapping_ordinal = 1
    state.edit.buffer = "APPLE2"
    state.edit.validation = ValidationState(status="VALID", icon="✓", error_message=None)

    assert select_edit_is_submittable(state, state.edit) is True


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
