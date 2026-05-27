"""
Main event loop and console entry point.
"""

import shutil

from mapping_resolution_tui.fixtures.storyboard import make_storyboard_config, make_storyboard_mappings
from mapping_resolution_tui.reducer import make_initial_state
from mapping_resolution_tui.renderer import render_frame


def main() -> None:
    height = shutil.get_terminal_size(fallback=(75, 15)).lines
    state = make_initial_state(
        make_storyboard_config(),
        make_storyboard_mappings(),
        frame_height=height,
    )
    print("\n".join(render_frame(state)))
