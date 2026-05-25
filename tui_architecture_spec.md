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
| Mapping | One target token plus one or more source values. |
| Source | A value that can justify or supply a target token. Source labels are data/configuration values, not a fixed enum. |
| Default source | The source used to initialize the row's target value before user edits. |
| Source effective value | The value used by the TUI for matching and autofill: `sanitizedValue ?? originalValue`. |
| Target value | The literal override stored on a mapping, or null when the row uses the default source value. |
| Original target value | The target value computed at initialization; it MUST NOT change after initialization. |
| Collision group | Mappings whose derived `currentTargetValue` values are equal and whose group size is greater than 1. |
| Unresolved collision | A mapping that belongs to a collision group. |
| Prompt line | Display row 2. It contains the filter, editing label, accept prompt, or exit prompt. |
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
type ConfirmationKind = "NONE" | "ACCEPT" | "EXIT";
type ConfirmationChoice = "YES" | "NO";
type FocusRegion = "TOKEN_INPUT" | "SOURCE_LIST";

interface AppState {
  config: AppConfig;
  mode: Mode;
  mappings: Mapping[];

  filter: FilterState;
  selection: SelectionState;
  edit: EditState | null;
  confirmation: ConfirmationState;

  terminal: TerminalState;
  result: ResultState;
}

type SourceLabel = string;

interface AppConfig {
  entityNameSingular: string;
  entityNamePlural: string;
  mappingNounSingular: string;
  mappingNounPlural: string;
  targetColumnLabel: string;
  sourceColumnLabel: string;
  acceptPrompt: string;
  exitPrompt: string;
  createdMessage: (count: number) => string;
  sourceLabels: SourceLabel[];
}

interface Mapping {
  ordinal: number;
  sources: Source[];
  defaultSourceLabel: SourceLabel;
  targetValue: string | null;
}

interface Source {
  label: SourceLabel;
  originalValue: string | null;
  sanitizedValue: string | null;
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
  mappingOrdinal: number;
  buffer: string;
  focusRegion: FocusRegion;
  sourcePointerIndex: number | null;
  sourceEntryBuffer: string | null;
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

- `confirmation.choice` MUST be owned by root state and MUST be reset to `NO` every time the app enters
  `CONFIRMING`, regardless of confirmation kind.
- `edit` MUST be `null` outside `EDITING`.
- `visibleRows`, `collisionGroups`, `unresolvedCollisions`, validation display positions, prompt text,
  footer text, and render lines MUST be derived selectors, not mutable component state.
- `config` MUST be root-owned immutable input for a TUI session. Renderers MUST NOT hard-code entity
  nouns, mapping nouns, column labels, source labels, accept prompt text, exit prompt text, or created
  output text.
- `selectedOrdinal` MUST identify the selected mapping by stable ordinal, not by visible-row index.
- `scrollOffset` MUST be the zero-based offset into the current derived visible row list.
- `defaultSourceValue`, `currentTargetValue`, and source `effectiveValue` MUST be derived selectors,
  not stored fields.
- Edit ghost text MUST be derived from `targetValue`, `defaultSourceValue`, and `edit.buffer`, not
  stored in `EditState`.

Derived entity selectors:

```text
source.effectiveValue = source.sanitizedValue ?? source.originalValue
mapping.defaultSource = the only source where source.label == mapping.defaultSourceLabel
mapping.defaultSourceValue = mapping.defaultSource.effectiveValue
mapping.currentTargetValue = mapping.targetValue ?? mapping.defaultSourceValue
mapping.activeSources = sources where source.effectiveValue is not null, in source display order
edit.ghostSuffix =
  if mapping.targetValue == null and edit.buffer is a prefix of mapping.defaultSourceValue:
    mapping.defaultSourceValue without the edit.buffer prefix
  else:
    ""
edit.renderedValue = edit.buffer + edit.ghostSuffix
edit.concreteValue =
  if edit.buffer is non-empty:
    edit.buffer
  else if mapping.targetValue == null:
    mapping.defaultSourceValue
  else:
    mapping.targetValue
```

Entity invariants:

- A mapping MUST contain at most one source for each `SourceLabel`.
- `config.sourceLabels` MUST define the allowed labels and display order for sources.
- Every `Source.label` and `Mapping.defaultSourceLabel` MUST be present in `config.sourceLabels`.
- `defaultSourceLabel` MUST refer to an existing source whose `effectiveValue` is not null.
- `targetValue = null` means the mapping has no explicit override and uses `defaultSourceValue`.
- Committing an edit whose submitted value equals `defaultSourceValue` MUST still store the literal
  string in `targetValue`; implementations MUST NOT canonicalize it back to null.

### 2.2 Storyboard Fixture Configuration

The storyboard uses this concrete configuration:

```typescript
const storyboardConfig: AppConfig = {
  entityNameSingular: "commodity",
  entityNamePlural: "commodities",
  mappingNounSingular: "mapping",
  mappingNounPlural: "mappings",
  targetColumnLabel: "Beancount Token",
  sourceColumnLabel: "GnuCash Source",
  acceptPrompt: "Accept all?",
  exitPrompt: "Skip adding commodities?",
  createdMessage: (count) => `${count} commodities created.`,
  sourceLabels: ["cmdty_id", "user_symbol"],
};
```

Implementations MUST support equivalent configurations for other entity types and source labels without
changing the state machine, render pipeline, or key handling.

### 2.3 Source and Sanitization Contract

For the storyboard fixture dataset:

| Ordinal | Sources | Default source value | Initial current target |
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
- A source whose `sanitizedValue` is non-null and differs from `originalValue` MUST display as
  `{label}: "{originalValue}" → "{sanitizedValue}"`.
- A source whose `sanitizedValue` is null or equals `originalValue` MUST display as
  `{label}: "{originalValue}"`.
- For source selection and ghost text, `(not set)` MUST have `effectiveValue = null` and MUST NOT match
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

1. Sort mappings by `defaultSourceValue`.
2. Break ties by ASCII order of the default source's original value.
3. Break any remaining ties by original ordinal.

The table MUST NOT dynamically reorder when `targetValue` or `currentTargetValue` changes during
editing. Frame 5 keeps rows 2 and 3 adjacent after row 3 changes to `ATT`.

### 3.2 Collision Groups

Algorithm:

```text
groupByTarget = map currentTargetValue -> mappings whose currentTargetValue is equal
collisionGroups = all groups where size > 1
unresolvedCollisionOrdinals = ordinals from collisionGroups
unresolvedCollisionCount = collisionGroups.length
```

Rendering rules:

- The header count is the number of unresolved collision groups, not the number of rows in those groups.
- A row MUST render `!` when its `currentTargetValue` belongs to an unresolved collision group.
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
- `text` MUST match only the ordinal column and the current target token (`config.targetColumnLabel`).
- The filter matcher MUST NOT compare `text` with `config.sourceColumnLabel`, any `Source.label`, or
  any source display/effective/original/sanitized value.
- Matching MUST be case-insensitive for ASCII letters.
- Ordinal matching MUST use the decimal ordinal string without left padding. Query `1` matches rows
  `1`, `10`, and `11`.
- Token matching MUST search the full `currentTargetValue`.
- If `text` is empty, no bold highlight spans are emitted.
- If `text` is non-empty, every non-overlapping matched span in the ordinal and target token display
  MUST be bold.
- Empty results MUST render one blank table body line below the header, clear `selectedOrdinal`, and
  show `Error: no matching rows  ·  esc clear filter`.
- `ctrl+s` in `BROWSING` with empty results MUST still open accept confirmation when collisions are
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
```

When a filter change removes the previously selected row, selection MUST clamp to the first visible row.
Frame 2 selects row 2 after applying the collision metafilter. Frame 3 selects row 3 after typing `3`.

## 4. State Machine

### 4.1 Confirmation Variants

There are two distinct confirmation situations:

| Variant | Mode | `confirmation.kind` | Prompt | Default | YES action | NO/Enter action |
|---|---|---|---|---|---|---|
| Accept confirmation | `CONFIRMING` | `ACCEPT` | `config.acceptPrompt` | `NO` | Accept mappings and render completion output | Return to `BROWSING` |
| Ctrl+c exit confirmation | `CONFIRMING` | `EXIT` | `config.exitPrompt` | `NO` | Skip and exit | Return to previous mapping review |

The storyboard no longer distinguishes a normal submit confirmation from an automatic last-collision
accept confirmation. Both entry paths MUST use `confirmation.kind = ACCEPT`. Every y/n confirmation
prompt MUST default to `NO` when shown; the app MUST NOT remember a previous boolean choice between
confirmation visits.

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
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount == 0` | Enter accept confirmation; set `choice = NO` | `CONFIRMING` with `ACCEPT` |
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount > 0` | No state change | `BROWSING` |
| `BROWSING` | `ctrl+c` | Any | Enter exit confirmation; set `choice = NO`; `secondCtrlCArmed = true` | `CONFIRMING` with `EXIT` |
| `EDITING` | Printable char | Any | Apply streaming overwrite algorithm; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Backspace` or `ctrl+h` | Any | Return to token input if needed; delete one buffer char; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Tab` | Ghost suffix available | Complete buffer to displayed value; clear source navigation; validate | `EDITING` |
| `EDITING` | `↑` / `↓` | Source list non-empty | Enter, move within, or exit reversible source navigation | `EDITING` |
| `EDITING` | `Enter` | Validation `VALID` | Commit displayed edit value to mapping target; clear edit; recompute collisions | `CONFIRMING` with `ACCEPT` if collisions now zero, else `BROWSING` |
| `EDITING` | `Enter` | Validation not `VALID` | No commit; keep validation error | `EDITING` |
| `EDITING` | `Esc` | Any | Discard buffer; clear edit; restore selection on edited row | `BROWSING` |
| `EDITING` | `ctrl+c` | Any | Discard buffer; clear edit; restore selection on edited row | `BROWSING` |
| `CONFIRMING ACCEPT` | `y` | Any | `choice = YES` | Same confirmation kind |
| `CONFIRMING ACCEPT` | `n` | Any | `choice = NO` | Same confirmation kind |
| `CONFIRMING ACCEPT` | `←` / `→` | Any | Toggle choice | Same confirmation kind |
| `CONFIRMING ACCEPT` | `↑` / `↓` | Any | Scroll only; no selected row movement | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Shift+↑` / `PgUp` | Any | Page scroll up only | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Shift+↓` / `PgDn` | Any | Page scroll down only | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Enter` | `choice == YES` | Set `result.status = ACCEPTED` | Terminal final state |
| `CONFIRMING ACCEPT` | `Enter` | `choice == NO` | Leave confirmation; selection becomes first visible row at current scroll | `BROWSING` |
| `CONFIRMING ACCEPT` | `Esc` | Any | Leave confirmation | `BROWSING` |
| `CONFIRMING ACCEPT` | `ctrl+c` | Any | Cancel batch, set `result.status = CANCELLED` | Terminal final state |
| `CONFIRMING EXIT` | `y` | Any | `choice = YES` | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `n` | Any | `choice = NO` | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `←` / `→` | Any | Toggle choice | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `↑` / `↓` | Any | Scroll only; no selected row movement | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Shift+↑` / `PgUp` | Any | Page scroll up only | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Shift+↓` / `PgDn` | Any | Page scroll down only | `CONFIRMING EXIT` |
| `CONFIRMING EXIT` | `Enter` | `choice == YES` | Set `result.status = SKIPPED` | Terminal final state |
| `CONFIRMING EXIT` | `Enter` | `choice == NO` | Leave exit confirmation | `BROWSING` |
| `CONFIRMING EXIT` | `Esc` | Any | Leave exit confirmation | `BROWSING` |
| `CONFIRMING EXIT` | `ctrl+c` | `secondCtrlCArmed` | Send SIGINT; set `result.status = SIGINT` | Terminal final state |

## 5. Key Handling Matrix

| Key | `BROWSING` | `EDITING` | `CONFIRMING ACCEPT` | `CONFIRMING EXIT` |
|---|---|---|---|---|
| `↑` | Move selection up | Move source pointer up with wrap | Scroll up | Scroll up |
| `↓` | Move selection down | Move source pointer down with wrap | Scroll down | Scroll down |
| `Shift+↑` / `PgUp` | Page up and select first visible row | No-op | Page scroll up | Page scroll up |
| `Shift+↓` / `PgDn` | Page down and select first visible row | No-op | Page scroll down | Page scroll down |
| `←` | No-op | No-op | Toggle choice | Toggle choice |
| `→` | No-op | No-op | Toggle choice | Toggle choice |
| `Enter` | Edit selected row | Submit only if valid | Confirm if YES, otherwise edit mappings | Skip if YES, otherwise edit mappings |
| `Esc` | Clear active filter, otherwise no-op | Cancel edit | Edit mappings | Edit mappings |
| `Tab` | Toggle collision metafilter | Complete ghost text in token input | No-op | No-op |
| `!` | Toggle collision metafilter | Type literal `!` only if validation grammar later permits; currently invalid printable char | No-op | No-op |
| `Backspace` | Delete filter char or metafilter | Return to token input if needed, then delete edit char | No-op | No-op |
| `ctrl+h` | Same as Backspace | Same as Backspace | No-op | No-op |
| `ctrl+s` | Open accept confirmation if zero collisions | No-op | No-op | No-op |
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

When the footer separator is visible, the footer MUST be exactly two rows below the last rendered table
body row. When the footer separator is collapsed, the footer MUST be exactly one row below the last
rendered table body row. When the table body reaches row 13 in the canonical 15-row frame, the footer
is row 15.

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
| Table header | 1..75 | `   #   {targetColumnLabel}{padding}{sourceColumnLabel}`. For the storyboard config this is exactly `   #   Beancount Token            GnuCash Source`. |
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
| `unresolvedCollisionCount > 0`, not exit confirmation | `❯ Reviewing {total} {entityNameSingular} {mappingNounPlural}. {count} unresolved collision{plural}. ctrl+c cancel` |
| Exit confirmation | `❯ Reviewing {total} {entityNameSingular} {mappingNounPlural}. {count} unresolved collision{plural}. ctrl+c exit` |
| `unresolvedCollisionCount == 0`, `BROWSING` or `EDITING` | `❯ Reviewing {total} {entityNameSingular} {mappingNounPlural}. ctrl+s submit  ·  ctrl+c cancel` |
| `unresolvedCollisionCount == 0`, accept confirmation | `❯ Reviewing {total} {entityNameSingular} {mappingNounPlural}. ctrl+c cancel` |

Shortcut portions in the header MUST be dim. The `❯` glyph SHOULD be bold.

### 6.5 Prompt Templates

| State | Prompt |
|---|---|
| Browsing, no filter, collisions > 0 | `  Filter: Tab to view collisions`, with `T` reverse-video and remainder dim |
| Browsing, no filter, collisions = 0 | `  Filter: Type to filter`, with `T` reverse-video and remainder dim |
| Browsing, metafilter only | `  Filter: !Type to filter`, with only `T` reverse-video and remainder dim |
| Browsing, text filter | `  Filter: {visibleQuery}{cursor}` |
| Editing | `  Editing mapping for "{defaultSourceValue}":` |
| Accept confirming | `  {acceptPrompt} [Y/n]` or `  {acceptPrompt} [y/N]`, active choice reverse-video and bold |
| Exit confirming | `  {exitPrompt} [Y/n]` or `  {exitPrompt} [y/N]`, active choice reverse-video and bold |

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

Frame 6 is a storyboard-specific render case: it enters `CONFIRMING ACCEPT` with `NO` selected but
still renders the footer text `↵ confirm`. This footer text MUST be preserved for frame-accurate
rendering; the `Enter` key behavior MUST still follow `choice == NO` and return to `BROWSING`.

Frame 4 shows no submit affordance while the buffer is still ghost-only/uncommitted. Frames 5, 9, 12a,
and 12b show submit once validation is valid.

### 6.7 Terminal Result Frame

When `result.status = ACCEPTED`, the TUI MUST render the final inline frame shown in storyboard frame
15:

- Row 1 MUST be `config.createdMessage(total)`. For the storyboard config and 11-row dataset this is
  `11 commodities created.`
- Row 2 MUST be `❯`.
- Rows 3 through 15 MUST be blank/cleared.
- The alternate screen buffer MUST NOT be used.

## 7. Edit Buffer, Ghost Text, Source Pointer, and Validation

### 7.1 Entering Edit Mode

On `BROWSING Enter`:

1. `edit.mappingOrdinal` MUST be the selected mapping ordinal.
2. If `mapping.targetValue === null`:
   - `edit.buffer` MUST be empty.
3. If `mapping.targetValue !== null`:
   - `edit.buffer` MUST be the literal `mapping.targetValue`.
4. `focusRegion = TOKEN_INPUT`.
5. `sourcePointerIndex = null`.
6. `sourceEntryBuffer = null`.

Ghost text is derived, not stored. When `mapping.targetValue === null` and `edit.buffer` is a prefix of
`mapping.defaultSourceValue`, the input line MUST display the remaining suffix of `defaultSourceValue`
as ghost text. When `mapping.targetValue !== null`, no ghost text MUST render even if the literal
`targetValue` is a prefix of `defaultSourceValue`.

The reverse-video cursor MUST cover the next ghost character when ghost text is active, or a space after
the buffer when no ghost text is active. Frame 4 displays `A` as the cursor and `T-T` as dim ghost text
for row 3 because its `targetValue` is null. Frame 9 displays `APPLE` as ghost text when row 1's
`targetValue` is null. If row 1 later has literal `targetValue = "APPL"`, re-entering edit mode MUST
display `APPL` with the cursor after `L` and no ghost `E`.

`ghostValue`, `ghostCursor`, and `ghostSourceLabel` MUST NOT be stored in `EditState`; all three are
derivable from the selected mapping and `edit.buffer`.

### 7.2 Streaming Overwrite Algorithm

On printable character `ch` in `EDITING`:

```text
if focusRegion == SOURCE_LIST:
  focusRegion = TOKEN_INPUT
  sourcePointerIndex = null
  sourceEntryBuffer = null

if displayWidth(buffer) >= 24:
  discard ch
  set maxLengthFlashUntil
  set error "24 chars max"
  render capped invalid icon
  return

buffer += ch
validate()
recompute collisions using buffer for edited mapping
```

Ghost behavior:

- Typing a character that keeps `buffer` as a prefix of `defaultSourceValue` MUST continue rendering
  the remaining suffix as ghost text when `targetValue` is null.
- Typing a character that makes `buffer` no longer a prefix of `defaultSourceValue` MUST make
  `edit.ghostSuffix` derive to empty; no separate deviation flag is stored.
- If later Backspace returns `buffer` to a prefix of `defaultSourceValue` while `targetValue` is null,
  ghost text MUST reappear.
- Backspace MUST delete the last buffer character when `buffer` is non-empty.
- If Backspace is pressed while `focusRegion = SOURCE_LIST`, the pointer MUST first return to
  `TOKEN_INPUT`, clear `sourcePointerIndex`, clear `sourceEntryBuffer`, and then delete one buffer
  character from the current autofilled buffer.
- If `buffer` is empty, Backspace MUST do nothing.

Frame 5 requirement: typing `A`, `T`, `T` over ghost `AT-T` produces buffer `ATT`; the third character
makes `buffer` no longer a prefix of `defaultSourceValue`, so ghost text disappears, the cursor appears
after `ATT`, validation is `✓`, and rows 2 and 3 have no collision icons.

Frame 12b backspace requirement: from source-list focus with buffer `APPLE`, Backspace MUST return focus
to `TOKEN_INPUT`, clear `sourcePointerIndex`, clear `sourceEntryBuffer`, delete the final `E`, and
render `APPL` plus ghost `E` as `APPL*E*` because the mapping's `targetValue` is still null.

### 7.3 Tab Autocomplete

In `EDITING`, `Tab` MUST:

1. If `edit.ghostSuffix` is non-empty, set `buffer` to `edit.renderedValue`.
2. Clear `sourcePointerIndex`.
3. Clear `sourceEntryBuffer`.
4. Set `focusRegion = TOKEN_INPUT`.
5. Validate.

Frame 12b remains reachable by `↑` from frame 9. `Tab` from frame 9 completes `APPLE` in the token
input but MUST NOT place the source pointer beside `user_symbol: "APPLE"`.

### 7.4 Source Pointer Movement

The source list order MUST be the order supplied by the mapping. For frame 9, row 1's sources are:

1. `cmdty_id: "AAPL"`
2. `user_symbol: "APPLE"`

Rules:

- `sourcePointerIndex` indexes `mapping.activeSources`, not the raw source array.
- `sourceEntryBuffer` stores the buffer value from immediately before focus switched from
  `TOKEN_INPUT` to `SOURCE_LIST`.
- `sourceEntryBuffer` MUST be null while `focusRegion = TOKEN_INPUT`.
- When `focusRegion = TOKEN_INPUT`, `↓` MUST:
  - Set `sourceEntryBuffer = buffer`.
  - Set `sourcePointerIndex = 0`.
  - Set `buffer = activeSources[0].effectiveValue`.
  - Set `focusRegion = SOURCE_LIST`.
- When `focusRegion = TOKEN_INPUT`, `↑` MUST:
  - Set `sourceEntryBuffer = buffer`.
  - Set `sourcePointerIndex = activeSources.length - 1`.
  - Set `buffer = activeSources[sourcePointerIndex].effectiveValue`.
  - Set `focusRegion = SOURCE_LIST`.
- When `focusRegion = SOURCE_LIST` and `↑` is pressed while `sourcePointerIndex == 0`, the cursor has
  moved above the first source. The implementation MUST restore `buffer = sourceEntryBuffer`, clear
  `sourcePointerIndex`, clear `sourceEntryBuffer`, and set `focusRegion = TOKEN_INPUT`.
- When `focusRegion = SOURCE_LIST` and `↓` is pressed while
  `sourcePointerIndex == activeSources.length - 1`, the cursor has moved below the last source. The
  implementation MUST restore `buffer = sourceEntryBuffer`, clear `sourcePointerIndex`, clear
  `sourceEntryBuffer`, and set `focusRegion = TOKEN_INPUT`.
- When `focusRegion = SOURCE_LIST` and movement remains within the list, `↑` and `↓` MUST move
  `sourcePointerIndex` by -1 or +1.
- Movement MUST set `focusRegion = SOURCE_LIST`.
- Movement MUST autofill `buffer` with the pointed source's `effectiveValue`.
- Printable typing, Backspace, and `ctrl+h` while `focusRegion = SOURCE_LIST` MUST exit source-list
  navigation, clear `sourcePointerIndex`, and clear `sourceEntryBuffer` before applying the edit.
- Exact matches between `buffer` and a source `effectiveValue` MUST NOT create or move
  `sourcePointerIndex` while `focusRegion = TOKEN_INPUT`.

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

`bodyCapacity` MUST be a derived selector from the current terminal height and the current mode's
minimum body requirement:

```text
fixedRowsBeforeBody = 4  // header, prompt, blank separator, table header
footerRows = 1
preferredFooterSeparatorRows = 1

if mode == EDITING:
  minimumBodyRows = activeSources.length
else if mode == BROWSING and selectedOrdinal != null:
  minimumBodyRows = 1
else:
  minimumBodyRows = 0

bodyCapacityWithFooterSeparator =
  max(0, terminal.height - fixedRowsBeforeBody - preferredFooterSeparatorRows - footerRows)
bodyCapacityWithoutFooterSeparator =
  max(0, terminal.height - fixedRowsBeforeBody - footerRows)

footerSeparatorVisible =
  terminal.height >= fixedRowsBeforeBody + preferredFooterSeparatorRows + footerRows
  and bodyCapacityWithFooterSeparator >= minimumBodyRows

bodyCapacity =
  bodyCapacityWithFooterSeparator if footerSeparatorVisible
  else bodyCapacityWithoutFooterSeparator
```

For a 15-row terminal, `bodyCapacity = 15 - 4 - 1 - 1 = 9`; the table body occupies rows 5
through 13. Expanded edit rows consume one body row per rendered mapping/source line.

The blank separator above the footer is optional. It MUST render when the preferred layout leaves
enough body capacity for the current mode's minimum body requirement. It MUST collapse when collapsing
it is necessary to fit the minimum body rows. If even the collapsed layout cannot fit the minimum body
rows, the table body renders only `bodyCapacity` rows and the mode-specific too-small behavior applies.

On terminal resize:

- `frameHeight = max(terminal.height, 1)`.
- `bodyCapacity` and `footerSeparatorVisible` MUST be recomputed from the new `terminal.height`.
- The same row allocation algorithm MUST be used with the new height and recomputed `bodyCapacity`.
- If height is too small to fit the fixed prefix rows and footer, renderer MUST truncate from the
  bottom after preserving as much as possible of this order: header, prompt, blank separator, table
  header, footer. Body rows render only when `bodyCapacity > 0`.
- Width changes MUST NOT wrap lines.

### 8.2 Anchored Table Body Allocation

`BROWSING` and `EDITING` MUST render the table body around a non-optional anchor block. Context rows
before and after the anchor are optional and MUST be allocated deterministically.

Anchor definitions:

```text
if mode == BROWSING:
  anchorBlock = [selected mapping row]
if mode == EDITING:
  anchorBlock = expanded edit display rows for selectedOrdinal
  anchorBlock.length = max(1, activeSources.length)
```

In `EDITING`, the active mapping/input row and the first source row share one display row. Each
remaining source consumes one additional display row. The edit anchor therefore contains all
non-optional edit display rows, not `1 + activeSources.length` rows.

`CONFIRMING` has no selected anchor; it uses `scrollOffset` as a normal list window.

When `bodyCapacity >= anchorBlock.length`, allocate table body rows using an anchor-high, fill-below-first
policy:

```text
anchorIndex = index of selectedOrdinal within visibleRows
contextAfter = visibleRows after anchorIndex
contextCapacity = bodyCapacity - anchorBlock.length

afterCount = min(contextAfter.length, contextCapacity)

visibleBody =
  anchorBlock
  + head(contextAfter, afterCount)
```

This keeps the anchor block as high as possible while preserving nearby following context first. It also
means a page may render fewer than `bodyCapacity` rows when the selected or edited row is near the end
of `visibleRows`; implementations MUST NOT backfill preceding rows above the anchor in this policy.

When anchored allocation renders fewer than `bodyCapacity` rows, the footer separator and footer MUST
follow the last rendered body row. The renderer MUST NOT insert filler body rows to push the footer to
the terminal bottom. Remaining terminal rows after the footer MUST be cleared as blank filler lines.

When `bodyCapacity < anchorBlock.length`, the anchor cannot fully fit:

- In `EDITING`, render `LAYOUT_BLOCKED`.
- In `BROWSING`, render `LAYOUT_BLOCKED` only when `bodyCapacity < 1`; otherwise the selected row fits.

`scrollOffset` remains the persisted scroll position for unanchored `CONFIRMING` mode and for page
commands. The anchored body selector may derive visible rows that do not start exactly at
`scrollOffset`; implementations MUST treat the selector output as authoritative for rendering.

### 8.3 Browsing Scrolling

- `↑` and `↓` move selection by one visible row.
- Movement MUST clamp at first and last visible row.
- Rendering MUST use the anchored body allocation rules so the selected row remains visible.

### 8.4 Confirming Scrolling

- In `CONFIRMING`, no row cursor is shown and no selected row movement occurs.
- `↑` and `↓` adjust `scrollOffset` only.
- `Shift+↑`, `Shift+↓`, `PgUp`, and `PgDn` adjust `scrollOffset` by one page.
- Leaving confirmation with "edit mappings" MUST restore `BROWSING`; selected row MUST become the
  first visible row at the current `scrollOffset`.

This explains frame 7b: after frame 7a scrolls to rows 2..10 and a later page-down/enter exits
confirmation, browsing is at the last page with row 11 selected.

### 8.5 Page Movement

- Page size MUST equal current non-editing body capacity.
- `PgDn`/`Shift+↓` MUST set `scrollOffset = min(scrollOffset + pageSize, maxOffset)`.
- `PgUp`/`Shift+↑` MUST set `scrollOffset = max(scrollOffset - pageSize, 0)`.
- In `BROWSING`, selected row MUST become the first visible row after paging.
- In `CONFIRMING`, selection MUST NOT change.

### 8.6 Keeping Edited Row Visible

- Entering `EDITING` MUST render with anchored body allocation, using the edit block as the anchor.
- If the expanded edit block cannot fit in `bodyCapacity`, `LAYOUT_BLOCKED` MUST render.
- The edited row MUST never be scrolled out of view while `EDITING`.

This places the expanded edit block as high as possible while keeping the full block visible. Example:
from frame 1a, navigating to row 9 and pressing `Enter` in a 15x75 terminal has
`bodyCapacity = 9`, `anchorIndex = 8`, `anchorBlock.length = 2`, and `contextCapacity = 7`.
The body selector MUST render the expanded row 9 block followed by rows 10 and 11. Rows 1 through 8
are omitted because preceding context is never backfilled above the anchor.

### 8.7 `LAYOUT_BLOCKED`

`LAYOUT_BLOCKED` is a render-only blocked layout over the current `EDITING` state. It MUST preserve the
edit buffer, selected mapping, source navigation state, and mapping state. It MUST NOT reuse
`confirmation.kind = EXIT`, because resize is not an exit signal and MUST NOT arm second-`ctrl+c`
SIGINT behavior.

Trigger:

```text
requiredEditBodyRows = activeSources.length
layoutBlocked = mode == EDITING and bodyCapacity < requiredEditBodyRows
```

The storyboard fixture has two active sources per mapping. Therefore:

- At terminal height 8, `bodyCapacity = 8 - 4 - 1 - 1 = 2`; the full two-source edit block fits.
- At terminal height 7, the preferred layout would have `bodyCapacity = 7 - 4 - 1 - 1 = 1`, so the
  separator above the footer MUST collapse and the effective `bodyCapacity = 7 - 4 - 1 = 2`; the full
  two-source edit block still fits.
- At terminal height 6, the separator above the footer MUST collapse and
  `bodyCapacity = 6 - 4 - 1 = 1`; `LAYOUT_BLOCKED` MUST render because the full two-source edit block
  does not fit.

If mappings can vary by source count, `requiredEditBodyRows` MUST be computed from the currently edited
mapping instead of from a session-wide constant.

Behavior:

- Resizing large enough to make `bodyCapacity >= requiredEditBodyRows` MUST return to the normal
  `EDITING` render.
- `Esc` or `ctrl+c` MUST cancel the edit using normal `EDITING` behavior.
- Printable input, Backspace, source navigation, and submit SHOULD be ignored while blocked; the user
  must resize or cancel. This prevents hidden edits while the source list cannot be inspected.
- `LAYOUT_BLOCKED` MUST render at most `bodyCapacity` body rows from the active edit block.
- `LAYOUT_BLOCKED` MUST use the same header, prompt, table header, token rendering, validation icon,
  and footer semantics as `EDITING`, except for the blocked footer text below.

Mockup for a 7-row terminal where the separator above the footer has collapsed and effective
`bodyCapacity = 2`; the full two-source edit block fits:

```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "QQQ":

   #   Beancount Token            GnuCash Source
▸  9   QQQ* * ✓                     ┃ cmdty_id: "QQQ"
                                  ┃ user_symbol: (not set)
  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel
```

Mockup for a 6-row terminal where the separator above the footer has collapsed and effective
`bodyCapacity = 1`; blocked footer text is rendered:

```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "QQQ":

   #   Beancount Token            GnuCash Source
▸  9   QQQ* * ✓                     ┃ cmdty_id: "QQQ"
  Enlarge terminal to edit sources  ·  esc cancel
```

Mockup for a 5-row terminal where the separator above the footer has collapsed and effective
`bodyCapacity = 0`; footer truncates rendering of the table body:

```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "QQQ":

   #   Beancount Token            GnuCash Source
  Enlarge terminal to edit sources  ·  esc cancel
```

Mockup for an 11-row terminal where `bodyCapacity = 5` and 11 total mappings; optional context rows
fill below the anchored edit block according to the anchor-high, fill-below-first rule:

```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "QQQ":

   #   Beancount Token            GnuCash Source
▸  9   QQQ* * ✓                     ┃ cmdty_id: "QQQ"
                                  ┃ user_symbol: (not set)
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel

```

## 9. Collision Resolution Semantics

Collision icons and accept transition are derived from live `currentTargetValue` values:

1. Compute collision groups from `currentTargetValue`, using `edit.concreteValue` for the edited
   mapping.
2. Render `!` for each unresolved collision row.
3. On valid edit submit, commit `edit.concreteValue` as the literal string
   `mapping.targetValue`, even when it equals `defaultSourceValue`.
4. If `unresolvedCollisionCount` becomes zero because of the commit:
   - Enter `CONFIRMING`.
   - Set `confirmation.kind = ACCEPT`.
   - Set `confirmation.choice = NO`.
5. Later manual `ctrl+s` entries MUST also use `confirmation.kind = ACCEPT` and set
   `confirmation.choice = NO`.
6. The user changing the accept choice MUST NOT affect the default for later confirmation visits.

Frame 6 is the automatic zero-collision accept entry with `N` selected. Frame 14 is a later accept
confirmation visit that also defaults to `N`. Frame 15 is the terminal accepted-output state after the
user changes frame 14 to `Y` and presses `Enter`.

## 10. Golden-State Acceptance Tests

All golden tests MUST assert app state, visible rows, prompt/footer, and render. Render assertions MUST
strip ANSI for geometry and inspect style spans separately for bold, dim, and reverse-video.

### 10.1 Frame Tests

| Frame | Initial state | Input sequence | Expected app state | Expected visible rows | Expected prompt/footer | Render assertions |
|---|---|---|---|---|---|---|
| 1a | Fresh dataset, rows 2 and 3 collide | None | `BROWSING`, `filter=""`, selected row 1, `scrollOffset=0`, 1 collision group | 1..9 | Prompt ghost `Tab to view collisions`; footer edit selected | Header includes `1 unresolved collision`; row 1 has `▸`; rows 2/3 have `!`; footer row 15 |
| 1b | Frame 1a | `ctrl+c` | `CONFIRMING EXIT`, choice `NO`, `secondCtrlCArmed=true` | 1..9 | `Skip adding commodities? [y/N]`; footer edit mappings | Header shortcut says `ctrl+c exit`; no row cursor; second `ctrl+c` sends SIGINT |
| 2 | Frame 1a or after exiting 1b | `Tab` or `!` | `BROWSING`, `collisionOnly=true`, selected row 2 | 2,3 | Prompt `!Type to filter`; footer clear filter | Footer row 8; rows 2/3 only; filler clears rows 9..15 |
| 3 | Frame 2 | `3` | `BROWSING`, `collisionOnly=true`, `text="3"`, selected row 3 | 3 | Prompt `!3{cursor}`; footer clear filter | Ordinal `3` bold; no source matching; footer row 7 |
| 4 | Frame 3 | `Backspace`, `↓`, `Enter` | `EDITING` row 3, empty buffer, ghost `AT-T`, token focus | 2 dim, expanded 3 | Editing prompt for `AT-T`; footer no submit | Row 2 super dim; active row shows `▸`, `!`, reverse `A`, dim `T-T`; source rows include `(not set)` |
| 5 | Frame 4 | `A`, `T`, `T` | `EDITING` row 3, buffer `ATT`, valid, collisions zero live | 2 dim, expanded 3 | Footer includes submit | Rows 2/3 have no `!`; active row shows `ATT`, cursor, `✓` |
| 6 | Frame 5 | `Enter` | `CONFIRMING ACCEPT`, choice `NO`, `scrollOffset=0`, collisions zero | 1..9 | `Accept all? [y/N]`; footer confirm per storyboard frame | Header omits collision count; no cursor; row 3 target `ATT` |
| 7a | Frame 6 | `↓` | `CONFIRMING ACCEPT`, choice `NO`, `scrollOffset=1` | 2..10 | `Accept all? [y/N]`; footer edit mappings | No cursor; first visible row is 2; row 10 visible |
| 7b | Frame 7a | `Shift+↓`, `Enter` | `BROWSING`, collisions zero, selected row 11 | 11 | Filter ghost `Type to filter`; footer edit selected | Header includes `ctrl+s submit`; row 11 has `▸`; footer row 7 |
| 7c | Frame 7b | `↑` | `BROWSING`, selected row 10, last page visible | 10,11 | Filter ghost `Type to filter`; footer edit selected | Row 10 has `▸`; row 11 follows; footer row 8 |
| 8 | Frame 7c | `1` | `BROWSING`, `text="1"`, selected row 1 | 1,4,10,11 | Prompt `1{cursor}`; footer clear filter | Bold matches on ordinals 1/10/11 and token `C100-F`; source `100-F` is not matched |
| 9 | Frame 8 | `Enter` | `EDITING` row 1, empty buffer, ghost `APPLE`, token focus | Expanded 1, dim 4/10/11 | Editing prompt for `APPLE`; footer submit | Active row shows reverse `A` and dim `PPLE`; source rows `AAPL`, `APPLE`; dim inactive rows |
| 10 | Frame 9 | `4`, `4`, `P`, `L` | `EDITING` row 1, buffer `44PL`, invalid, token focus | Expanded 1, dim 4/10/11 | Error `must start with A–Z`; no submit | `✗` two spaces after cursor; footer row 11; no source pointer |
| 11 | Frame 10 | Type `56789012345678901234` | `EDITING` row 1, 24-char buffer, invalid, max error active | Expanded 1, dim 4/10/11 | Error `24 chars max`; no submit | Cursor at max boundary; `✗` at capped icon column; 25th char discarded in separate assertion |
| 12a | Frame 9 or 10/11 | `↓` | `EDITING`, buffer `AAPL`, valid, source focus first source | Expanded 1, dim 4/10/11 | Footer submit | Row-level cursor absent; source pointer at first source; `✓` shown |
| 12b | Frame 9 or 10/11 | `↑` | `EDITING`, buffer `APPLE`, valid, `sourcePointerIndex=1` | Expanded 1, dim 4/10/11 | Footer submit | Source pointer line 2; pointer came from source navigation, not exact-match tracking |
| 13 | Frame 12b | `Enter` or `Esc`, then `2` after existing filter `1` | `BROWSING`, `text="12"`, selected null | Empty result | Error no matching rows | Blank body row under header; no cursor; footer row 7 |
| 14 | Frame 13 | `ctrl+s` | `CONFIRMING ACCEPT`, choice `NO`, collisions zero | 1..9 | `Accept all? [y/N]`; footer edit mappings | Accept prompt defaults to `NO`; filter does not constrain confirming table |
| 15 | Frame 14 | `y` or `←`, then `Enter` | Terminal accepted state, `result.status=ACCEPTED` | None | None | Frame line 1 is `11 commodities created.`; frame line 2 is `❯`; remaining frame lines are blank/cleared |

### 10.2 Defect-Prevention Tests

| Issue from checklist | Required test |
|---|---|
| Distinct confirmation intents missing | Assert frame 1b uses `kind=EXIT`, prompt `Skip adding commodities?`, default `NO`, and `YES` result `SKIPPED`; frames 6 and 14 both use `kind=ACCEPT`, default `NO`, and `YES` result `ACCEPTED`. |
| Confirmation default regression | Change an accept or exit prompt to `YES`, leave confirmation, re-enter any y/n confirmation, and assert `confirmation.choice=NO`. No renderer/component local state may remember the previous boolean. |
| `ctrl+c` dispatcher absent | Assert `ctrl+c` in `BROWSING` enters exit confirmation, in `EDITING` cancels edit, in `ACCEPT` cancels batch, and second `ctrl+c` in `EXIT` emits SIGINT. |
| Filtering underspecified | Assert Tab and `!` both toggle collision metafilter; query text matches ordinal/token only; source text does not match; empty results clear selection; `ctrl+s` still opens accept confirmation with zero collisions. |
| Edit input append contradiction | Assert frame 4 to 5 streaming overwrite produces `ATT`, not `AT-TATT` or `ATTT`; ghost disappears when buffer no longer prefixes `defaultSourceValue`. |
| Lossy domain model | Unit-test collision groups, source effective values, literal `targetValue`, derived `currentTargetValue`, default source, and live edited target as separate fields. |
| Missing sorting rules | Change row 3 target to `ATT`; assert order remains row 2 then row 3 and does not resort by new target. |
| Layout not deterministic | Golden-render all frames at 15x75; assert row numbers for header, prompt, table header, footer, blank filler, and no alternate screen sequences. |
| Validation incomplete | Assert grammar cases, `✓`/`✗`, submit gating, 24th-character cap, and 25th-character discard/flash. |
| Source selection incomplete | Assert `↑`/`↓` enter source navigation at last/first active source, autofill by `sourcePointerIndex`, moving above the first source or below the last source restores `sourceEntryBuffer`, and typing/backspace exits source navigation. |
| Refactored mapping semantics | Assert `targetValue = null` enters edit mode with empty buffer plus `defaultSourceValue` ghost text; assert literal `targetValue = defaultSourceValue` enters edit mode with that value pre-filled and commits back as a literal string. |
| Derived ghost semantics | Assert frame 12b Backspace changes `APPLE` to `APPL`, returns focus to token input, clears source navigation, and renders ghost `E`; assert submitting stores literal `APPL` and re-entering edit mode shows no ghost. |

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
- `ctrl+c` in accept confirmation cancels the batch because the header says `ctrl+c cancel`;
  the storyboard only explicitly defines second `ctrl+c` SIGINT for exit confirmation.
- Leaving accept confirmation with `NO` selects the first visible row at the current scroll offset.
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
