Feature: Submit or cancel an edit with live collision resolution

  Submitting a valid edit commits the buffer to the mapping target and, when
  the post-commit collision count is zero, opens the accept confirmation;
  otherwise it returns to the browsing context with the filter intact.
  Cancelling discards the buffer. Throughout editing the collision markers
  recompute live from the buffer, and an empty buffer never resolves a
  conflict (FR8/FR16/FR22/FR23).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Submitting a valid edit that resolves the final collision enters accept confirmation
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    And I type "ATT"
    And I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
    And the confirmation kind should be ACCEPT
    And the confirmation choice should be NO
    And mapping 3 should have target value "ATT"

  Scenario: Submitting a valid edit while collisions remain returns to browsing
    When I press "KEY_ENTER"
    And I type "APPL"
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode
    And mapping 1 should have target value "APPL"
    And the selected ordinal should be 1
    And the live collision ordinals should be 2 and 3

  Scenario: Submitting preserves the filter exactly as it was on entry
    When I type "1"
    And I press "KEY_ENTER"
    And I type "APPL"
    And I press "KEY_ENTER"
    Then the app should be in BROWSING mode
    And the filter raw should be "1"
    And the selected ordinal should be 1

  Scenario: Pressing enter with an invalid buffer does not submit
    When I press "KEY_ENTER"
    And I type "44PL"
    And I press "KEY_ENTER"
    Then the app should be in EDITING mode
    And mapping 1 should have no target value
    And the edit validation error should be "must start with A-Z"

  Scenario: Pressing enter with an empty buffer does not submit
    When I press "KEY_ENTER"
    And I press "KEY_ENTER"
    Then the app should be in EDITING mode
    And mapping 1 should have no target value

  Scenario: Cancelling with escape preserves the filter and discards the buffer
    When I type "1"
    And I press "KEY_ENTER"
    And I type "XYZ"
    And I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode
    And the filter raw should be "1"
    And the selected ordinal should be 1
    And mapping 1 should have no target value
    And the edit should be cleared

  Scenario: Collision markers recompute live and an empty buffer stays unresolved
    Given the selection is on ordinal 3
    When I press "KEY_ENTER"
    Then the live collision ordinals should be 2 and 3
    When I type "ATT"
    Then there should be no live collision ordinals
    When I press "KEY_BACKSPACE"
    And I press "KEY_BACKSPACE"
    And I press "KEY_BACKSPACE"
    Then the edit buffer should be empty
    And the live collision ordinals should be 2 and 3
