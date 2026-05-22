--
commit and push the current version of tui_interaction_storyboard and issue_queue

/resume 44615292-2086-48c8-bda2-4d033264c1ca

/branch issue-09

ignoring the last 18 exchanges or so, let's go back to your response to the prompt "analyze tui-interaction-storyboard for any inconsistencies/gaps in the storyboard and/or mockups" -
--

### 6. The "confirm all" exit path (Y → ↵) is never shown

The storyboard ends at Frame 14 (back to CONFIRMING with N). The state after pressing `↵` with Y selected — success screen, program exit, return value — is never depicted. This is a meaningful terminal state that's completely absent.

---

### 7. BROWSING with 0 collisions is never shown

After the edit resolves the collision, the app transitions straight to CONFIRMING and never re-enters BROWSING with 0 collisions. What the filter hint line (`Filter: *T*__ab to view collisions__`) shows — or whether it disappears — when there are no collisions is unspecified.

---

### 8. Collapsed display rule for multiple GnuCash sources

Row 1 appears in collapsed views (Frames 1, 6, 8, 14) as:
```
1   APPLE   user_symbol: "APPLE"
```
But Frame 9's expanded view reveals a **second source**: `cmdty_id: "AAPL"`. The rule for which source is displayed in the single-line collapsed column — and whether any indicator of additional sources exists — is never specified.

---

### 9. Tab key behavior in edit mode is underspecified

The transition to Frame 12 says the user pressed Tab after clearing the token field, and the result shows `APPLE* * ✓` in the token and `▸` on `user_symbol: "APPLE"`. What Tab actually does (activate the source selector? auto-fill the token from the highlighted source? both simultaneously?) and what happens if `▸` is moved to the other source (`cmdty_id: "AAPL"`) — does the token auto-fill "AAPL"? — is never described.
