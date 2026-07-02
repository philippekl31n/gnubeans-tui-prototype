import pytest
from dataclasses import FrozenInstanceError

def test_root_app_state_has_required_fields():
    from mapping_resolution_tui.state import (
        AppState, AppConfig, FilterState, SelectionState, 
        ConfirmationState, TerminalState, ResultState, Mode
    )
    
    # Just creating a mock instance to verify fields
    state = AppState(
        config=AppConfig(
            entity_name_singular="item",
            entity_name_plural="items",
            mapping_noun_singular="mapping",
            mapping_noun_plural="mappings",
            target_column_label="Target",
            source_column_label="Source",
            accept_prompt="Accept?",
            exit_prompt="Exit?",
            created_message=lambda x: f"{x} created.",
            source_labels=["source1"],
            target_policy=None
        ),
        mode=Mode.BROWSING,
        mappings=[],
        filter=FilterState(raw="", collision_only=False, text="", cursor=0),
        selection=SelectionState(selected_ordinal=None, scroll_offset=0),
        edit=None,
        confirmation=ConfirmationState(kind="NONE", choice="NO", second_ctrl_c_armed=False),
        terminal=TerminalState(height=24, width=80),
        result=ResultState(status="RUNNING")
    )
    
    assert state.config is not None
    assert state.mode == Mode.BROWSING
    assert state.mappings == []
    assert state.filter is not None
    assert state.selection is not None
    assert state.edit is None
    assert state.confirmation is not None
    assert state.terminal is not None
    assert state.result is not None

def test_confirmation_state():
    from mapping_resolution_tui.state import ConfirmationState, ConfirmationKind, ConfirmationChoice
    
    conf = ConfirmationState(
        kind=ConfirmationKind.ACCEPT,
        choice=ConfirmationChoice.YES,
        second_ctrl_c_armed=True
    )
    assert conf.kind == ConfirmationKind.ACCEPT
    assert conf.choice == ConfirmationChoice.YES
    assert conf.second_ctrl_c_armed is True

def test_state_immutability():
    from mapping_resolution_tui.state import SelectionState
    
    selection = SelectionState(selected_ordinal=1, scroll_offset=0)
    with pytest.raises(FrozenInstanceError):
        selection.scroll_offset = 1

def get_commodity_target_policy() -> 'mapping_resolution_tui.state.TargetPolicy':
    from mapping_resolution_tui.state import TargetValidationContext, ValidationState, TargetPolicy
    def validate(value: str, context: TargetValidationContext) -> ValidationState:
        return ValidationState(status="VALID", icon="✓", error_message=None)
    return TargetPolicy(max_token_length=24, validate=validate)

def get_storyboard_config() -> 'mapping_resolution_tui.state.AppConfig':
    from mapping_resolution_tui.state import AppConfig
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
        target_policy=get_commodity_target_policy()
    )

def test_storyboard_fixture_config():
    
    config = get_storyboard_config()
    assert config.entity_name_singular == "commodity"
    assert config.entity_name_plural == "commodities"
    assert config.mapping_noun_singular == "mapping"
    assert config.mapping_noun_plural == "mappings"
    assert config.target_column_label == "Beancount Token"
    assert config.source_column_label == "GnuCash Source"
    assert config.accept_prompt == "Accept all?"
    assert config.exit_prompt == "Skip adding commodities?"
    assert config.created_message(5) == "5 commodities created."
    assert config.source_labels == ["cmdty_id", "user_symbol"]
    assert config.target_policy is not None

def get_storyboard_mappings() -> list:
    from mapping_resolution_tui.state import Mapping, Source
    return [
        Mapping(
            ordinal=1,
            sources=[
                Source(label="cmdty_id", original_value="AAPL", sanitized_value=None),
                Source(label="user_symbol", original_value="APPLE", sanitized_value=None),
            ],
            default_source_label="user_symbol",
            target_value=None
        ),
        Mapping(
            ordinal=2,
            sources=[
                Source(label="cmdty_id", original_value="AT&T", sanitized_value=None),
            ],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=3,
            sources=[
                Source(label="cmdty_id", original_value="AT-T", sanitized_value=None),
            ],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=4,
            sources=[
                Source(label="cmdty_id", original_value="100-F", sanitized_value="C100-F"),
            ],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=5,
            sources=[Source(label="cmdty_id", original_value="GOOGL", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=6,
            sources=[Source(label="cmdty_id", original_value="MSFT", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=7,
            sources=[Source(label="cmdty_id", original_value="NVDA", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=8,
            sources=[Source(label="cmdty_id", original_value="SPY", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=9,
            sources=[Source(label="cmdty_id", original_value="QQQ", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=10,
            sources=[Source(label="cmdty_id", original_value="VTSAX", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
        Mapping(
            ordinal=11,
            sources=[Source(label="cmdty_id", original_value="VWUSX", sanitized_value=None)],
            default_source_label="cmdty_id",
            target_value=None
        ),
    ]

def test_storyboard_fixture_dataset():
    
    mappings = get_storyboard_mappings()
    assert len(mappings) == 11
    
    # Row 1
    m1 = mappings[0]
    assert m1.ordinal == 1
    assert m1.target_value is None
    assert m1.default_source_label == "user_symbol"
    assert len(m1.sources) == 2
    assert m1.sources[0].label == "cmdty_id"
    assert m1.sources[0].original_value == "AAPL"
    assert m1.sources[0].sanitized_value is None
    assert m1.sources[1].label == "user_symbol"
    assert m1.sources[1].original_value == "APPLE"
    assert m1.sources[1].sanitized_value is None

    # Row 2 and 3 initial targets
    m2 = mappings[1]
    m3 = mappings[2]
    assert m2.ordinal == 2
    assert m3.ordinal == 3
    # They should have the same default_source_value = "AT-T"
    assert m2.sources[0].original_value == "AT&T"
    assert m3.sources[0].original_value == "AT-T"

    # Row 4 sanitized value
    m4 = mappings[3]
    assert m4.ordinal == 4
    assert m4.sources[0].original_value == "100-F"
    assert m4.sources[0].sanitized_value == "C100-F"
