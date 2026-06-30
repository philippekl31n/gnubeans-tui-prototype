Feature: Enter edit mode and type a replacement token

  Pressing Enter on a selected mapping opens edit mode with live ghost text and
  validation feedback, so a reviewer can confidently set or correct a target
  value before submitting.

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Pressing Enter on a selected row enters edit mode with an empty buffer
    Given the reviewer has selected ordinal 1
    When the reviewer presses enter
    Then the mode is EDITING
    And the edited ordinal is 1
    And the edit buffer is empty
    And the edit cursor is at position 0
    And the ghost suffix is "APPLE"

  Scenario: Typing a prefix character keeps the ghost and advances the cursor
    Given the reviewer is editing ordinal 1
    When the reviewer types "A" into the token input
    Then the edit buffer is "A"
    And the edit cursor is at position 1
    And the ghost suffix is "PPLE"
    And the validation status is "VALID"

  Scenario: Typing past the default-source prefix hides the ghost
    Given the reviewer is editing ordinal 1
    When the reviewer types "AX" into the token input
    Then the edit buffer is "AX"
    And the ghost suffix is empty

  Scenario: Invalid input is inserted and gates the submit key
    Given the reviewer is editing ordinal 1
    When the reviewer types "44PL" into the token input
    Then the edit buffer is "44PL"
    And the validation status is "INVALID"
    And the footer error reads "must start with A-Z"
    And the submit hint is not offered

  Scenario: A valid token offers the submit hint
    Given the reviewer is editing ordinal 1
    When the reviewer types "ATT" into the token input
    Then the validation status is "VALID"
    And the submit hint is offered

  Scenario: Backspace removes the character before the cursor
    Given the reviewer is editing ordinal 1
    When the reviewer types "ATT" into the token input
    And the reviewer presses backspace in the token input
    Then the edit buffer is "AT"
    And the edit cursor is at position 2
