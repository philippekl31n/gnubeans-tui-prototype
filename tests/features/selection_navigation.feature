Feature: Selection clamping, browsing navigation, and empty results

  As a reviewer, I want selection to remain predictable when filters change or
  match nothing, and to move the selection by row or by page, so that browsing
  never points at a hidden row or an invalid mapping (FR12, FR13, FR14; spec
  §3.4, §8.2, §8.3, §8.5).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Selection is unchanged when the filter leaves the selected row visible
    When the reviewer types "1" into the filter
    Then the visible ordinals are 1, 4, 10, 11
    And the selected ordinal is 1

  Scenario: Selection clamps to the first visible row when the filter hides it
    Given the reviewer has selected ordinal 5
    When the reviewer types "!" into the filter
    Then the visible ordinals are 2, 3
    And the selected ordinal is 2

  Scenario: Collision metafilter plus the text 3 selects ordinal 3 only
    When the reviewer types "!" into the filter
    And the reviewer types "3" into the filter
    Then the visible ordinals are 3
    And the selected ordinal is 3

  Scenario: A filter that matches nothing clears the selection
    When the reviewer types "z" into the filter
    Then no rows are visible
    And the selection is cleared

  Scenario: The empty-result frame renders a blank body row and the error footer
    When the reviewer types "z" into the filter
    And the browsing frame is rendered
    Then a single blank body row is shown under the table header
    And no row cursor is rendered
    And the footer reads "Error: no matching rows  ·  esc clear filter"

  Scenario: Down and up arrows move the selection one row, clamped at the ends
    When the reviewer presses down arrow
    Then the selected ordinal is 2
    When the reviewer presses up arrow
    Then the selected ordinal is 1
    When the reviewer presses up arrow
    Then the selected ordinal is 1

  Scenario: Arrow keys move the cursor between rows without scrolling the list
    When the reviewer presses down arrow
    Then the selected ordinal is 2
    And the scroll offset is 0
    And the rendered body still shows ordinal 1
    And the rendered body still shows ordinal 9
    And the row cursor is on ordinal 2

  Scenario: ctrl+n and ctrl+p page the selection down and up
    When the reviewer presses "ctrl+n"
    Then the scroll offset is 9
    And the selected ordinal is 10
    When the reviewer presses "ctrl+p"
    Then the scroll offset is 0
    And the selected ordinal is 1

  Scenario: The down arrow clamps at the last visible row
    When the reviewer presses down arrow 12 times
    Then the selected ordinal is 11
    And the selected row is visible in the rendered body

  Scenario: PgDn pages to the last page and selects its first row
    When the reviewer presses page down
    Then the scroll offset is 9
    And the selected ordinal is 10
    And the selected row is visible in the rendered body
    When the reviewer presses page down
    Then the scroll offset is 9
    And the selected ordinal is 11

  Scenario: PgUp pages back to the top and selects the first row
    When the reviewer presses "ctrl+n"
    And the reviewer presses page up
    Then the scroll offset is 0
    And the selected ordinal is 1
    And the selected row is visible in the rendered body
    When the reviewer presses page up
    Then the scroll offset is 0
    And the selected ordinal is 1

  Scenario: Page keys stay reliable when shifted arrows are indistinguishable
    When a plain down arrow arrives because the terminal cannot detect shift
    Then the selected ordinal is 2
    And the scroll offset is 0
    When PgDn arrives from the same terminal
    Then the scroll offset is 9
    And the selected ordinal is 10
