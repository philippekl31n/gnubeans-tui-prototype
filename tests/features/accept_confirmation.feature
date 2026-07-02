Feature: Accept confirmation flow

  When all collisions are resolved, the user can enter the accept confirmation
  flow either automatically on submitting the final resolution, or manually via ctrl+s.
  The user can toggle their choice between YES and NO, and confirming YES accepts
  all mappings and writes them to the terminal.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Submitting the final resolution enters accept confirmation with NO focused
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO

  Scenario: Typing y sets choice to YES
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I type "y"
    Then the confirmation choice should be YES

  Scenario: Pressing right sets choice to NO
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I type "y"
    And I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Pressing left sets choice to YES
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I press "KEY_LEFT"
    Then the confirmation choice should be YES

  Scenario: Escaping accept confirmation returns to browsing
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode

  Scenario: CTRL_S from browsing enters accept confirmation if resolved
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I press "KEY_ESCAPE"
    And I press ctrl+s
    Then the app should be in CONFIRMING mode
    And the confirmation choice should be NO

  Scenario: Enter on YES accepts all and produces final result
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    And I type "y"
    And I press "KEY_ENTER"
    Then the app result status should be ACCEPTED
