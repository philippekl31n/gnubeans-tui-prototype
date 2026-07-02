Feature: Exit without saving with a double ctrl+c guard

  ctrl+c in BROWSING — or in an accept confirmation — opens the exit
  confirmation (frame 1b) instead of ending the review, guarding against an
  accidental discard. Enter on YES is a clean skip that adds no commodities
  (SKIPPED, never SIGINT); Enter on NO or Esc returns to browsing; a second
  ctrl+c force-exits via SIGINT, bypassing the y/N choice entirely
  (spec §4.1/§4.2, TASK-012).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: ctrl+c from browsing opens the exit confirmation
    When I press ctrl+c
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be EXIT
    And the confirmation choice should be NO
    And the second ctrl+c should be armed
    And the result status should be RUNNING

  Scenario: ctrl+c from an accept confirmation enters the exit confirmation
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press ctrl+c
    Then the confirmation kind should be EXIT
    And the confirmation choice should be NO
    And the second ctrl+c should be armed

  Scenario: y and n set the choice and the arrows toggle it
    When I press ctrl+c
    And I type "y"
    Then the confirmation choice should be YES
    When I type "n"
    Then the confirmation choice should be NO
    When I press "KEY_LEFT"
    Then the confirmation choice should be YES
    When I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Enter on YES skips adding commodities cleanly
    When I press ctrl+c
    And I type "y"
    And I press "KEY_ENTER"
    Then the result status should be SKIPPED

  Scenario: Enter on NO returns to browsing
    When I press ctrl+c
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode
    And the confirmation kind should be NONE
    And the result status should be RUNNING

  Scenario: Esc returns to browsing
    When I press ctrl+c
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode
    And the confirmation kind should be NONE
    And the result status should be RUNNING

  Scenario: a second ctrl+c force-exits via SIGINT
    When I press ctrl+c
    And I press ctrl+c
    Then the result status should be SIGINT

  Scenario: the second ctrl+c bypasses the y/N choice even on YES
    When I press ctrl+c
    And I type "y"
    And I press ctrl+c
    Then the result status should be SIGINT
