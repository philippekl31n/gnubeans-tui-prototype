Feature: Accept all resolved mappings and produce the output

  A reviewer accepts every resolved mapping and produces the output file. The
  accept confirmation is entered automatically when the last collision is
  resolved (FR23) or manually via ctrl+s once no collision remains. It defaults
  to NO; y/n and the arrow keys set the choice; Enter on YES commits all
  mappings and exits the TUI, while Enter on NO or Esc returns to browsing with
  the filter preserved (spec §4.1/§4.2).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Resolving the last collision auto-enters the accept confirmation
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO

  Scenario: ctrl+s opens the accept confirmation when no collision remains
    Given the AT-T collision is already resolved
    When I press ctrl+s
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO

  Scenario: ctrl+s is a no-op while a collision is still open
    When I press ctrl+s
    Then the app should be in BROWSING mode

  Scenario: y and n set the confirmation choice
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I type "y"
    Then the confirmation choice should be YES
    When I type "n"
    Then the confirmation choice should be NO

  Scenario: Arrow keys toggle the confirmation choice
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_LEFT"
    Then the confirmation choice should be YES
    When I press "KEY_RIGHT"
    Then the confirmation choice should be NO

  Scenario: Accepting on YES commits all mappings and exits the TUI
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I type "y"
    And I press "KEY_ENTER"
    Then the result status should be ACCEPTED
    And mapping 3 should have target value "ATT"

  Scenario: Enter on NO returns to browsing with the filter preserved
    Given the AT-T collision is already resolved
    When I type "1"
    And I press ctrl+s
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode
    And the filter raw should be "1"
    And the result status should be RUNNING

  Scenario: Esc returns to browsing with the filter preserved
    Given the AT-T collision is already resolved
    When I type "1"
    And I press ctrl+s
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode
    And the filter raw should be "1"

  Scenario: Down and up arrows scroll the confirming table without moving the selection
    Given the AT-T collision is already resolved
    When I press ctrl+s
    Then the scroll offset should be 0
    And the selected ordinal should be 1
    And the confirming body should show ordinals "1,2,3,4,5,6,7,8,9"
    When I press "KEY_DOWN"
    Then the scroll offset should be 1
    And the selected ordinal should be 1
    And the confirming body should show ordinals "2,3,4,5,6,7,8,9,10"
    When I press "KEY_UP"
    Then the scroll offset should be 0
    And the selected ordinal should be 1
    And the confirming body should show ordinals "1,2,3,4,5,6,7,8,9"

  Scenario: Up arrow at the top of the confirming table is clamped
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_UP"
    Then the scroll offset should be 0
    And the selected ordinal should be 1

  Scenario: Down arrow scrolling clamps at the last full window
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_DOWN"
    And I press "KEY_DOWN"
    Then the scroll offset should be 2
    When I press "KEY_DOWN"
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

  Scenario: PageDown and PageUp page-scroll and clamp at the last row
    Given the AT-T collision is already resolved
    When I press ctrl+s
    And I press "KEY_PGDOWN"
    Then the scroll offset should be 9
    When I press "KEY_PGDOWN"
    Then the scroll offset should be 10
    And the confirming body should show ordinals "11"
    When I press "KEY_PGDOWN"
    Then the scroll offset should be 10
    When I press "KEY_PGUP"
    Then the scroll offset should be 1
    When I press "KEY_PGUP"
    Then the scroll offset should be 0
