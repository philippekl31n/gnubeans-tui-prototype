Feature: Collision metafilter via bang autocomplete and filter clear

  Tab (and ctrl+i) autocompletes a leading ! into the filter only while the
  "Tab to view collisions" ghost is visible — an empty filter with at least one
  unresolved collision. The ! is ordinary editable text once present, so a
  second Tab never clears it. Esc clears the whole filter and restores the list.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Tab autocompletes the collision metafilter when the ghost is visible
    When the reviewer presses Tab
    Then the filter prompt shows "!"
    And the collision metafilter is active
    And the visible ordinals are 2, 3
    And the selected ordinal is 2

  Scenario: A second Tab does not clear the inserted bang
    When the reviewer presses Tab
    And the reviewer presses Tab
    Then the filter prompt shows "!"
    And the visible ordinals are 2, 3

  Scenario: Tab does not autocomplete when the filter already has text
    When the reviewer types "3" into the filter
    And the reviewer presses Tab
    Then the filter prompt shows "3"
    And the collision metafilter is not active

  Scenario: Tab does not autocomplete when no unresolved collisions remain
    Given the AT-T collision is resolved
    When the reviewer presses Tab
    Then the filter prompt is empty
    And the collision metafilter is not active

  Scenario: Typing a leading bang engages the metafilter as ordinary text
    When the reviewer types "!" into the filter
    Then the collision metafilter is active
    And the visible ordinals are 2, 3

  Scenario: A leading bang with trailing text filters collisions by the text
    When the reviewer types "!3" into the filter
    Then the collision metafilter is active
    And the visible ordinals are 3
    And the selected ordinal is 3

  Scenario: Esc clears the metafilter and returns to the top of the list
    When the reviewer presses Tab
    And the reviewer presses esc
    Then all 11 rows are visible
    And the filter prompt is empty
    And the collision metafilter is not active
    And the selected ordinal is 1
