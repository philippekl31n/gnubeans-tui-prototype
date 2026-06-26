Feature: Text filter input with cursor and match highlights

  Text filtering narrows the review list by ordinal and target token only.
  Source values never create matches. Line editing follows readline semantics
  and every match is highlighted in the rendered frame.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Typing a digit narrows the list to ordinal and token matches
    When the reviewer types "1" into the filter
    Then the visible ordinals are 1, 4, 10, 11
    And the filter prompt shows "1"

  Scenario: Matches are highlighted in bold in the rendered frame
    When the reviewer types "1" into the filter
    Then the ordinal digit "1" is bold on the first visible row
    And the "1" inside the C100-F token is bold

  Scenario: Source values never create false matches
    When the reviewer types "AAPL" into the filter
    Then no rows are visible

  Scenario: Backspace removes the character before the cursor
    When the reviewer types "12" into the filter
    And the reviewer presses backspace
    Then the filter prompt shows "1"
    And the visible ordinals are 1, 4, 10, 11

  Scenario: Esc clears the filter and restores every row
    When the reviewer types "1" into the filter
    And the reviewer presses esc
    Then all 11 rows are visible
    And the filter prompt is empty
