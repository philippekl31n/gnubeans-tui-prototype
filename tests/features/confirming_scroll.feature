Feature: Confirming scroll flow

  In CONFIRMING mode, the table list does not have a selection cursor.
  Instead, the user can use arrow keys and page keys to scroll the table view
  while keeping the prompt intact and without affecting selected_ordinal.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Up and down arrows scroll by one row in CONFIRMING mode
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the scroll offset should be 0
    When I press "KEY_DOWN"
    Then the scroll offset should be 1
    And the selected ordinal should be 3
    When I press "KEY_UP"
    Then the scroll offset should be 0
    And the selected ordinal should be 3

  Scenario: Shift+Up and Shift+Down page scroll in CONFIRMING mode
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the scroll offset should be 0
    When I press "KEY_PGDOWN"
    Then the scroll offset should be 2
    And the selected ordinal should be 3
    When I press "KEY_PGUP"
    Then the scroll offset should be 0
    And the selected ordinal should be 3
