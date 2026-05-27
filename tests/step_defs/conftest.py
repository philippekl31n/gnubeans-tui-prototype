import pytest


@pytest.fixture
def initial_state():
    from mapping_resolution_tui.fixtures.storyboard import make_storyboard_config, make_storyboard_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    return make_initial_state(make_storyboard_config(), make_storyboard_mappings(), frame_height=15)
