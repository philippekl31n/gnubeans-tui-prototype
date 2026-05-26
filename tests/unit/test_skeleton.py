import pytest

def test_project_skeleton_modules_exist():
    # Attempt to import all the required module boundaries
    import mapping_resolution_tui.config
    import mapping_resolution_tui.state
    import mapping_resolution_tui.actions
    import mapping_resolution_tui.reducer
    import mapping_resolution_tui.selectors
    import mapping_resolution_tui.renderer
    import mapping_resolution_tui.loop
    
    assert mapping_resolution_tui.config is not None
    assert mapping_resolution_tui.state is not None
    assert mapping_resolution_tui.actions is not None
    assert mapping_resolution_tui.reducer is not None
    assert mapping_resolution_tui.selectors is not None
    assert mapping_resolution_tui.renderer is not None
    assert mapping_resolution_tui.loop is not None

def test_dependencies_installed():
    import blessed
    assert blessed is not None
    import pytest_bdd
    assert pytest_bdd is not None
