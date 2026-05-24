# Gnubeans TUI Implementation Contract

This document is normative for implementing the TUI component described by
`tui_interaction_storyboard.md`. The storyboard is the source of truth. This
contract exists so independent implementation agents can produce the same state,
rendering, and key behavior without rereading the storyboard.

Normative keywords:

- MUST and MUST NOT define required behavior.
- SHOULD defines preferred behavior only where the storyboard leaves room.
- "Frame" refers to the numbered storyboard frame.

## 1. Terms and Coordinate System

| Term | Definition |
|---|---|
| Terminal frame | The TUI redraw area. The canonical storyboard frame is 15 rows by 75 columns. |
| Display row | 1-based terminal row within the frame. |
| Display column | 1-based terminal column within the frame. |
| Mapping | One Beancount target token plus one or more GnuCash source values. |
| Source | A value that can justify or supply a target token, such as `cmdty_id` or `user_symbol`. |
| Default source | The source used to initialize the row's target value before user edits. |
| Source safe value | The Beancount-safe value derived from a source value. |
| Target value | The current Beancount token stored for a mapping. |
| Original target value | The target value computed at initialization; it MUST NOT change after initialization. |
| Collision group | Mappings whose current target values are equal and whose group size is greater than 1. |
| Unresolved collision | A mapping that belongs to a collision group. |
| Prompt line | Display row 2. It contains the filter, editing label, accept-all prompt, or exit prompt. |
| Footer line | The command hint or error line drawn two rows after the final table body line. |

Display-width rules:

- Layout MUST be computed using Unicode display width, not byte length.
- The glyphs `❯`, `▸`, `┃`, `✓`, `✗`, `↑`, `↓`, `↵`, and `·` MUST be treated as width 1.
- The en dash in `A–Z` and the arrow `→` MUST be treated as width 1 in the 15x75 golden render.
- Implementations MUST NOT wrap any line. Text that exceeds the terminal width MUST remain on a
  single logical line and be horizontally scrollable by the terminal emulator.
- ANSI styling MUST NOT count toward display width.

## 2. Root State, Derived View State, and Ownership

All mutable application state MUST be owned by the root/app state. Renderers and
components MUST be pure projections of root state plus derived selectors.

### 2.1 Root State

```typescript
type Mode = "BROWSING" | "EDITING" | "CONFIRMING";
type ConfirmationKind = "NONE" | "NORMAL_SUBMIT" | "ACCEPT_ALL" | "EXIT";
type ConfirmationChoice = "YES" | "NO";
type FocusRegion = "TOKEN_INPUT" | "SOURCE_LIST";

interface AppState {
  mode: Mode;
  mappings: Mapping[];

  filter: FilterState;
  selection: SelectionState;
  edit: EditState | null;
  confirmation: ConfirmationState;

  terminal: TerminalState;
  result: ResultState;
}

interface Mapping {
  id: string;
  ordinal: number;
  sources: Source[];
  defaultSourceId: string;
  originalTargetValue: string;
  targetValue: string;
}

interface Source {
  id: string;
  kind: "cmdty_id" | "user_symbol";
  originalValue: string | null;
  displayValue: string;
  safeValue: string | null;
  isDefault: boolean;
}

interface FilterState {
  raw: string;
  collisionOnly: boolean;
  text: string;
}

interface SelectionState {
  selectedOrdinal: number | null;
  scrollOffset: number;
}

interface EditState {
  mappingId: string;
  buffer: string;
  ghostSourceId: string | null;
  ghostValue: string;
  ghostCursor: number;
  deviatedFromGhost: boolean;
  focusRegion: FocusRegion;
  sourcePointerId: string | null;
  lastExplicitSourcePointerId: string | null;
  validation: ValidationState;
  maxLengthFlashUntil: number | null;
}

interface ValidationState {
  status: "VALID" | "INVALID" | "EMPTY";
  icon: "✓" | "✗" | null;
  errorMessage: string | null;
}

interface ConfirmationState {
  kind: ConfirmationKind;
  choice: ConfirmationChoice;
  acceptAllLastChoice: ConfirmationChoice;
  exitChoice: ConfirmationChoice;
  secondCtrlCArmed: boolean;
}

interface TerminalState {
  width: number;
  height: number;
  frameWidth: number;
  frameHeight: number;
}

interface ResultState {
  status: "RUNNING" | "ACCEPTED" | "SKIPPED" | "CANCELLED" | "SIGINT";
}
```

Ownership rules:

- `confirmation.acceptAllLastChoice` MUST be owned by root state and MUST persist after leaving
  `CONFIRMING`.
- `confirmation.exitChoice` MUST be owned by root state. Its default MUST be `NO`.
- `edit` MUST be `null` outside `EDITING`.
- `visibleRows`, `collisionGroups`, `unresolvedCollisions`, validation display positions, prompt text,
  footer text, and render lines MUST be derived selectors, not mutable component state.
- `selectedOrdinal` MUST identify the selected mapping by stable ordinal, not by visible-row index.
- `scrollOffset` MUST be the zero-based offset into the current derived visible row list.

### 2.2 Source and Sanitization Contract

For the commodity mapping dataset in the storyboard:

| Ordinal | Sources | Original target | Initial target |
|---:|---|---|---|
| 1 | `cmdty_id: "AAPL"`, `user_symbol: "APPLE"` | `APPLE` | `APPLE` |
| 2 | `cmdty_id: "AT&T"` | `AT-T` | `AT-T` |
| 3 | `cmdty_id: "AT-T"` | `AT-T` | `AT-T` |
| 4 | `cmdty_id: "100-F"` | `C100-F` | `C100-F` |
| 5 | `cmdty_id: "GOOGL"` | `GOOGL` | `GOOGL` |
| 6 | `cmdty_id: "MSFT"` | `MSFT` | `MSFT` |
| 7 | `cmdty_id: "NVDA"` | `NVDA` | `NVDA` |
| 8 | `cmdty_id: "SPY"` | `SPY` | `SPY` |
| 9 | `cmdty_id: "QQQ"` | `QQQ` | `QQQ` |
| 10 | `cmdty_id: "VTSAX"` | `VTSAX` | `VTSAX` |
| 11 | `cmdty_id: "VWUSX"` | `VWUSX` | `VWUSX` |

Source display rules:

- A source with `originalValue = null` MUST display as `(not set)`.
- A source whose `safeValue` differs from `originalValue` MUST display as
  `{kind}: "{originalValue}" → "{safeValue}"`.
- A source whose `safeValue` equals `originalValue` MUST display as `{kind}: "{originalValue}"`.
- For source selection and ghost text, `(not set)` MUST have `safeValue = null` and MUST NOT match
  the edit buffer.

Sanitization rules used by this contract:

1. Uppercase the source value.
2. Replace each non-`A-Z`, non-`0-9`, non-`-` character with `-`.
3. Collapse consecutive hyphens to one hyphen.
4. Trim leading and trailing hyphens.
5. If the first character is not `A-Z`, prefix `C`.
6. Truncate to 24 display columns.

## 3. Derived Selectors

### 3.1 Stable Sort

The base display order MUST be stable after initialization:

1. Sort mappings by the safe value of their default source.
2. Break ties by ASCII order of the default source's original value.
3. Break any remaining ties by original ordinal.

The table MUST NOT dynamically reorder when `targetValue` changes during editing. Frame 5 keeps rows
2 and 3 adjacent after row 3 changes to `ATT`.

### 3.2 Collision Groups

Algorithm:

```text
groupByTarget = map targetValue -> mappings whose targetValue is equal
collisionGroups = all groups where size > 1
unresolvedCollisionOrdinals = ordinals from collisionGroups
unresolvedCollisionCount = collisionGroups.length
```

Rendering rules:

- The header count is the number of unresolved collision groups, not the number of rows in those groups.
- A row MUST render `!` when its current `targetValue` belongs to an unresolved collision group.
- During `EDITING`, collision groups MUST be recomputed from the live edit buffer for the edited row.
- Frame 5 requirement: when row 3's live buffer becomes `ATT`, row 2 and row 3 MUST both stop
  rendering `!` immediately because `AT-T` and `ATT` are no longer equal.

### 3.3 Filter Query Parser

The filter is normalized into:

```typescript
interface ParsedFilter {
  collisionOnly: boolean;
  text: string;
}
```

Grammar:

```text
query          ::= metafilter? text
metafilter     ::= "!"
text           ::= any printable characters except control keys
```

Key semantics:

- In `BROWSING`, `Tab` MUST toggle `filter.collisionOnly`.
- In `BROWSING`, `!` MUST toggle `filter.collisionOnly`; it MUST NOT append a literal `!` to
  `filter.text`.
- The prompt MUST render the active metafilter as a leading `!`.
- Backspace and `ctrl+h` MUST delete the last character of `filter.text` when `filter.text` is not
  empty. If `filter.text` is empty and `collisionOnly` is true, they MUST clear `collisionOnly`.
- `Esc` MUST clear both `collisionOnly` and `text` when either is active.

Matching semantics:

- If `collisionOnly` is true, candidate rows MUST first be limited to unresolved collision rows.
- `text` MUST match only the ordinal column and the current Beancount target token.
- `text` MUST NOT match the GnuCash Source column.
- Matching MUST be case-insensitive for ASCII letters.
- Ordinal matching MUST use the decimal ordinal string without left padding. Query `1` matches rows
  `1`, `10`, and `11`.
- Token matching MUST search the full current `targetValue`.
- If `text` is empty, no bold highlight spans are emitted.
- If `text` is non-empty, every non-overlapping matched span in the ordinal and target token display
  MUST be bold.
- Empty results MUST render one blank table body line below the header, clear `selectedOrdinal`, and
  show `Error: no matching rows  ·  esc clear filter`.
- `ctrl+s` in `BROWSING` with empty results MUST still open normal confirmation when collisions are
  zero.

### 3.4 Visible Rows and Selection

Algorithm:

```text
baseRows = stable sorted mappings
visibleRows = baseRows filtered by collisionOnly and text
if visibleRows is empty:
  selectedOrdinal = null
else if selectedOrdinal is null or not in visibleRows:
  selectedOrdinal = first visible row ordinal
scrollOffset = clamp(scrollOffset, 0, max(0, visibleRows.length - bodyCapacity))
if selectedOrdinal is not visible in BROWSING or EDITING:
  scrollOffset = nearest offset that includes selectedOrdinal
```

When a filter change removes the previously selected row, selection MUST clamp to the first visible row.
Frame 2 selects row 2 after applying the collision metafilter. Frame 3 selects row 3 after typing `3`.

## 4. State Machine

### 4.1 Confirmation Variants

There are three distinct confirmation situations:

| Variant | Mode | `confirmation.kind` | Prompt | Default | YES action | NO/Enter action |
|---|---|---|---|---|---|---|
| Normal confirmation | `CONFIRMING` | `NORMAL_SUBMIT` | `Accept all?` | Last accept-all choice | Accept mappings | Return to `BROWSING` |
| Accept-all confirmation on collision resolution | `CONFIRMING` | `ACCEPT_ALL` | `Accept all?` | `YES` on first entry caused by resolving last collision | Accept mappings | Return to `BROWSING` |
| Ctrl+c exit confirmation | `CONFIRMING` | `EXIT` | `Skip adding commodities?` | `NO` | Skip and exit | Return to previous mapping review |

`NORMAL_SUBMIT`, `ACCEPT_ALL`, and `EXIT` MUST be distinguishable in state even when two variants share
the `Accept all?` prompt. `NORMAL_SUBMIT` and `ACCEPT_ALL` share `acceptAllLastChoice`; `EXIT` MUST NOT
share choice state with either. The accept-all choice MUST persist across later normal confirmation
visits. Frame 14 MUST preserve `NO` from frame 7a.

### 4.2 Transition Table

| Current state | Event | Guard | Side effects | Next state |
|---|---|---|---|---|
| `BROWSING` | Printable char | Any | Append char to `filter.text`; parse/filter; clamp selection | `BROWSING` |
| `BROWSING` | `Tab` or `!` | Any | Toggle `filter.collisionOnly`; clamp selection | `BROWSING` |
| `BROWSING` | `Backspace` or `ctrl+h` | Filter active | Delete filter text or clear metafilter; clamp selection | `BROWSING` |
| `BROWSING` | `Esc` | Filter active | Clear filter and metafilter; clamp selection | `BROWSING` |
| `BROWSING` | `↑` / `↓` | `visibleRows` non-empty | Move `selectedOrdinal` by -1/+1 and adjust scroll to keep selected visible | `BROWSING` |
| `BROWSING` | `Shift+↑` / `PgUp` | `visibleRows` non-empty | Page up; selected row becomes first visible row after paging | `BROWSING` |
| `BROWSING` | `Shift+↓` / `PgDn` | `visibleRows` non-empty | Page down; selected row becomes first visible row after paging | `BROWSING` |
| `BROWSING` | `Enter` | `selectedOrdinal != null` | Initialize `edit` for selected row | `EDITING` |
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount == 0` | Enter normal confirmation; set choice to `acceptAllLastChoice` | `CONFIRMING` with `NORMAL_SUBMIT` |
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount > 0` | No state change | `BROWSING` |
| `BROWSING` | `ctrl+c` | Any | Enter exit confirmation; `exitChoice = NO`; `secondCtrlCArmed = true` | `CONFIRMING` with `EXIT` |
| `EDITING` | Printable char | Any | Apply streaming overwrite algorithm; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Backspace` or `ctrl+h` | Any | Delete one buffer char or rewind ghost cursor; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Tab` | Ghost text available | Complete buffer to ghost/source safe value; update pointer; validate | `EDITING` |
| `EDITING` | `↑` / `↓` | Source list non-empty | Move source pointer with wraparound; autofill buffer from pointed source safe value | `EDITING` |
| `EDITING` | `Enter` | Validation `VALID` | Commit buffer to mapping target; clear edit; recompute collisions | `CONFIRMING` with `ACCEPT_ALL` if collisions now zero, else `BROWSING` |
| `EDITING` | `Enter` | Validation not `VALID` | No commit; keep validation error | `EDITING` |
| `EDITING` | `Esc` | Any | Discard buffer; clear edit; restore selection on edited row | `BROWSING` |
| `EDITING` | `ctrl+c` | Any | Discard buffer; clear edit; restore selection on edited row | `BROWSING` |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `y` | Any | `choice = YES`; `acceptAllLastChoice = YES` | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `n` | Any | `choice = NO`; `acceptAllLastChoice = NO` | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `←` / `→` | Any | Toggle choice; persist to `acceptAllLastChoice` | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `↑` / `↓` | Any | Scroll only; no selected row movement | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `Shift+↑` / `PgUp` | Any | Page scroll up only | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `Shift+↓` / `PgDn` | Any | Page scroll down only | Same confirmation kind |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `Enter` | `choice == YES` | Set `result.status = ACCEPTED` | Terminal final state |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `Enter` | `choice == NO` | Leave confirmation; preserve choice; selection becomes first visible row at current scroll | `BROWSING` |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `Esc` | Any | Leave confirmation; preserve choice | `BROWSING` |
| `CONFIRMING NORMAL_SUBMIT` or `ACCEPT_ALL` | `ctrl+c` | Any | Cancel batch, set `result.status = CANCELLED` | Terminal final state |
| `CONFIRMING EXIT` | `y` | Any | `exitChoice = YES` | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `n` | Any | `exitChoice = NO` | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `←` / `→` | Any | Toggle `exitChoice` | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `↑` / `↓` | Any | Scroll only; no selected row movement | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Shift+↑` / `PgUp` | Any | Page scroll up only | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Shift+↓` / `PgDn` | Any | Page scroll down only | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Enter` | `exitChoice == YES` | Set `result.status = SKIPPED` | Terminal final state |
| `CONFIRMING EXIT` | `Enter` | `exitChoice == NO` | Leave exit confirmation | `BROWSING` |
| `CONFIRMING EXIT` | `Esc` | Any | Leave exit confirmation | `BROWSING` |
| `CONFIRMING EXIT` | `ctrl+c` | `secondCtrlCArmed` | Send SIGINT; set `result.status = SIGINT` | Terminal final state |

## 5. Key Handling Matrix

| Key | `BROWSING` | `EDITING` | `CONFIRMING NORMAL_SUBMIT` / `ACCEPT_ALL` | `CONFIRMING EXIT` |
|---|---|---|---|---|
| `↑` | Move selection up | Move source pointer up with wrap | Scroll up | Scroll up |
| `↓` | Move selection down | Move source pointer down with wrap | Scroll down | Scroll down |
| `Shift+↑` / `PgUp` | Page up and select first visible row | No-op | Page scroll up | Page scroll up |
| `Shift+↓` / `PgDn` | Page down and select first visible row | No-op | Page scroll down | Page scroll down |
| `←` | No-op | No-op | Toggle choice | Toggle choice |
| `→` | No-op | No-op | Toggle choice | Toggle choice |
| `Enter` | Edit selected row | Submit only if valid | Confirm if YES, otherwise edit mappings | Skip if YES, otherwise edit mappings |
| `Esc` | Clear active filter, otherwise no-op | Cancel edit | Edit mappings | Edit mappings |
| `Tab` | Toggle collision metafilter | Autocomplete from ghost/source | No-op | No-op |
| `!` | Toggle collision metafilter | Type literal `!` only if validation grammar later permits; currently invalid printable char | No-op | No-op |
| `Backspace` | Delete filter char or metafilter | Delete edit char/rewind ghost | No-op | No-op |
| `ctrl+h` | Same as Backspace | Same as Backspace | No-op | No-op |
| `ctrl+s` | Open normal confirmation if zero collisions | No-op | No-op | No-op |
| `ctrl+c` | Enter exit confirmation | Cancel edit to browsing | Cancel batch | Send SIGINT |
| `y` / `n` | Append to filter | Type into buffer | Set choice | Set choice |
| Other printable | Append to filter | Type into buffer | No-op | No-op |

## 6. Render Layout Contract

### 6.1 Fixed 15x75 Grid

For the canonical 15x75 frame:

| Row | Contents |
|---:|---|
| 1 | Header |
| 2 | Prompt |
| 3 | Blank |
| 4 | Table header |
| 5..N | Table body rows, including expanded edit source rows or a single blank empty-result row |
| N+1 | Blank separator |
| N+2 | Footer |
| Remaining rows through 15 | Blank filler lines cleared on each redraw |

The footer MUST be exactly two rows below the last table body row. When the table body reaches row 13,
the footer is row 15.

### 6.2 Inline Redraw and Clear

- The TUI MUST render inline without entering the alternate screen buffer.
- Each redraw MUST return the cursor to the top of the frame, clear every previously drawn frame line,
  write the new 15-line frame, and leave the cursor after the frame.
- If a later frame uses fewer body lines than a previous frame, the remaining old lines MUST be cleared
  with blank filler lines through row 15.
- The renderer MUST NOT insert extra blank lines above row 1 or between logical rows.

### 6.3 Columns

Columns are 1-based.

| Field | Columns | Contract |
|---|---:|---|
| Header start | 1 | Header begins with `❯`. |
| Prompt indent | 1..2 | Two leading spaces before prompt text. |
| Table header | 1..75 | Exactly `   #   Beancount Token            GnuCash Source`. |
| Row cursor | 1 | `▸` only in `BROWSING` selected row or `EDITING` token input focus. |
| Ordinal | 4..5 | Right-aligned to width 2 for the 11-row storyboard dataset. |
| Collision marker | 8 | `!` when unresolved, otherwise space. |
| Token start | 9 | Current target or edit buffer starts here. |
| Token max display | 9..32 | 24 display columns. |
| Edit cursor at length L | `9 + L` | Reverse-video space. At length 24 this is column 33. |
| Validation icon normal | Cursor column + 2 | `✓` or `✗`, except max-length cap below. |
| Validation icon max cap | 34 | At 24 chars the icon MUST remain at column 34. |
| Source divider | 36 | `┃` in expanded edit rows. |
| Source text | 38 | Source display text begins after divider and one space. |
| Source pointer | 34 | `▸` before the divider when source list has focus or exact match points at that source. |

The storyboard prose calls the max cursor and icon positions "column 32" and "column 33" using a
zero-based mental model. This contract uses 1-based display columns; therefore they correspond to
columns 33 and 34 here.

### 6.4 Header Templates

| Condition | Header |
|---|---|
| `unresolvedCollisionCount > 0`, not exit confirmation | `❯ Reviewing {total} commodity mappings. {count} unresolved collision{plural}. ctrl+c cancel` |
| Exit confirmation | `❯ Reviewing {total} commodity mappings. {count} unresolved collision{plural}. ctrl+c exit` |
| `unresolvedCollisionCount == 0`, `BROWSING` or `EDITING` | `❯ Reviewing {total} commodity mappings. ctrl+s submit  ·  ctrl+c cancel` |
| `unresolvedCollisionCount == 0`, normal or accept-all confirmation | `❯ Reviewing {total} commodity mappings. ctrl+c cancel` |

Shortcut portions in the header MUST be dim. The `❯` glyph SHOULD be bold.

### 6.5 Prompt Templates

| State | Prompt |
|---|---|
| Browsing, no filter, collisions > 0 | `  Filter: Tab to view collisions`, with `T` reverse-video and remainder dim |
| Browsing, no filter, collisions = 0 | `  Filter: Type to filter`, with `T` reverse-video and remainder dim |
| Browsing, metafilter only | `  Filter: !Type to filter`, with only `T` reverse-video and remainder dim |
| Browsing, text filter | `  Filter: {visibleQuery}{cursor}` |
| Editing | `  Editing mapping for "{originalTargetValue}":` |
| Accept-all confirming | `  Accept all? [Y/n]` or `  Accept all? [y/N]`, active choice reverse-video and bold |
| Exit confirming | `  Skip adding commodities? [Y/n]` or `  Skip adding commodities? [y/N]`, active choice reverse-video and bold |

### 6.6 Footer Templates

| State | Footer |
|---|---|
| Browsing, inactive/empty filter | `  shift+↑↓ pageup/dn  ·  ↵ edit selected` |
| Browsing, active filter with rows | `  shift+↑↓ pageup/dn  ·  ↵ edit selected  ·  esc clear filter` |
| Browsing, active filter with no rows | `  Error: no matching rows  ·  esc clear filter` |
| Editing, valid or empty | `  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel` when valid; omit submit when invalid/empty |
| Editing, invalid | `  Error: {message}  ·  ↑↓ select source  ·  esc cancel` |
| Confirming, choice YES | `  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ confirm` |
| Confirming, choice NO | `  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ edit mappings` |

Frame 4 shows no submit affordance while the buffer is still ghost-only/uncommitted. Frames 5, 9, 12a,
and 12b show submit once validation is valid.

## 7. Edit Buffer, Ghost Text, Source Pointer, and Validation

### 7.1 Entering Edit Mode

On `BROWSING Enter`:

1. `edit.mappingId` MUST be the selected mapping.
2. `edit.buffer` MUST be empty.
3. `ghostSourceId` MUST be the source whose `safeValue` equals the mapping's current `targetValue`.
   If multiple sources match, choose the first source in source display order.
4. `ghostValue` MUST be that source's safe value, or the current target value if no source matches.
5. `ghostCursor = 0`, `deviatedFromGhost = false`.
6. `focusRegion = TOKEN_INPUT`.
7. `sourcePointerId` MUST be the exact-match source id if any; otherwise `null`.
8. `lastExplicitSourcePointerId` MUST be the exact-match source id if any; otherwise the first source
   with non-null `safeValue`.

The displayed token input is `buffer + remainingGhost` until deviation. The reverse-video cursor is at
the next ghost character. Frame 4 displays `A` as the cursor and `T-T` as dim ghost text for row 3.

### 7.2 Streaming Overwrite Algorithm

On printable character `ch` in `EDITING`:

```text
if displayWidth(buffer) >= 24:
  discard ch
  set maxLengthFlashUntil
  set error "24 chars max"
  render capped invalid icon
  return

if not deviatedFromGhost and ghostCursor < len(ghostValue) and ch == ghostValue[ghostCursor]:
  buffer += ch
  ghostCursor += 1
else:
  if not deviatedFromGhost:
    deviatedFromGhost = true
    ghostValue = ""
  buffer += ch

updateExactMatchPointer()
validate()
recompute collisions using buffer for edited mapping
```

Deviation behavior:

- The first character that does not equal the next ghost character MUST discard all remaining ghost
  text and append normally.
- After deviation, subsequent printable characters MUST append normally.
- Backspace after deviation MUST remove the last buffer character.
- Backspace before deviation MUST remove the last accepted buffer character and move `ghostCursor`
  back by one. If `buffer` is empty, Backspace MUST do nothing.

Frame 5 requirement: typing `A`, `T`, `T` over ghost `AT-T` produces buffer `ATT`, deviation at the
third character, cursor after `ATT`, validation `✓`, and no collision icons on rows 2 or 3.

### 7.3 Tab Autocomplete

In `EDITING`, `Tab` MUST:

1. If `ghostSourceId` has a non-null safe value, set `buffer` to that full safe value.
2. Set `deviatedFromGhost = true`.
3. Move `sourcePointerId` to the source whose safe value exactly equals `buffer`.
4. Set `lastExplicitSourcePointerId = sourcePointerId` when the pointer is non-null.
5. Set `focusRegion = SOURCE_LIST` when an exact source match exists.
6. Validate.

Frame 12b: from frame 9, `Tab` completes `APPLE` and points at `user_symbol: "APPLE"`.

### 7.4 Source Pointer Movement

The source list order MUST be the order supplied by the mapping. For frame 9, row 1's sources are:

1. `cmdty_id: "AAPL"`
2. `user_symbol: "APPLE"`

Rules:

- `↑` and `↓` in `EDITING` MUST move the source pointer through sources with non-null safe values.
- Movement MUST wrap at the top and bottom.
- Movement MUST set `focusRegion = SOURCE_LIST`.
- Movement MUST autofill `buffer` with the pointed source's safe value.
- Movement MUST set `lastExplicitSourcePointerId` to the pointed source.
- If typed edits produce an exact match with a source safe value, `sourcePointerId` MUST move live to
  that source even when focus remains `TOKEN_INPUT`.
- If typed edits do not exactly match any source safe value, `sourcePointerId` MUST remain on
  `lastExplicitSourcePointerId`.

Frame 12a: `↓` from frame 9 points at `cmdty_id: "AAPL"` and fills `AAPL`.
Frame 12b: `↑` from frame 9 wraps to `user_symbol: "APPLE"` and fills `APPLE`.

### 7.5 Validation

Validation grammar:

```text
TOKEN ::= [A-Z] ([A-Z0-9-]{0,22} [A-Z0-9])?
```

Additional rules:

- Empty buffer with only ghost text MUST be treated as valid if the full displayed ghost value is valid,
  but submit affordance SHOULD be shown only once the displayed value is a concrete buffer value or a
  source/autocomplete selection.
- A concrete buffer MUST be at least 1 character.
- A concrete buffer MUST be at most 24 display columns.
- A concrete buffer MUST start with `A-Z`.
- A concrete buffer MUST contain only `A-Z`, `0-9`, and `-` after the first character.
- A concrete buffer MUST end with `A-Z` or `0-9`.

Display and gating:

- `✓` MUST render for valid concrete input.
- `✗` MUST render for invalid concrete input.
- `Enter` MUST submit only when validation is `VALID`.
- Error precedence MUST be:
  1. `24 chars max`
  2. `must start with A–Z`
  3. `only A–Z, 0–9, and - allowed`
  4. `must end with A–Z or 0–9`
- Frame 10: after typing the first `4`, the footer MUST show `Error: must start with A–Z`; `✗` MUST
  appear two spaces to the right of the reverse-video cursor.
- Frame 11: after the 24th character, the cursor reaches the max token boundary and `✗` MUST render at
  the capped icon column. A 25th character MUST be discarded, flash `✗` at the capped icon column, and
  set transient error `24 chars max`.

## 8. Scrolling and Viewport Rules

### 8.1 Body Capacity

For a 15-row terminal:

- Rows 1 to 4 are fixed header/prompt/blank/table-header.
- The footer must be row `lastBodyRow + 2`.
- Therefore max body rows in a non-editing full page is 9 rows, occupying rows 5 through 13.
- Expanded edit rows consume one body row per rendered mapping/source line.

On terminal resize:

- `frameHeight = max(terminal.height, 1)`.
- The same row allocation algorithm MUST be used with the new height.
- If height is too small to fit all fixed rows and footer, renderer MUST prioritize header, prompt,
  table header, active row, and footer in that order.
- Width changes MUST NOT wrap lines.

### 8.2 Browsing Scrolling

- `↑` and `↓` move selection by one visible row.
- If selection moves above the visible body, decrement `scrollOffset`.
- If selection moves below the visible body, increment `scrollOffset`.
- Movement MUST clamp at first and last visible row.

### 8.3 Confirming Scrolling

- In `CONFIRMING`, no row cursor is shown and no selected row movement occurs.
- `↑` and `↓` adjust `scrollOffset` only.
- `Shift+↑`, `Shift+↓`, `PgUp`, and `PgDn` adjust `scrollOffset` by one page.
- Leaving confirmation with "edit mappings" MUST restore `BROWSING`; selected row MUST become the
  first visible row at the current `scrollOffset`.

This explains frame 7b: after frame 7a scrolls to rows 2..10 and a later page-down/enter exits
confirmation, browsing is at the last page with row 11 selected.

### 8.4 Page Movement

- Page size MUST equal current non-editing body capacity.
- `PgDn`/`Shift+↓` MUST set `scrollOffset = min(scrollOffset + pageSize, maxOffset)`.
- `PgUp`/`Shift+↑` MUST set `scrollOffset = max(scrollOffset - pageSize, 0)`.
- In `BROWSING`, selected row MUST become the first visible row after paging.
- In `CONFIRMING`, selection MUST NOT change.

### 8.5 Keeping Edited Row Visible

- Entering `EDITING` MUST set `scrollOffset` so the edited row and its expanded source lines fit when
  possible.
- If the expanded edit block cannot fit with all currently visible rows, non-selected rows MUST be
  clipped after preserving the edited row, its source lines, separator, and footer.
- The edited row MUST never be scrolled out of view while `EDITING`.

## 9. Collision Resolution Semantics

Collision icons and accept-all transition are derived from live target values:

1. Compute collision groups from current target values, using edit buffer for the edited mapping.
2. Render `!` for each unresolved collision row.
3. On valid edit submit, commit the edit buffer to `mapping.targetValue`.
4. If `unresolvedCollisionCount` becomes zero because of the commit:
   - Enter `CONFIRMING`.
   - Set `confirmation.kind = ACCEPT_ALL`.
   - Set `confirmation.choice = YES`.
   - Set `confirmation.acceptAllLastChoice = YES` only for this first automatic zero-collision entry.
5. Later manual `ctrl+s` entries MUST use `confirmation.kind = NORMAL_SUBMIT` and
   `confirmation.acceptAllLastChoice`.
6. If the user changes accept-all to `NO`, that `NO` MUST persist across later accept-all visits.

Frame 6 is the automatic zero-collision accept-all entry with `Y` selected. Frame 14 is a later normal
confirmation visit with `N` retained from frame 7a.

## 10. Golden-State Acceptance Tests

All golden tests MUST assert app state, visible rows, prompt/footer, and render. Render assertions MUST
strip ANSI for geometry and inspect style spans separately for bold, dim, and reverse-video.

### 10.1 Frame Tests

| Frame | Initial state | Input sequence | Expected app state | Expected visible rows | Expected prompt/footer | Render assertions |
|---|---|---|---|---|---|---|
| 1a | Fresh dataset, rows 2 and 3 collide | None | `BROWSING`, `filter=""`, selected row 1, `scrollOffset=0`, 1 collision group | 1..9 | Prompt ghost `Tab to view collisions`; footer edit selected | Header includes `1 unresolved collision`; row 1 has `▸`; rows 2/3 have `!`; footer row 15 |
| 1b | Frame 1a | `ctrl+c` | `CONFIRMING EXIT`, `exitChoice=NO`, `secondCtrlCArmed=true` | 1..9 | `Skip adding commodities? [y/N]`; footer edit mappings | Header shortcut says `ctrl+c exit`; no row cursor; second `ctrl+c` sends SIGINT |
| 2 | Frame 1a or after exiting 1b | `Tab` or `!` | `BROWSING`, `collisionOnly=true`, selected row 2 | 2,3 | Prompt `!Type to filter`; footer clear filter | Footer row 8; rows 2/3 only; filler clears rows 9..15 |
| 3 | Frame 2 | `3` | `BROWSING`, `collisionOnly=true`, `text="3"`, selected row 3 | 3 | Prompt `!3{cursor}`; footer clear filter | Ordinal `3` bold; no source matching; footer row 7 |
| 4 | Frame 3 | `Backspace`, `↓`, `Enter` | `EDITING` row 3, empty buffer, ghost `AT-T`, token focus | 2 dim, expanded 3 | Editing prompt for `AT-T`; footer no submit | Row 2 super dim; active row shows `▸`, `!`, reverse `A`, dim `T-T`; source rows include `(not set)` |
| 5 | Frame 4 | `A`, `T`, `T` | `EDITING` row 3, buffer `ATT`, valid, collisions zero live | 2 dim, expanded 3 | Footer includes submit | Rows 2/3 have no `!`; active row shows `ATT`, cursor, `✓` |
| 6 | Frame 5 | `Enter` | `CONFIRMING ACCEPT_ALL`, choice `YES`, `scrollOffset=0`, collisions zero | 1..9 | `Accept all? [Y/n]`; footer confirm | Header omits collision count; no cursor; row 3 target `ATT` |
| 7a | Frame 6 | `n`, `↓` or `↓`, `n` | `CONFIRMING ACCEPT_ALL`, choice `NO`, `acceptAllLastChoice=NO`, `scrollOffset=1` | 2..10 | `Accept all? [y/N]`; footer edit mappings | No cursor; first visible row is 2; row 10 visible |
| 7b | Frame 7a | `Shift+↓`, `Enter` | `BROWSING`, collisions zero, selected row 11, last choice `NO` | 11 | Filter ghost `Type to filter`; footer edit selected | Header includes `ctrl+s submit`; row 11 has `▸`; footer row 7 |
| 7c | Frame 7b | `↑` | `BROWSING`, selected row 10, last page visible | 10,11 | Filter ghost `Type to filter`; footer edit selected | Row 10 has `▸`; row 11 follows; footer row 8 |
| 8 | Frame 7c | `1` | `BROWSING`, `text="1"`, selected row 1 | 1,4,10,11 | Prompt `1{cursor}`; footer clear filter | Bold matches on ordinals 1/10/11 and token `C100-F`; source `100-F` is not matched |
| 9 | Frame 8 | `Enter` | `EDITING` row 1, empty buffer, ghost `APPLE`, token focus | Expanded 1, dim 4/10/11 | Editing prompt for `APPLE`; footer submit | Active row shows reverse `A` and dim `PPLE`; source rows `AAPL`, `APPLE`; dim inactive rows |
| 10 | Frame 9 | `4`, `4`, `P`, `L` | `EDITING` row 1, buffer `44PL`, invalid | Expanded 1, dim 4/10/11 | Error `must start with A–Z`; no submit | `✗` two spaces after cursor; footer row 11; source pointer retained |
| 11 | Frame 10 | Type `56789012345678901234` | `EDITING` row 1, 24-char buffer, invalid, max error active | Expanded 1, dim 4/10/11 | Error `24 chars max`; no submit | Cursor at max boundary; `✗` at capped icon column; 25th char discarded in separate assertion |
| 12a | Frame 9 or 10/11 | `↓` | `EDITING`, buffer `AAPL`, valid, source focus first source | Expanded 1, dim 4/10/11 | Footer submit | Row-level cursor absent; source pointer at first source; `✓` shown |
| 12b | Frame 9 or 10/11 | `Tab` or `↑` | `EDITING`, buffer `APPLE`, valid, pointer second source | Expanded 1, dim 4/10/11 | Footer submit | Source pointer line 2; exact-match live pointer tracks `APPLE` |
| 13 | Frame 12b | `Enter` or `Esc`, then `2` after existing filter `1` | `BROWSING`, `text="12"`, selected null | Empty result | Error no matching rows | Blank body row under header; no cursor; footer row 7 |
| 14 | Frame 13 | `ctrl+s` | `CONFIRMING NORMAL_SUBMIT`, choice `NO`, collisions zero | 1..9 | `Accept all? [y/N]`; footer edit mappings | Accept-all `NO` retained; filter does not constrain confirming table |

### 10.2 Defect-Prevention Tests

| Issue from checklist | Required test |
|---|---|
| Distinct confirmation intents missing | Assert frame 1b uses `kind=EXIT`, prompt `Skip adding commodities?`, default `NO`, and `YES` result `SKIPPED`; frame 6 uses `kind=ACCEPT_ALL`; frame 14 uses `kind=NORMAL_SUBMIT`; both accept prompts use `YES` result `ACCEPTED`. |
| `acceptAllConfirm` contradictory ownership | Mutate accept-all choice to `NO`, leave confirmation, re-enter via `ctrl+s`, and assert root `confirmation.acceptAllLastChoice=NO` drives prompt. No renderer/component local state may override it. |
| `ctrl+c` dispatcher absent | Assert `ctrl+c` in `BROWSING` enters exit confirmation, in `EDITING` cancels edit, in `NORMAL_SUBMIT`/`ACCEPT_ALL` cancels batch, and second `ctrl+c` in `EXIT` emits SIGINT. |
| Filtering underspecified | Assert Tab and `!` both toggle collision metafilter; query text matches ordinal/token only; source text does not match; empty results clear selection; `ctrl+s` still opens normal confirmation with zero collisions. |
| Edit input append contradiction | Assert frame 4 to 5 streaming overwrite produces `ATT`, not `AT-TATT` or `ATTT`; deviation discards remaining ghost. |
| Lossy domain model | Unit-test collision groups, source safe values, original target, current target, default source, and live edited target as separate fields. |
| Missing sorting rules | Change row 3 target to `ATT`; assert order remains row 2 then row 3 and does not resort by new target. |
| Layout not deterministic | Golden-render all frames at 15x75; assert row numbers for header, prompt, table header, footer, blank filler, and no alternate screen sequences. |
| Validation incomplete | Assert grammar cases, `✓`/`✗`, submit gating, 24th-character cap, and 25th-character discard/flash. |
| Source selection incomplete | Assert up/down wrap, autofill, Tab autocomplete, exact-match live pointer, and last explicit pointer retention when no exact match exists. |

## 11. Non-Goals, Assumptions, and Unresolved Questions

### 11.1 Non-Goals

- This contract does not define color values.
- This contract does not define mouse behavior.
- This contract does not define alternate datasets beyond the fields and algorithms above.
- This contract does not define persistence format after `ACCEPTED`, `SKIPPED`, `CANCELLED`, or `SIGINT`.
- This contract does not require a specific terminal library.

### 11.2 Assumptions

- ASCII case-insensitive filtering is required, although the storyboard does not demonstrate lowercase input.
- `ctrl+c` in `EDITING` is treated as edit cancel because the storyboard header says `ctrl+c cancel`; the
  storyboard does not show an edit-mode `ctrl+c` frame.
- `ctrl+c` in normal/accept-all confirmation cancels the batch because the header says `ctrl+c cancel`;
  the storyboard only explicitly defines second `ctrl+c` SIGINT for exit confirmation.
- Leaving accept-all confirmation with `NO` selects the first visible row at the current scroll offset.
  This is inferred from frames 7a to 7b.
- Frame 13 keeps the prior text filter `1` and appends `2`, yielding `12`; the storyboard does not show
  the full intermediate path from frame 12b to frame 13.

### 11.3 Unresolved Questions

- The storyboard does not define readline shortcuts other than Backspace and `ctrl+h`.
- The storyboard does not define whether `Shift+↑`/`Shift+↓` are distinguishable from normal arrows in
  all terminal environments; implementations may map `PgUp`/`PgDn` as the reliable page equivalents.
- The storyboard does not define exact timing for max-length error fade. Tests SHOULD assert immediate
  behavior only unless a timer is explicitly specified later.
- The storyboard does not define behavior for printable invalid characters such as `!` in edit mode
  beyond validation failure.
