import pytest


@pytest.fixture
def initial_state():
    from tests.fixtures.storyboard import make_config, make_mappings
    from mapping_resolution_tui.reducer import make_initial_state
    return make_initial_state(make_config(), make_mappings(), frame_height=15)
