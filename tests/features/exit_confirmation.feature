Feature: Exit without saving guarded by a double ctrl+c

  A reviewer is warned before abandoning a mapping session. ctrl+c in browsing
  (or in an accept confirmation) opens the exit confirmation instead of quitting
  outright. It defaults to NO; y/n and the arrow keys set the choice; Enter on
  YES marks the run SKIPPED — a clean skip that adds no commodities — while
  Enter on NO or Esc returns to the mapping review. A second ctrl+c while the
  exit confirmation is armed force-exits by sending SIGINT, bypassing the y/N
  choice entirely (spec §4.1/§4.2).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: ctrl+c in browsing enters the exit confirmation
    When I press ctrl+c
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be EXIT
    And the confirmation choice should be NO
    And the second ctrl+c should be armed
    And the result status should be RUNNING

  Scenario: ctrl+c in the accept confirmation enters the exit confirmation
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press ctrl+c
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be EXIT
    And the confirmation choice should be NO
    And the second ctrl+c should be armed

  Scenario: y and n set the exit confirmation choice
    When I press ctrl+c
    And I type "y"
    Then the confirmation choice should be YES
    When I type "n"
    Then the confirmation choice should be NO

  Scenario: Arrow keys toggle the exit confirmation choice
    When I press ctrl+c
    And I press "KEY_LEFT"
    Then the confirmation choice should be YES
    When I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Enter on YES skips adding commodities without sending a signal
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

  Scenario: A second ctrl+c force-exits with SIGINT bypassing the choice
    When I press ctrl+c
    And I press ctrl+c
    Then the result status should be SIGINT

  Scenario: The second ctrl+c stays armed after toggling the choice
    When I press ctrl+c
    And I type "y"
    And I type "n"
    And I press ctrl+c
    Then the result status should be SIGINT
