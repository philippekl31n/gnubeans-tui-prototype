from pytest_bdd import given, when, then, scenarios

scenarios("../features/rendering.feature")


@given("the frame 1a is rendered in a 15-row terminal", target_fixture="screen")
def frame_rendered(frame_1a_screen):
    return frame_1a_screen


@when("the header line is inspected", target_fixture="header")
def header_line(screen):
    return screen.display[0]


@then('the user sees "1 unresolved collision"')
def sees_collision_count(header):
    assert "1 unresolved collision" in header


@then("the header prompt glyph is bold")
def header_glyph_bold(screen):
    assert screen.buffer[0][0].bold is True


@when("the filter prompt line is inspected", target_fixture="prompt")
def prompt_line(screen):
    return screen.display[1]


@then("the hint text begins with a reverse-video character")
def hint_char_is_reverse(screen):
    # "  Filter: " is 10 chars (indices 0–9); index 10 is the first hint char wrapped in _REV
    assert screen.buffer[1][10].reverse is True


@then('the line communicates "Tab to view collisions"')
def prompt_has_tab_hint(prompt):
    assert "Tab to view collisions" in prompt


@when("the body rows are inspected", target_fixture="body")
def body_rows(screen):
    return [screen.display[i] for i in range(4, 13)]


@then("the row at display position 1 starts with the selection cursor glyph")
def first_row_has_cursor(body):
    assert body[0].startswith("▸")
