from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any
from enum import Enum

class Mode(Enum):
    BROWSING = "BROWSING"
    EDITING = "EDITING"
    CONFIRMING = "CONFIRMING"

class ConfirmationKind(Enum):
    NONE = "NONE"
    ACCEPT = "ACCEPT"
    EXIT = "EXIT"

class ConfirmationChoice(Enum):
    YES = "YES"
    NO = "NO"

class FocusRegion(Enum):
    TOKEN_INPUT = "TOKEN_INPUT"
    SOURCE_LIST = "SOURCE_LIST"

@dataclass(frozen=True)
class TargetValidationContext:
    is_concrete_buffer: bool
    is_ghost_only_default: bool
    mapping: 'Mapping'

@dataclass(frozen=True)
class ValidationState:
    status: str
    icon: Optional[str]
    error_message: Optional[str]

@dataclass(frozen=True)
class TargetPolicy:
    max_token_length: int
    validate: Callable[[str, TargetValidationContext], ValidationState]

@dataclass(frozen=True)
class Source:
    label: str
    original_value: Optional[str]
    sanitized_value: Optional[str]

@dataclass(frozen=True)
class Mapping:
    sources: List[Source]
    default_source_label: str
    target_value: Optional[str]
    ordinal: Optional[int] = None

@dataclass(frozen=True)
class AppConfig:
    entity_name_singular: str
    entity_name_plural: str
    mapping_noun_singular: str
    mapping_noun_plural: str
    target_column_label: str
    source_column_label: str
    accept_prompt: str
    exit_prompt: str
    created_message: Callable[[int], str]
    source_labels: List[str]
    target_policy: TargetPolicy

@dataclass(frozen=True)
class FilterState:
    raw: str
    collision_only: bool
    text: str
    cursor: int

@dataclass(frozen=True)
class SelectionState:
    selected_ordinal: Optional[int]
    scroll_offset: int

@dataclass(frozen=True)
class EditState:
    mapping_ordinal: int
    buffer: str
    cursor: int
    focus_region: FocusRegion
    source_pointer_index: Optional[int]
    source_entry_buffer: Optional[str]
    validation: ValidationState
    max_length_flash_until: Optional[float]

@dataclass(frozen=True)
class ConfirmationState:
    kind: ConfirmationKind
    choice: ConfirmationChoice
    second_ctrl_c_armed: bool

@dataclass(frozen=True)
class TerminalState:
    height: int

@dataclass(frozen=True)
class ResultState:
    status: str


class FooterHint(Enum):
    PAGE_SCROLL = "PAGE_SCROLL"
    EDIT_SELECTED = "EDIT_SELECTED"
    CLEAR_FILTER = "CLEAR_FILTER"
    SCROLL = "SCROLL"
    CONFIRM = "CONFIRM"
    EDIT_MAPPINGS = "EDIT_MAPPINGS"
    TYPE_TO_EDIT = "TYPE_TO_EDIT"
    SELECT_SOURCE = "SELECT_SOURCE"
    SUBMIT = "SUBMIT"
    CANCEL = "CANCEL"
    NO_MATCHING_ROWS = "NO_MATCHING_ROWS"


@dataclass(frozen=True)
class FooterContent:
    hints: tuple[FooterHint, ...]
    error: str | None = None


@dataclass(frozen=True)
class FilterPromptContent:
    filter_raw: str
    filter_text: str
    filter_cursor: int
    collision_only: bool
    collision_hint_visible: bool


@dataclass(frozen=True)
class AppState:
    config: AppConfig
    mode: Mode
    mappings: List[Mapping]
    filter: FilterState
    selection: SelectionState
    edit: Optional[EditState]
    confirmation: ConfirmationState
    terminal: TerminalState
    result: ResultState


