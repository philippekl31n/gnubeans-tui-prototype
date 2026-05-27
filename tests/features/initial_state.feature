Feature: Initial review state

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Initial browsing mode with empty filter and row 1 selected
    When the initial state is inspected
    Then the mode is BROWSING
    And the filter text is empty
    And the selected ordinal is 1
    And the scroll offset is 0
    And edit state is absent

  Scenario: Nine rows are displayed in the initial 15-row frame
    When the visible rows are computed for the initial state
    Then exactly 9 rows are shown in the frame
    And all ordinals from 1 through 9 are among the displayed rows
