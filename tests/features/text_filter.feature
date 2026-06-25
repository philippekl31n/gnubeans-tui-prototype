Feature: Text filter input with cursor and match highlights

  As a reviewer, I want to type a text filter that matches mapping ordinals and
  target tokens only, so that I can narrow the review list without source values
  creating false matches.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Typing a printable character inserts it and advances the cursor
    When the reviewer types "1" into the filter
    Then the filter text is "1"
    And the filter cursor is at offset 1

  Scenario: Typing inserts at the cursor position within existing text
    Given the filter already contains "ac" with the cursor at offset 1
    When the reviewer types "b" into the filter
    Then the filter text is "abc"
    And the filter cursor is at offset 2

  Scenario: Arrow keys move the cursor within the text, clamped to both ends
    Given the filter already contains "abc" with the cursor at offset 3
    When the reviewer presses left arrow
    Then the filter cursor is at offset 2
    When the reviewer presses right arrow
    Then the filter cursor is at offset 3
    When the reviewer presses right arrow
    Then the filter cursor is at offset 3

  Scenario: Readline aliases ctrl+b and ctrl+f move the cursor
    Given the filter already contains "abc" with the cursor at offset 3
    When the reviewer presses "ctrl+b"
    Then the filter cursor is at offset 2
    When the reviewer presses "ctrl+f"
    Then the filter cursor is at offset 3

  Scenario: Backspace removes the character before the cursor
    Given the filter already contains "abc" with the cursor at offset 3
    When the reviewer presses backspace
    Then the filter text is "ab"
    And the filter cursor is at offset 2

  Scenario: Filtering narrows to ordinal and token matches
    When the reviewer types "1" into the filter
    Then the visible ordinals are 1, 4, 10, 11

  Scenario: Source values are excluded from matching
    When the reviewer types "AAPL" into the filter
    Then no rows are visible

  Scenario: A lowercase query matches an uppercase target token
    When the reviewer types "c" into the filter
    Then the visible ordinals are 4

  Scenario: Match spans render bold and the cursor block follows the query
    When the reviewer types "1" into the filter
    And the filter view is rendered
    Then the matched ordinal digit on the row for ordinal 1 is bold
    And the token match on the row for ordinal 4 is bold
    And the source column is not bold on any visible row
    And the prompt ends with a reverse-video cursor block
