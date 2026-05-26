import pytest

from mapping_resolution_tui.state import AppConfig, Mapping, Source


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
