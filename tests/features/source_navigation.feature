Feature: Navigate alternative sources and autofill the edit buffer

  While editing a mapping the reviewer can arrow into the list of available
  sources and autofill the token buffer from the pointed source's effective
  value, so an established token can be chosen without re-typing (FR21).

  Background:
    Given the storyboard fixture is loaded in a 15-row terminal

  Scenario: Down from the token input jumps to the first source and autofills
    Given the reviewer is editing ordinal 1
    When the reviewer presses down arrow in the edit view
    Then the focus region is SOURCE_LIST
    And the source pointer index is 0
    And the saved source entry buffer is empty
    And the edit buffer is "AAPL"
    And the edit cursor is at position 4
    And the validation status is "VALID"
    And the source pointer is on the cmdty_id source
    And exactly one source pointer indicator is rendered

  Scenario: Up from the token input wraps to the last source and autofills
    Given the reviewer is editing ordinal 1
    When the reviewer presses up arrow in the edit view
    Then the focus region is SOURCE_LIST
    And the source pointer index is 1
    And the edit buffer is "APPLE"
    And the edit cursor is at position 5
    And the validation status is "VALID"
    And the source pointer is on the user_symbol source

  Scenario: Down within the source list advances the pointer and autofills
    Given the reviewer is editing ordinal 1
    When the reviewer presses down arrow in the edit view
    And the reviewer presses down arrow in the edit view
    Then the focus region is SOURCE_LIST
    And the source pointer index is 1
    And the edit buffer is "APPLE"
    And the source pointer is on the user_symbol source

  Scenario: Moving down past the last source returns to the token input
    Given the reviewer is editing ordinal 1
    When the reviewer types "AT" into the token input
    And the reviewer presses down arrow in the edit view
    And the reviewer presses down arrow in the edit view
    And the reviewer presses down arrow in the edit view
    Then the focus region is TOKEN_INPUT
    And the source pointer index is cleared
    And the saved source entry buffer is cleared
    And the edit buffer is "AT"
    And the edit cursor is at position 2

  Scenario: Moving up past the first source restores the pre-navigation buffer
    Given the reviewer is editing ordinal 1
    When the reviewer types "AT" into the token input
    And the reviewer presses down arrow in the edit view
    And the reviewer presses up arrow in the edit view
    Then the focus region is TOKEN_INPUT
    And the source pointer index is cleared
    And the edit buffer is "AT"

  Scenario: Typing a character in the source list exits navigation and edits the autofill
    Given the reviewer is editing ordinal 1
    When the reviewer presses down arrow in the edit view
    And the reviewer types "X" into the token input
    Then the focus region is TOKEN_INPUT
    And the source pointer index is cleared
    And the saved source entry buffer is cleared
    And the edit buffer is "AAPLX"

  Scenario: Backspace in the source list exits navigation and deletes from the autofill
    Given the reviewer is editing ordinal 1
    When the reviewer presses up arrow in the edit view
    And the reviewer presses backspace in the token input
    Then the focus region is TOKEN_INPUT
    And the source pointer index is cleared
    And the edit buffer is "APPL"
