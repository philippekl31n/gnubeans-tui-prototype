Feature: Selection clamping, browsing navigation, and empty-result rendering

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Filter change clamps selection to first visible row and resets scroll
    When the reviewer types "3" into the filter
    Then the visible ordinals are 3
    And the selected ordinal is 3
    And the scroll offset is 0
    When the reviewer presses esc
    Then the visible ordinals are 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
    And the selected ordinal is 1
    And the scroll offset is 0

  Scenario: Up and down arrows move selection within visible rows
    When the reviewer presses down
    Then the selected ordinal is 2
    When the reviewer presses down
    Then the selected ordinal is 3
    When the reviewer presses up
    Then the selected ordinal is 2
    When the reviewer presses up
    Then the selected ordinal is 1
    When the reviewer presses up
    Then the selected ordinal is 1
    
  Scenario: Page up and page down move selection by capacity and clamp
    When the reviewer presses page down
    Then the scroll offset is 2
    And the selected ordinal is 3
    When the reviewer presses page down
    Then the scroll offset is 2
    And the selected ordinal is 3
    When the reviewer presses page up
    Then the scroll offset is 0
    And the selected ordinal is 1

  Scenario: Readline aliases ctrl+n and ctrl+p move selection
    When the reviewer presses ctrl+n
    Then the selected ordinal is 2
    When the reviewer presses ctrl+p
    Then the selected ordinal is 1

  Scenario: Empty filter results render error footer and no rows
    When the reviewer types "999" into the filter
    Then no rows are visible
    And the selected ordinal is None
    And the footer shows "Error: no matching rows"
