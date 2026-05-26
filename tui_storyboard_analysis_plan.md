# TUI Interaction Storyboard Analysis Plan

## Dimension 1 — State Machine Completeness
- Map every named mode (`BROWSING`, `FILTERING`, `CONFIRMING`, editing) and verify each has defined entry and exit paths
- Check for missing terminal states: what happens after the user accepts all (presses `Y` + `↵` in CONFIRMING)?
- Verify every `> TRANSITION:` block leads to a numbered state and every state is reachable

## Dimension 2 — Transition Correctness
- For each transition, verify the *from* state's shortcuts bar actually lists the key being pressed
- Example: State 6 shows `↵ confirm` but the 6→7 transition uses `n` or `→` — are those exposed?
- Check multi-step transitions (e.g., "User types `↵`, `1`") arrive in a state consistent with both inputs sequentially applied

## Dimension 3 — Data Consistency Across States
- Track all 11 rows across every mockup: ordinals, token values, GnuCash Source strings
- Flag unexpected row mutations (e.g., State 9 shows row 1 with `cmdty_id: "AAPL"` but State 1 shows `user_symbol: "APPLE"` — same row, different source)
- Verify collision count in the header line tracks correctly with actual `!`-marked rows

## Dimension 4 — Mockup Line Budget
- Count physical lines in each mockup and verify ≤ 15 (stated terminal height)
- State 6 (CONFIRMING) shows 9 data rows + header + prompt + column headers + shortcuts = verify it fits
- Check that blank padding lines are used correctly to fill to 15 without overflow

## Dimension 5 — Column Alignment
- Verify ordinal column width rule ("two digits wide matching table size") holds for all mockups
- Check the `┃` sidebar in edit mode is consistently positioned across states 4, 5, 9, 10, 11, 12
- Verify `▸` cursor, `!`, `✓`, `✗` icons don't disturb column alignment

## Dimension 6 — Filter State Machine
- Trace filter string header across states 2→3→8→12→13: verify it reflects exactly what keys were typed
- State 2 filter is `!* *`, state 3 is `!3* *` (user typed `3`) — confirm cursor position in filter bar is shown
- Verify `esc` from filter returns to the correct prior mode (BROWSING vs. CONFIRMING depending on how filter was entered)
- Confirm filter matches only ordinal + Beancount Token columns (not GnuCash Source), as stated in State 8 note

## Dimension 7 — Edit Mode Behavior
- Verify `↑↓ select` in edit mode navigates *within* the expanded row's source options (the `┃` sidebar entries), not between table rows
- State 12 shows `▸` moved to `user_symbol` source line — confirm this is consistent with `↑↓` behavior
- Verify dim styling applies to all non-selected surrounding rows consistently across edit states
- Confirm collision icon `!` removal timing (State 5 note: disappears as soon as token deviates from default)

## Dimension 8 — Input Validation & Cursor Rules
- State 10: error appears after first `4` (immediately) — confirm `✗` icon placement rule ("two spaces right of cursor") is mockup-accurate
- State 11: 24-char limit with icon at column 33 — verify the described column 32/33 exception is documented as intentional or a known limitation
- Confirm the 25th-character-discard + flash behavior has a corresponding mockup or is noted as non-visual

## Dimension 9 — CONFIRMING Mode Gaps
- The `[Y/N]` prompt: how does keyboard navigation between Y and N work? State 6→7 transition uses `n` or `→` — is `←` defined? Is `Y` a direct accept?
- State 7 shows rows 10–11 (bottom of dataset) — how did the cursor get there from State 6 which showed rows 1–9? The transition says `↓` but that's one step — is paging defined?
- State 14 returns to CONFIRMING with `[y/*N*]` retained — confirm this "boolean memory" rule is applied consistently

## Dimension 10 — Missing States / Open Questions
- No mockup for: final accept (Y + `↵`), program exit, or error states (e.g., invalid file input)
- No mockup for BROWSING with 0 collisions (only collision > 0 shown in State 1)
- The `*T*` hint in State 1's filter line (`Filter: *T*ab to view collisions`) — is this a metafilter shortcut hint, and is it defined anywhere?

---

**Output per dimension:** confirmed behaviors, flagged inconsistencies, open questions — ranked as *blocks implementation*, *needs clarification*, or *cosmetic*.
