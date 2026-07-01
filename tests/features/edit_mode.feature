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

  Scenario: Live collision tracking
    When I type "!AT"
    And I press "KEY_DOWN"
    And I press "KEY_ENTER"
    # Now editing AT-T -> AT-T collision mapping.
    # Buffer is "", which is explicitly treated as unresolved.
    Then the app should report 1 unresolved collision group
    When I type "A"
    # AT-T mapping buffer becomes "A", no longer collides with anything!
    Then the app should report 0 unresolved collision groups
    When I type "T-T"
    # Buffer is "AT-T", collides with the other AT-T mapping again!
    Then the app should report 1 unresolved collision group
    When I press "KEY_ESCAPE"
    Then the app should be in BROWSING mode

  Scenario: Submit edit with unresolved collisions remaining
    When I type "!AT"
    And I press "KEY_DOWN"
    And I press "KEY_ENTER"
    # Edit the second AT-T mapping
    When I type "X"
    # Now it is AT-TX, valid but collision unresolved since another mapping may collide? Wait, if it's AT-TX, it NO LONGER collides!
    # Let me instead edit AAPL to GOOGL to CREATE a collision.
    When I press "KEY_ESCAPE"
    And I press "KEY_ESCAPE"
    # Reset filter
    When I type "APPLE"
    And I press "KEY_ENTER"
    # Edit APPLE mapping
    When I type "GOOGL"
    # Now GOOGL collides with existing GOOGL mapping. So collisions go from 1 to 2!
    Then the app should report 2 unresolved collision groups
    When I press "KEY_ENTER"
    # Submitted, but 2 collisions remain.
    Then the app should be in BROWSING mode
    And the app should report 2 unresolved collision groups

  Scenario: Submit edit resolving final collision
    When I type "!AT"
    And I press "KEY_ENTER"
    # Edit the first AT-T mapping
    When I type "AT-X"
    # Now it is AT-X, no longer collides!
    Then the app should report 0 unresolved collision groups
    When I press "KEY_ENTER"
    Then the app should be in CONFIRMING mode
