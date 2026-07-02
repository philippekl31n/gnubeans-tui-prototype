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
