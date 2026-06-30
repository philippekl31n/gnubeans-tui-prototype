"""
Storyboard fixture: canonical 11-row commodity dataset.
Data only — no application initialization logic.
"""

import random
import re

from dataclasses import replace

from mapping_resolution_tui.state import (
    AppConfig,
    Mapping,
    Source,
    TargetPolicy,
    TargetValidationContext,
    ValidationState,
)

_BEANCOUNT_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")


def _commodity_validate(value: str, context: TargetValidationContext) -> ValidationState:
    if not value:
        return ValidationState(status="EMPTY", icon=None, error_message=None)
    if len(value) > 24:
        return ValidationState(status="INVALID", icon="✗", error_message="24 chars max")
    if not value[0].isupper() or not value[0].isalpha():
        return ValidationState(status="INVALID", icon="✗", error_message="must start with A-Z")
    if not _BEANCOUNT_RE.match(value):
        return ValidationState(status="INVALID", icon="✗", error_message="only A-Z, 0-9, and - allowed")
    if not ((value[-1].isalpha() and value[-1].isupper()) or value[-1].isdigit()):
        return ValidationState(status="INVALID", icon="✗", error_message="must end with A-Z or 0-9")
    return ValidationState(status="VALID", icon="✓", error_message=None)


def make_config() -> AppConfig:
    return AppConfig(
        entity_name_singular="commodity",
        entity_name_plural="commodities",
        mapping_noun_singular="mapping",
        mapping_noun_plural="mappings",
        target_column_label="Beancount Token",
        source_column_label="GnuCash Source",
        accept_prompt="Accept all?",
        exit_prompt="Skip adding commodities?",
        created_message=lambda count: f"{count} commodities created.",
        source_labels=["cmdty_id", "user_symbol"],
        target_policy=TargetPolicy(max_token_length=24, validate=_commodity_validate),
    )


def _canonical_mappings() -> list[Mapping]:
    mappings = [
        Mapping(
            sources=[
                Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
                Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
            ],
            default_source_label="user_symbol",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="AT&T", sanitized_value="AT-T")],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="AT-T", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="100-F", sanitized_value="C100-F")],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="GOOGL", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="MSFT", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="NVDA", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="SPY", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="QQQ", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="VTSAX", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
        Mapping(
            sources=[Source(label="cmdty_id", original_value="VWUSX", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None,
        ),
    ]
    # Every mapping carries both configured source slots (spec §8.7: the storyboard
    # fixture has two sources per mapping). Where no user-assigned symbol exists the
    # user_symbol source is (not set) — inactive for autofill/ghost, but still shown
    # in the expanded edit row's source list (frame 4's `user_symbol: (not set)`).
    return [_ensure_user_symbol_slot(mapping) for mapping in mappings]


def _ensure_user_symbol_slot(mapping: Mapping) -> Mapping:
    if any(source.label == "user_symbol" for source in mapping.sources):
        return mapping
    return replace(
        mapping,
        sources=[
            *mapping.sources,
            Source(label="user_symbol", original_value=None, sanitized_value=None),
        ],
    )


def make_mappings() -> list[Mapping]:
    """Return the 11 storyboard mappings in randomized order.

    Callers must not rely on input order; bootstrap sorting is exercised on every run.
    """
    return random.sample(_canonical_mappings(), 11)
