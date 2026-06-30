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
