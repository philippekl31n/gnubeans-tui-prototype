Feature: Frame 1a rendering — visual narrative

  Background:
    Given the frame 1a is rendered in a 15-row terminal

  Scenario: Header communicates the collision count to the user
    When the header line is inspected
    Then the user sees "1 unresolved collision"
    And the header prompt glyph is bold

  Scenario: Filter prompt shows a keyboard affordance
    When the filter prompt line is inspected
    Then the hint text begins with a reverse-video character
    And the line communicates "Tab to view collisions"

  Scenario: First body row shows the selection cursor
    When the body rows are inspected
    Then the row at display position 1 starts with the selection cursor glyph
