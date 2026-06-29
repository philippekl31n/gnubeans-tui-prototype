"""Unit tests for the synthetic dataset generators in examples/demo.py.

These cover the pure generators only — the interactive loop is not driven here.
"""

from examples.demo import _make_synthetic_config, _make_synthetic_mappings
from mapping_resolution_tui.selectors import select_default_source


def test_synthetic_config_overrides_token_field_width():
    config = _make_synthetic_config(10)

    assert config.target_policy.max_token_length == 10
    # Labels and validator are inherited from the storyboard config.
    assert config.target_column_label == "Beancount Token"
    assert config.source_column_label == "GnuCash Source"


def test_synthetic_mappings_count_matches_items():
    mappings = _make_synthetic_mappings(256, 10)

    assert len(mappings) == 256


def test_synthetic_mappings_tokens_fit_field_and_resolve_source():
    token_length = 10
    mappings = _make_synthetic_mappings(256, token_length)

    for mapping in mappings:
        # Token stays within the M-wide field so the source column stays aligned.
        assert mapping.target_value
        assert len(mapping.target_value) <= token_length
        # default_source_label resolves to one of the mapping's sources.
        assert select_default_source(mapping).label == "cmdty_id"


def test_synthetic_mappings_exercise_sanitization_arrow():
    mappings = _make_synthetic_mappings(8, 10)

    # Every 4th row carries a differing sanitized value (rows 4 and 8 here).
    sanitized = [
        m for m in mappings if select_default_source(m).sanitized_value is not None
    ]
    assert len(sanitized) == 2
