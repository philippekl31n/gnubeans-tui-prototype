"""
Main event loop and console entry point.
"""



from mapping_resolution_tui.state import AppConfig, Mapping
from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.renderer import render_lines


def run(
    config: AppConfig,
    mappings: list[Mapping],
) -> list[Mapping] | None:
    # Initialize the core application state
    state = make_initial_state(config, mappings)
    
    # Event loop will listen for input, update terminal height, and redraw
    # For now, just print the static inline UI:
    print("\n".join(render_lines(state)))
    
    return state.mappings
