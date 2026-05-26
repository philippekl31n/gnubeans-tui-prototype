### 6. The "confirm all" exit path (Y → ↵) is never shown

The storyboard ends at Frame 14 (back to CONFIRMING with N). The state after pressing `↵` with Y selected — success screen, program exit, return value — is never depicted. This is a meaningful terminal state that's completely absent.

---

### 7. ~~BROWSING with 0 collisions is never shown~~ (resolved in storyboard)

Frames 7b and 7c now show BROWSING with 0 collisions. Frame 1a adds a note: "When collisions = 0, filter-prompt ghost-text is `*T*__ype to filter__`".

---

### 8. Collapsed display rule for multiple GnuCash sources

Row 1 appears in collapsed views (Frames 1, 6, 8, 14) as:
```
1   APPLE   user_symbol: "APPLE"
```
But Frame 9's expanded view reveals a **second source**: `cmdty_id: "AAPL"`. The rule for which source is displayed in the single-line collapsed column — and whether any indicator of additional sources exists — is never specified.

---

### 10. Arch spec uses generic labels inconsistent with storyboard

Two concrete mismatches between the arch spec and every storyboard frame:
- HeaderComponent template says `Reviewing {total} items.` — storyboard says "commodity mappings".
- TableComponent header row says `Target Value` / `Source Data` — storyboard says `Beancount Token` / `GnuCash Source`.

---

### 11. `ctrl+s submit` shortcut is absent from the arch spec

Frames 7b–13 all show `ctrl+s submit · ctrl+c cancel` in the header when collisions = 0. Frame 13 → 14 uses `ctrl+s` as the transition. The arch spec has no mention of `ctrl+s` anywhere — not in the keyboard routing matrix, not in RootLayout events, not in ShortcutsFooter templates. Required spec: trigger conditions (BROWSING/EDITING, collisions = 0), action (enter CONFIRMING with N pre-selected), and whether it is available or blocked during EDITING.

---

### 12. ctrl+c skip-confirmation state (Frame 1b) is absent from the arch spec

Frame 1b shows a new CONFIRMING-like state triggered by `ctrl+c`: prompt is `Skip adding commodities? [y/*N*]`, scrollable table, footer `↑↓ scroll · shift+↑↓ pageup/dn · ↵ edit mappings`. This is a second "confirm" variant distinct from the "Accept all?" CONFIRMING mode in every way — different prompt, different default boolean (N not Y), different Y outcome (exit without saving). None of this is described in the arch spec. Pressing `ctrl+c` a second time in this state sends SIGINT.

---

### 13. FILTERING mode is deprecated but still present in the arch spec

Per the updated storyboard, filtering is live within BROWSING mode — the table reacts as the user types with no `↵`-gated mode transition. There is no separate `FILTERING` AppMode. The arch spec still has `FILTERING` as an enum value with its own full keyboard routing section. The entire FILTERING routing block must be removed and its behaviors absorbed into BROWSING. Key changes: filter input mutates `filterQuery` live; `↵` in BROWSING goes directly to EDITING (not FILTERING); `esc` clears filter and stays in BROWSING; the `esc → CONFIRMING` rule is removed.

---

### 14. ShortcutsFooter templates don't match storyboard

All six templates in the arch spec ShortcutsFooter differ from the storyboard. Representative gaps:
- Arch spec BROWSING: `Type to filter · ↑↓ prev/next page · ↵ select row` — storyboard: `shift+↑↓ pageup/dn · ↵ edit selected`
- Arch spec Confirming (Y): `↑↓ prev/next page · ↵ confirm` — storyboard: `↑↓ scroll · shift+↑↓ pageup/dn · ↵ confirm`
- "Type to filter" appears in both arch spec BROWSING/FILTERING templates but never in any storyboard frame.

---

### 15. `▸` cursor semantics in BROWSING contradict the arch spec

Arch spec: `selectedIndex: number | null (null when Props.mode is BROWSING or CONFIRMING)`. But Frames 1a, 7b, 7c all show `▸` in BROWSING and the transition 7b → 7c uses plain `↑` to move it by one row. `selectedIndex` must be a non-null tracked value in BROWSING. The arch spec navigation event description also only says BROWSING "paginates scrollOffset" and makes no mention of per-row cursor movement.

---

### 16. Filter hint ghost-text mechanism is unspecified in the arch spec

Three distinct filter prompt states are visible in the storyboard but none are fully described in the arch spec:

1. Empty filter, collisions > 0: `T` of "Tab to view collisions" is in reverse-video (acting as a cursor hint).
2. Empty filter, collisions = 0: `T` of "Type to filter" is in reverse-video.
3. Metafilter prefix typed (e.g. `!`): prefix renders normally, then `T` of "Type to filter" is in reverse-video.

The arch spec PromptComponent defines only one static BROWSING template and one active FILTERING template (which is now moot). The ghost-text hint mechanism, the collision-count-dependent hint variants, and the cursor-char-as-first-hint-char pattern are all undocumented.

---

### 17. BROWSING `↑↓` row navigation is missing from the ShortcutsFooter

BROWSING footer in all frames shows only `shift+↑↓ pageup/dn`. But transition 7b → 7c uses plain `↑` (no shift) to move `▸` up one row. Plain `↑↓` is a valid, functional key in BROWSING for per-row cursor movement, but it is not advertised in the footer. Confirm whether this is intentional (undocumented power-user key) or an oversight in the footer template.

