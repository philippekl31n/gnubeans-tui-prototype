Feature: Collision metafilter via bang autocomplete and filter clear

  As a reviewer, I want to engage the collision metafilter with a single Tab and
  clear all active filters with Esc, so that I can focus on what needs resolving
  without manual scrolling or re-typing. The filter is a single editable buffer
  (filter.raw); collision_only and text are derived after every mutation (§3.3).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Tab autocompletes the collision metafilter and clamps selection
    When the reviewer presses "tab"
    Then the filter buffer is "!"
    And the filter cursor is at offset 1
    And the collision-only metafilter is active
    And the visible ordinals are 2, 3
    And the selected ordinal is 2

  Scenario: A second Tab does not clear the autocompleted bang
    When the reviewer presses "tab"
    Then the filter buffer is "!"
    When the reviewer presses "tab"
    Then the filter buffer is "!"
    And the collision-only metafilter is active

  Scenario: Tab does not autocomplete once the filter already has text
    Given the filter buffer already contains "a" with the cursor at offset 1
    When the reviewer presses "tab"
    Then the filter buffer is "a"

  Scenario: Tab does not autocomplete when no unresolved collisions remain
    Given the collision is resolved so no unresolved collisions remain
    When the reviewer presses "tab"
    Then the filter buffer is empty

  Scenario: Typing a bang inserts ordinary editable text that derives the metafilter
    When the reviewer types "!" into the filter
    Then the filter buffer is "!"
    And the collision-only metafilter is active
    And the filter search text is empty

  Scenario: A bang prefix with text shows only matching collision rows
    When the reviewer types "!" into the filter
    And the reviewer types "3" into the filter
    Then the collision-only metafilter is active
    And the filter search text is "3"
    And the visible ordinals are 3

  Scenario: Backspacing the leading bang clears the derived metafilter
    When the reviewer types "!" into the filter
    Then the collision-only metafilter is active
    When the reviewer presses backspace
    Then the filter buffer is empty
    And the collision-only metafilter is inactive

  Scenario: Backspace at the start of the buffer is a no-op
    Given the filter buffer already contains "!3" with the cursor at offset 0
    When the reviewer presses backspace
    Then the filter buffer is "!3"

  Scenario: Esc clears both the metafilter and the search text
    When the reviewer types "!" into the filter
    And the reviewer types "3" into the filter
    And the reviewer presses Esc
    Then the filter buffer is empty
    And the collision-only metafilter is inactive
    And the filter search text is empty
    And the filter cursor is at offset 0
