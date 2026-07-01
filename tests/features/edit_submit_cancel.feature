Feature: Submit or cancel an edit and recompute collisions live

  Submitting a valid edit commits the buffer to the mapping target and, when it
  resolves the last outstanding collision, opens the accept confirmation;
  otherwise it returns to the browsing context. Cancelling discards the buffer
  and returns to browsing with the filter intact. Throughout editing the
  collision indicators recompute live from the buffer, and an empty buffer stays
  unresolved (FR8/FR16/FR22/FR23).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Submitting a valid edit that resolves the final collision enters accept confirmation
    Given the reviewer is editing ordinal 3
    When the reviewer types "ATT" into the token input
    And the reviewer presses enter
    Then the mode is CONFIRMING
    And the confirmation kind is ACCEPT
    And the confirmation choice is NO
    And the mapping 3 target value is "ATT"

  Scenario: Submitting a valid edit while collisions remain returns to browsing
    Given the reviewer is editing ordinal 1
    When the reviewer types "APPL" into the token input
    And the reviewer presses enter
    Then the mode is BROWSING
    And the mapping 1 target value is "APPL"
    And the selected ordinal is 1
    And the live collision ordinals are 2, 3

  Scenario: Submitting over an already collision-free dataset returns to browsing
    Given the AT-T collision has already been resolved
    And the reviewer is editing ordinal 1
    When the reviewer types "APPL" into the token input
    And the reviewer presses enter
    Then the mode is BROWSING
    And the mapping 1 target value is "APPL"

  Scenario: Pressing enter with an invalid buffer does not submit
    Given the reviewer is editing ordinal 1
    When the reviewer types "44PL" into the token input
    And the reviewer presses enter
    Then the mode is EDITING
    And the mapping 1 target value is unset
    And the footer error reads "must start with A-Z"

  Scenario: Pressing enter with an empty buffer does not submit
    Given the reviewer is editing ordinal 1
    When the reviewer presses enter
    Then the mode is EDITING
    And the mapping 1 target value is unset

  Scenario: Cancelling with escape preserves the filter and discards the buffer
    Given the reviewer has filtered to "1"
    And the reviewer is editing ordinal 1
    When the reviewer types "XYZ" into the token input
    And the reviewer presses escape
    Then the mode is BROWSING
    And the filter raw is "1"
    And the selected ordinal is 1
    And the mapping 1 target value is unset
    And there is no active edit

  Scenario: Collision markers recompute live and an empty buffer stays unresolved
    Given the reviewer is editing ordinal 3
    Then the live collision ordinals are 2, 3
    When the reviewer types "ATT" into the token input
    Then there are no live collision ordinals
    When the reviewer clears the token input
    Then the edit buffer is empty
    And the live collision ordinals are 2, 3
