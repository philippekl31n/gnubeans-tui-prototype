Feature: Exit without saving confirmation

  Scenario: Pressing ctrl+c in BROWSING mode enters EXIT confirmation
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be EXIT
    And the confirmation choice should be NO

  Scenario: Toggling confirmation choice with arrows
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I press "KEY_LEFT"
    Then the confirmation choice should be YES
    When I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Toggling confirmation choice with letters
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I type "y"
    Then the confirmation choice should be YES
    When I type "n"
    Then the confirmation choice should be NO

  Scenario: Pressing enter on NO returns to BROWSING
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode

  Scenario: Pressing esc returns to BROWSING
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I press "KEY_LEFT"
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode

  Scenario: Pressing enter on YES skips and exits
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I press "KEY_LEFT"
    And I press "KEY_ENTER"
    Then the app should exit with status SKIPPED

  Scenario: Second ctrl+c force exits immediately
    Given the storyboard fixture is loaded in a 15-row terminal
    When I press "ctrl+c"
    And I press "ctrl+c"
    Then the app should exit with status SIGINT
