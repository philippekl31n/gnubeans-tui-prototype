Feature: Accept all resolved mappings and produce output

  Entering the accept confirmation — automatically on resolving the final
  collision, or via ctrl+s from BROWSING once no collisions remain — lets the
  reviewer toggle between YES and NO, commit every mapping with Enter on YES,
  or return to browsing with Enter on NO or Esc (spec §4.1/§4.2, TASK-010).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Resolving the final collision auto-enters the accept confirmation
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO

  Scenario: ctrl+s from browsing opens the accept confirmation once resolved
    Given the AT-T collision is already resolved
    When I press ctrl+s
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO

  Scenario: ctrl+s is ignored while a collision remains unresolved
    When I press ctrl+s
    Then the app should be in BROWSING mode

  Scenario: y and n set the choice and the arrows toggle it
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I type "y"
    Then the confirmation choice should be YES
    When I type "n"
    Then the confirmation choice should be NO
    When I press "KEY_LEFT"
    Then the confirmation choice should be YES
    When I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Enter on YES accepts every mapping
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I type "y"
    And I press "KEY_ENTER"
    Then the result status should be ACCEPTED
    And mapping 3 should have target value "ATT"

  Scenario: Enter on NO returns to browsing with the filter preserved
    Given the AT-T collision is already resolved
    When I type "AT"
    And I press ctrl+s
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode
    And the result status should be RUNNING
    And the filter raw should be "AT"
    And the selected ordinal should be 2

  Scenario: Esc leaves the confirmation and clears its state
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode
    And the confirmation kind should be NONE

  Scenario: Down and up arrows scroll the confirming table without moving the selection
    Given the AT-T collision is already resolved
    When I press ctrl+s
    Then the scroll offset should be 0
    And the confirming body should show ordinals "1,2,3,4,5,6,7,8,9"
    When I press "KEY_DOWN"
    Then the scroll offset should be 1
    And the selected ordinal should be 1
    And the confirming body should show ordinals "2,3,4,5,6,7,8,9,10"
    When I press "KEY_UP"
    Then the scroll offset should be 0
    And the selected ordinal should be 1

  Scenario: Arrow scrolling clamps at the top and at the last full window
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_UP"
    Then the scroll offset should be 0
    When I press "KEY_DOWN"
    And I press "KEY_DOWN"
    And I press "KEY_DOWN"
    Then the scroll offset should be 2
    And the selected ordinal should be 1

  Scenario: Shift arrows page-scroll the confirming table without moving the selection
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_SDOWN"
    Then the scroll offset should be 9
    And the selected ordinal should be 1
    When I press "KEY_SUP"
    Then the scroll offset should be 0
    And the selected ordinal should be 1

  Scenario: Page movement clamps at the last row with a partially-full window
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_DOWN"
    And I press "KEY_PGDOWN"
    Then the scroll offset should be 10
    And the confirming body should show ordinals "11"
    When I press "KEY_PGDOWN"
    Then the scroll offset should be 10
    When I press "KEY_PGUP"
    Then the scroll offset should be 1
    When I press "KEY_PGUP"
    Then the scroll offset should be 0

  Scenario: The confirmation prompt stays visible at every scroll position
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_PGDOWN"
    And I press "KEY_PGDOWN"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO
