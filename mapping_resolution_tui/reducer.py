"""
Reducer module: pure state transitions and application initialization.
"""

from dataclasses import replace

from mapping_resolution_tui.selectors import sort_mappings_for_initial_display
from mapping_resolution_tui.state import (
    AppConfig,
    AppState,
    ConfirmationChoice,
    ConfirmationKind,
    ConfirmationState,
    FilterState,
    Mapping,
    Mode,
    ResultState,
    SelectionState,
    TerminalState,
)


def make_initial_state(
    config: AppConfig,
    mappings: list[Mapping],
    frame_height: int = 15,
) -> AppState:
    sorted_mappings = list(sort_mappings_for_initial_display(mappings))
    
    # Assign sequential ordinals 1..N after the bootstrap-time sort
    new_mappings = []
    for i, mapping in enumerate(sorted_mappings, 1):
        new_mappings.append(replace(mapping, ordinal=i))

    return AppState(
        config=config,
        mode=Mode.BROWSING,
        mappings=new_mappings,
        filter=FilterState(raw="", collision_only=False, text="", cursor=0),
        selection=SelectionState(
            selected_ordinal=new_mappings[0].ordinal if new_mappings else None,
            scroll_offset=0,
        ),
        edit=None,
        confirmation=ConfirmationState(
            kind=ConfirmationKind.NONE,
            choice=ConfirmationChoice.NO,
            second_ctrl_c_armed=False,
        ),
        terminal=TerminalState(height=frame_height),
        result=ResultState(status="RUNNING"),
    )
