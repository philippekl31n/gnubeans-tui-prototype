import pytest

def test_project_skeleton_modules_exist():
    # Attempt to import all the required module boundaries
    import gnubeans_mapping_tui.config
    import gnubeans_mapping_tui.state
    import gnubeans_mapping_tui.actions
    import gnubeans_mapping_tui.reducer
    import gnubeans_mapping_tui.selectors
    import gnubeans_mapping_tui.renderer
    import gnubeans_mapping_tui.loop
    
    assert gnubeans_mapping_tui.config is not None
    assert gnubeans_mapping_tui.state is not None
    assert gnubeans_mapping_tui.actions is not None
    assert gnubeans_mapping_tui.reducer is not None
    assert gnubeans_mapping_tui.selectors is not None
    assert gnubeans_mapping_tui.renderer is not None
    assert gnubeans_mapping_tui.loop is not None

def test_dependencies_installed():
    import blessed
    assert blessed is not None
    import pytest_bdd
    assert pytest_bdd is not None
