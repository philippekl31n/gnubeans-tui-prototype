Feature: Text filter input with cursor and match highlights

  As a reviewer, I want to type a text filter that matches mapping ordinals and
  target tokens only, so that I can narrow the review list without source values
  creating false matches. The filter is a single editable buffer (filter.raw)
  whose collision-only metafilter and search text are derived (spec §3.3).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Typing a printable character inserts it and advances the cursor
    When the reviewer types "1" into the filter
    Then the filter buffer is "1"
    And the filter cursor is at offset 1

  Scenario: Typing inserts at the cursor position within existing text
    Given the filter buffer already contains "ac" with the cursor at offset 1
    When the reviewer types "b" into the filter
    Then the filter buffer is "abc"
    And the filter cursor is at offset 2

  Scenario: A leading bang is ordinary text that derives the collision metafilter
    When the reviewer types "!" into the filter
    Then the filter buffer is "!"
    And the filter search text is empty
    And the collision-only metafilter is active

  Scenario: Tab is a no-op in browsing (reserved for bang autocomplete)
    When the reviewer presses "tab"
    Then the filter buffer is empty

  Scenario: Arrow keys move the cursor within the buffer, clamped to both ends
    Given the filter buffer already contains "abc" with the cursor at offset 3
    When the reviewer presses left arrow
    Then the filter cursor is at offset 2
    When the reviewer presses right arrow
    Then the filter cursor is at offset 3
    When the reviewer presses right arrow
    Then the filter cursor is at offset 3

  Scenario: Readline aliases ctrl+b and ctrl+f move the cursor
    Given the filter buffer already contains "abc" with the cursor at offset 3
    When the reviewer presses "ctrl+b"
    Then the filter cursor is at offset 2
    When the reviewer presses "ctrl+f"
    Then the filter cursor is at offset 3

  Scenario: ctrl+a and ctrl+e jump the cursor to the buffer ends
    Given the filter buffer already contains "abc" with the cursor at offset 1
    When the reviewer presses "ctrl+a"
    Then the filter cursor is at offset 0
    When the reviewer presses "ctrl+e"
    Then the filter cursor is at offset 3

  Scenario: Backspace removes the character before the cursor
    Given the filter buffer already contains "abc" with the cursor at offset 3
    When the reviewer presses backspace
    Then the filter buffer is "ab"
    And the filter cursor is at offset 2

  Scenario: ctrl+d deletes the character at the cursor
    Given the filter buffer already contains "abc" with the cursor at offset 1
    When the reviewer presses "ctrl+d"
    Then the filter buffer is "ac"
    And the filter cursor is at offset 1

  Scenario: ctrl+k kills from the cursor to the end of the buffer
    Given the filter buffer already contains "abcdef" with the cursor at offset 2
    When the reviewer presses "ctrl+k"
    Then the filter buffer is "ab"
    And the filter cursor is at offset 2

  Scenario: ctrl+u discards from the start of the buffer to the cursor
    Given the filter buffer already contains "abcdef" with the cursor at offset 4
    When the reviewer presses "ctrl+u"
    Then the filter buffer is "ef"
    And the filter cursor is at offset 0

  Scenario: ctrl+w deletes the word before the cursor
    Given the filter buffer already contains "foo bar" with the cursor at offset 7
    When the reviewer presses "ctrl+w"
    Then the filter buffer is "foo "
    And the filter cursor is at offset 4

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
