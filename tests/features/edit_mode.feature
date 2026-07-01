Feature: Edit Mode

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Enter edit mode and cancel
    When I press "KEY_ENTER"
    Then the app should be in EDITING mode
    And the edit buffer should be empty
    When I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode

  Scenario: Type in edit mode
    When I press "KEY_ENTER"
    And I type "ABC"
    Then the edit buffer should be "ABC"
    And the edit cursor should be at 3

  Scenario: Cancel discards a typed but uncommitted edit
    When I press "KEY_ENTER"
    And I type "ABC"
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode
    And the edit should be cleared

  Scenario: Backspace removes the last typed character
    When I press "KEY_ENTER"
    And I type "ABC"
    And I press "KEY_BACKSPACE"
    Then the edit buffer should be "AB"
    And the edit cursor should be at 2

  Scenario: Invalid input is rejected by the target policy
    When I press "KEY_ENTER"
    And I type "44PL"
    Then the edit validation error should be "must start with A-Z"

  Scenario: Typing beyond the max length is discarded and shows an error
    When I press "KEY_ENTER"
    And I type "ABCDEFGHIJKLMNOPQRSTUVWXY"
    Then the edit buffer should be "ABCDEFGHIJKLMNOPQRSTUVWX"
    And the edit validation error should be "24 chars max"
