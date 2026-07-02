### ~~6. The "confirm all" exit path (Y → ↵) is never shown~~ (resolved in storyboard and spec)

~~The storyboard ends at Frame 14 (back to CONFIRMING with N). The state after pressing `↵` with Y selected — success screen, program exit, return value — is never depicted. This is a meaningful terminal state that's completely absent.~~

Frame 15 was added to the storyboard: `11 commodities created. / ❯ / [blank lines]`. The arch spec golden-state table covers Frame 15 with `result.status=ACCEPTED` and the exact render assertions.

---

### 7. ~~BROWSING with 0 collisions is never shown~~ (resolved in storyboard)

Frames 7b and 7c now show BROWSING with 0 collisions. Frame 1a adds a note: "When collisions = 0, filter-prompt ghost-text is `*T*__ype to filter__`".

---

### ~~8. Collapsed display rule for multiple GnuCash sources~~ (resolved in storyboard and spec)

~~Row 1 appears in collapsed views (Frames 1, 6, 8, 14) as:~~
~~`1   APPLE   user_symbol: "APPLE"`~~
~~But Frame 9's expanded view reveals a **second source**: `cmdty_id: "AAPL"`. The rule for which source is displayed in the single-line collapsed column — and whether any indicator of additional sources exists — is never specified.~~

The storyboard consistently uses the default source (by `defaultSourceLabel`) in collapsed rows with no indicator of additional sources. The arch spec (§ Source Display) formalises the format: `{label}: "{originalValue}"` for plain values, `{label}: "{originalValue}" → "{sanitizedValue}"` for sanitized values, and `(not set)` for null. The current renderer predates this rule (Epic 1 only); later stories will implement it.

---

### ~~10. Arch spec uses generic labels inconsistent with storyboard~~ (resolved in spec)

~~Two concrete mismatches between the arch spec and every storyboard frame:~~
~~- HeaderComponent template says `Reviewing {total} items.` — storyboard says "commodity mappings".~~
~~- TableComponent header row says `Target Value` / `Source Data` — storyboard says `Beancount Token` / `GnuCash Source`.~~

The arch spec header template now reads `❯ Reviewing {total} {entityNameSingular} {mappingNounPlural}.` and the table header uses `{targetColumnLabel}` / `{sourceColumnLabel}`. The implementation reads these from `AppConfig`; labels are caller-supplied, not hardcoded.

---

### ~~11. `ctrl+s submit` shortcut is absent from the arch spec~~ (resolved in spec)

~~Frames 7b–13 all show `ctrl+s submit · ctrl+c cancel` in the header when collisions = 0. Frame 13 → 14 uses `ctrl+s` as the transition. The arch spec has no mention of `ctrl+s` anywhere — not in the keyboard routing matrix, not in RootLayout events, not in ShortcutsFooter templates.~~

`ctrl+s` is now fully specified in the arch spec: keyboard routing matrix (`BROWSING` → `CONFIRMING` when `unresolvedCollisionCount == 0`, no-op otherwise), header template for the zero-collision case, and readline-conflict note.

---

### ~~12. ctrl+c skip-confirmation state (Frame 1b) is absent from the arch spec~~ (resolved in spec)

~~Frame 1b shows a new CONFIRMING-like state triggered by `ctrl+c`... None of this is described in the arch spec.~~

Frame 1b is now in the arch spec golden-state table as `CONFIRMING EXIT, choice NO, secondCtrlCArmed=true`, with `Skip adding commodities? [y/*N*]` prompt, scroll-only table, `↵ edit mappings` footer, and second `ctrl+c` → SIGINT behaviour.

---

### ~~13. FILTERING mode is deprecated but still present in the arch spec~~ (resolved in spec)

~~Per the updated storyboard, filtering is live within BROWSING mode... The arch spec still has `FILTERING` as an enum value with its own full keyboard routing section.~~

`FILTERING` has been fully removed from the arch spec. Printable character input in `BROWSING` now inserts directly into `filter.text`; `↵` goes to `EDITING`; `esc` clears filter and stays in `BROWSING`.

---

### ~~14. ShortcutsFooter templates don't match storyboard~~ (resolved in spec)

~~All six templates in the arch spec ShortcutsFooter differ from the storyboard.~~

The arch spec footer table now matches the storyboard:
- Browsing, inactive/empty filter: `shift+↑↓ pageup/dn  ·  ↵ edit selected`
- Browsing, active filter with rows: `shift+↑↓ pageup/dn  ·  ↵ edit selected  ·  esc clear filter`
- Browsing, active filter, no rows: `Error: no matching rows  ·  esc clear filter`
- Confirming, choice NO (accept or exit): `↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ edit mappings`
- Confirming accept, choice YES: `↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ submit mappings`
- Confirming exit, choice YES: `↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ skip`

---

### ~~15. `▸` cursor semantics in BROWSING contradict the arch spec~~ (resolved in spec)

~~Arch spec: `selectedIndex: number | null (null when Props.mode is BROWSING or CONFIRMING)`. But Frames 1a, 7b, 7c all show `▸` in BROWSING...~~

The arch spec now states `▸` renders on the BROWSING selected row; `selectedOrdinal` is a non-null tracked value in `BROWSING`. Row cursor semantics are specified in the layout table.

---

### ~~16. Filter hint ghost-text mechanism is unspecified in the arch spec~~ (resolved in spec)

~~Three distinct filter prompt states are visible in the storyboard but none are fully described in the arch spec.~~

The arch spec prompt table now covers all three states:
1. Empty filter, collisions > 0: `Tab to view collisions` with `T` reverse-video and remainder dim
2. Empty filter, collisions = 0: `Type to filter` with `T` reverse-video and remainder dim
3. Metafilter only (`!`): `!Type to filter` with only `T` reverse-video and remainder dim

---

### ~~17. BROWSING `↑↓` row navigation is missing from the ShortcutsFooter~~ (resolved by design)

~~BROWSING footer in all frames shows only `shift+↑↓ pageup/dn`. But transition 7b → 7c uses plain `↑` (no shift) to move `▸` up one row.~~

Plain `↑↓` is intentionally absent from the footer — it is an undocumented power-user shortcut. The keyboard routing matrix specifies the behaviour; the footer template deliberately omits it to keep the hint line minimal.

---

### ~~18. Ordinal column right-aligned one column too far from the left edge~~ (resolved in spec and storyboard)

~~Arch spec §6.3 pinned the ordinal field to columns 4..5 (right-aligned, width 2), placing a two-digit ordinal's tens digit at column 4 — one column right of the header/prompt/footer text, which all indent to column 3. The misalignment was invisible in `frame_1a` because the 15-row frame only shows single-digit ordinals (1–9); it surfaced once `frame_8` rendered ordinals 10/11.~~

§6.3 was rewritten to express the table grid in **relative** terms: the ordinal field's left edge is anchored at column 3, its width `W` is the digit count of the mapping total, and every later column (the `#` heading, collision marker, token, source) is defined relative to the ordinal — so a wider ordinal shifts them all right together rather than columns being pinned at fixed absolute numbers. For the width-2 storyboard the instantiation is `#`/ordinal-units at column 4, collision at 8, token at 9, source at 35; the `#` shifted from column 5 to column 4 alongside the body ordinals. The storyboard ordinal-column note is updated to match. The renderer and the `frame_1a`/`frame_8` goldens render the width-2 instantiation; the canonical, variable-`W` column-position enforcement (regimes `W = 1`, `2`, `3`) remains EPIC-005 TASK-014's responsibility (FR34).

---

### 19. Browsing render model: standard viewport scrolling + partial-window paging (spec reconciled; one code follow-up open)

The arch spec previously described `BROWSING` body rendering with the §8.2 "anchored, anchor-high, no-backfill-above" policy. Taken literally that pins the selected row to the top of the body, so every `↑`/`↓` scrolls the whole list under a stationary cursor — the opposite of the expected list navigation. Per product-owner direction, browsing `↑`/`↓` use **standard viewport scrolling**: the row cursor moves *within* the `scrollOffset` window and the window scrolls only enough to keep the selected row visible.

This created a second question — how is frame 7b (last row alone at the top) reachable? Answer: it is a **page-movement** result, not a row-movement one. The two mechanisms use different bounds:
- Row movement (`↑`/`↓`, §8.3) clamps to `maxFillOffset = max(0, len − bodyCapacity)` and always keeps the window full.
- Page movement (`PgUp`/`PgDn`/`Shift+arrows`, §8.5) clamps to `maxScrollOffset = max(0, len − 1)` and makes the selected row the first visible row, which may render a partially-full window (frame 7b).

Spec reconciled accordingly: §3.4 (clamp now uses `maxScrollOffset` + keep-selected-visible), §8.2 (split into the browsing/confirming scroll-offset window and the editing anchor block), §8.3 (standard keep-visible scrolling within `maxFillOffset`), §8.4 (frame-7b arithmetic), and §8.5 (`maxScrollOffset` page bound). The EPIC-002 TASK-004 AC referencing anchored allocation was reworded.

**Open follow-up (needs its own product-owner-approved task/PR):** TASK-004's shipped browsing `PgUp`/`PgDn` (`reducer._page_selection`, `_clamp_scroll`) clamp `scrollOffset` to `maxFillOffset` (`len − bodyCapacity`), not `maxScrollOffset` (`len − 1`), so browsing page movement does **not** yet reach the partial window the revised §8.5 permits (it lands on the last *full* page, e.g. row 3 of 11 with `bodyCapacity = 9`, rather than the last row alone). This was deliberately left unchanged rather than folded silently into the doc edit, since it alters already-merged behaviour and its page-movement unit/BDD tests. The same `maxScrollOffset` bound must be adopted by EPIC-004's `CONFIRMING` page movement so the 7a→7b transition reproduces.
