# Gnubeans TUI Implementation Contract

This document is the normative implementation contract for the TUI component
illustrated by `tui_interaction_storyboard.md`. The storyboard is a visual
acceptance companion only; implementers MUST be able to reproduce the
storyboarded state transitions, rendering geometry, and key behavior from this
contract alone.

Normative keywords:

- MUST and MUST NOT define required behavior.
- SHOULD defines preferred behavior where an implementation choice remains.
- "Frame" refers to a numbered storyboard frame when a requirement is traced to
  that visual acceptance example.

## 1. Terms and Coordinate System

| Term | Definition |
|---|---|
| Terminal frame | The TUI redraw area. The canonical fixture frame is 15 rows by 75 columns. |
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
  targetPolicy: TargetPolicy;
}

interface TargetPolicy {
  maxTokenLength: number;
  validate(value: string, context: TargetValidationContext): ValidationState;
}

interface TargetValidationContext {
  isConcreteBuffer: boolean;
  isGhostOnlyDefault: boolean;
  mapping: Mapping;
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
  cursor: number;
}

interface SelectionState {
  selectedOrdinal: number | null;
  scrollOffset: number;
}

interface EditState {
  mappingOrdinal: number;
  buffer: string;
  cursor: number;
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
  status: "RUNNING" | "ACCEPTED" | "SKIPPED" | "SIGINT";
}
```

Ownership rules:

- `confirmation.choice` MUST be owned by root state because `y`/`n`, arrow toggles, `Enter`, and `Esc`
  require deterministic choice state between key events. The renderer MUST project the current choice
  only; it MUST NOT initialize, reset, or store confirmation choice.
- Entering `CONFIRMING` MUST set `confirmation.choice = NO`, regardless of confirmation kind. Leaving
  confirmation does not require choice cleanup because the next confirmation entry overwrites it.
- `edit` MUST be `null` outside `EDITING`.
- `visibleRows`, `collisionGroups`, `unresolvedCollisions`, validation display positions, prompt text,
  footer text, and render lines MUST be derived selectors, not mutable component state.
- `config` MUST be root-owned immutable input for a TUI session. Renderers MUST NOT hard-code entity
  nouns, mapping nouns, column labels, source labels, accept prompt text, exit prompt text, created
  output text, target validation rules, target maximum display width, or validation error text.
- `selectedOrdinal` MUST identify the selected mapping by stable ordinal, not by visible-row index.
- `scrollOffset` MUST be the zero-based offset into the current derived visible row list.
- `filter.cursor` MUST be the zero-based insertion offset into `filter.text`.
- `edit.cursor` MUST be the zero-based insertion offset into `edit.buffer`.
- Input cursors MUST be clamped to valid string boundaries after every mutation. The storyboard fixture
  uses ASCII values, but implementations MUST NOT split a Unicode scalar value when moving or deleting.
- `defaultSourceValue`, `currentTargetValue`, and source `effectiveValue` MUST be derived selectors,
  not stored fields.
- `Source.originalValue` and optional `Source.sanitizedValue` MUST be supplied as input data before the
  TUI component starts. The component MUST NOT compute, infer, or mutate `sanitizedValue`.
- Edit ghost text MUST be derived from `targetValue`, `defaultSourceValue`, `edit.buffer`, and
  `edit.cursor`, not stored in `EditState`.

Derived entity selectors:

```text
source.effectiveValue = source.sanitizedValue ?? source.originalValue
mapping.defaultSource = the only source where source.label == mapping.defaultSourceLabel
mapping.defaultSourceValue = mapping.defaultSource.effectiveValue
mapping.currentTargetValue = mapping.targetValue ?? mapping.defaultSourceValue
mapping.activeSources = sources where source.effectiveValue is not null, in source display order
edit.ghostSuffix =
  if mapping.targetValue == null
     and edit.cursor == edit.buffer.length
     and edit.buffer is a prefix of mapping.defaultSourceValue:
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
- A source with `originalValue = null` MUST also have `sanitizedValue = null`; callers MUST NOT create
  an effective value from a missing source.
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
  targetPolicy: commodityTargetPolicy,
};
```

The storyboard fixture's `commodityTargetPolicy` has these entity-specific rules:

1. Maximum target display width is 24 columns.
2. A concrete target MUST be at least 1 character.
3. A concrete target MUST start with `A-Z`.
4. A concrete target MUST contain only `A-Z`, `0-9`, and `-` after the first character.
5. A concrete target MUST end with `A-Z` or `0-9`.
6. Error precedence is `24 chars max`, then `must start with A-Z`, then
   `only A-Z, 0-9, and - allowed`, then `must end with A-Z or 0-9`.

Implementations MUST support equivalent configurations for other entity types and source labels without
changing the state machine, render pipeline, key handling, or component internals. Entity-specific
target validation MUST be supplied by `targetPolicy`. Entity-specific source normalization is outside
the TUI component; callers MUST provide each source's `originalValue` and optional `sanitizedValue`.

### 2.3 Source Value Input and Display Contract

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

The source display rules above use `originalValue` and `sanitizedValue` only. They MUST NOT infer,
compute, or recompute sanitization. This allows callers to prepare source values for other mapped
entities without changing the TUI component.

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

- Printable characters in `BROWSING` MUST insert into `filter.text` at `filter.cursor`, then advance
  `filter.cursor` by the inserted character length.
- In `BROWSING`, `Tab` MUST toggle `filter.collisionOnly`.
- In `BROWSING`, `!` MUST toggle `filter.collisionOnly`; it MUST NOT append a literal `!` to
  `filter.text`.
- The prompt MUST render the active metafilter as a leading `!`.
- Backspace, `ctrl+h`, and readline `backward-delete-char` aliases MUST delete the character before
  `filter.cursor` when `filter.cursor > 0`, then decrement `filter.cursor`. If `filter.cursor == 0`
  and `filter.text` is empty and `collisionOnly` is true, they MUST clear `collisionOnly`.
- `Esc` MUST clear both `collisionOnly` and `text` when either is active.
  Clearing `text` MUST set `filter.cursor = 0`.

Matching semantics:

- If `collisionOnly` is true, candidate rows MUST first be limited to unresolved collision rows.
- `text` MUST match only the ordinal column and the current target token (`config.targetColumnLabel`).
- The filter matcher MUST NOT compare `text` with `config.sourceColumnLabel`, any `Source.label`, or
  any source display/effective/original/sanitized value.
- Matching MUST be case-insensitive for ASCII letters.
- Lowercase ASCII query letters MUST match uppercase target letters and ordinal matching MUST be
  unaffected by letter case. Golden tests MUST include at least one lowercase query that matches an
  uppercase target token.
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
prompt MUST default to `NO` on entry by setting root confirmation state before the first render. The
renderer MUST NOT reset the prompt to `NO` on every render because the selected choice must persist
between key events until the user confirms, changes choice, cancels, or leaves confirmation.

### 4.2 Transition Table

| Current state | Event | Guard | Side effects | Next state |
|---|---|---|---|---|
| `BROWSING` | Printable char | Any | Insert char into `filter.text` at `filter.cursor`; advance cursor; parse/filter; clamp selection | `BROWSING` |
| `BROWSING` | `Tab` or `!` | Any | Toggle `filter.collisionOnly`; clamp selection | `BROWSING` |
| `BROWSING` | `Backspace` or `ctrl+h` | Filter active | Delete filter char before cursor or clear metafilter; clamp cursor and selection | `BROWSING` |
| `BROWSING` | `Esc` | Filter active | Clear filter and metafilter; clamp selection | `BROWSING` |
| `BROWSING` | `↑` / `↓` | `visibleRows` non-empty | Move `selectedOrdinal` by -1/+1 and adjust scroll to keep selected visible | `BROWSING` |
| `BROWSING` | `Shift+↑` / `PgUp` | `visibleRows` non-empty | Page up; selected row becomes first visible row after paging | `BROWSING` |
| `BROWSING` | `Shift+↓` / `PgDn` | `visibleRows` non-empty | Page down; selected row becomes first visible row after paging | `BROWSING` |
| `BROWSING` | `Enter` | `selectedOrdinal != null` | Initialize `edit` for selected row | `EDITING` |
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount == 0` | Enter accept confirmation; set `choice = NO` | `CONFIRMING` with `ACCEPT` |
| `BROWSING` | `ctrl+s` | `unresolvedCollisionCount > 0` | No state change | `BROWSING` |
| `BROWSING` | `ctrl+c` | Any | Enter exit confirmation; set `choice = NO`; `secondCtrlCArmed = true` | `CONFIRMING` with `EXIT` |
| `EDITING` | Printable char | Any | Apply edit insertion algorithm; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Backspace` or `ctrl+h` | Any | Return to token input if needed; delete char before cursor; validate; recompute collisions live | `EDITING` |
| `EDITING` | `Tab` | Ghost suffix available | Complete buffer to displayed value; clear source navigation; validate | `EDITING` |
| `EDITING` | `↑` / `↓` | Source list non-empty | Enter, move within, or exit reversible source navigation | `EDITING` |
| `EDITING` | `Enter` | Validation `VALID` | Commit displayed edit value to mapping target; clear edit; recompute collisions | `CONFIRMING` with `ACCEPT` if collisions now zero, else `BROWSING` |
| `EDITING` | `Enter` | Validation not `VALID` | No commit; keep validation error | `EDITING` |
| `EDITING` | `Esc` | Any | Discard buffer; clear edit; preserve filter; restore selection on edited row | `BROWSING` |
| `EDITING` | `ctrl+c` | Any | Discard buffer; clear edit; preserve filter; restore selection on edited row | `BROWSING` |
| `CONFIRMING ACCEPT` | `y` | Any | `choice = YES` | Same confirmation kind |
| `CONFIRMING ACCEPT` | `n` | Any | `choice = NO` | Same confirmation kind |
| `CONFIRMING ACCEPT` | `←` / `→` | Any | Toggle choice | Same confirmation kind |
| `CONFIRMING ACCEPT` | `↑` / `↓` | Any | Scroll only; no selected row movement | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Shift+↑` / `PgUp` | Any | Page scroll up only | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Shift+↓` / `PgDn` | Any | Page scroll down only | Same confirmation kind |
| `CONFIRMING ACCEPT` | `Enter` | `choice == YES` | Set `result.status = ACCEPTED` | Terminal final state |
| `CONFIRMING ACCEPT` | `Enter` | `choice == NO` | Leave confirmation; selection becomes first visible row at current scroll | `BROWSING` |
| `CONFIRMING ACCEPT` | `Esc` | Any | Leave confirmation | `BROWSING` |
| `CONFIRMING ACCEPT` | `ctrl+c` | Any | Enter exit confirmation; set `choice = NO`; `secondCtrlCArmed = true` | `CONFIRMING` with `EXIT` |
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
| `←` | Move filter cursor left | Move edit cursor left in token input; no-op in source list | Toggle choice | Toggle choice |
| `→` | Move filter cursor right | Move edit cursor right in token input; no-op in source list | Toggle choice | Toggle choice |
| `Enter` | Edit selected row | Submit only if valid | Confirm if YES, otherwise edit mappings | Skip if YES, otherwise edit mappings |
| `Esc` | Clear active filter, otherwise no-op | Cancel edit | Edit mappings | Edit mappings |
| `Tab` | Toggle collision metafilter | Complete ghost text in token input | No-op | No-op |
| `!` | Toggle collision metafilter | Insert literal `!`; validation becomes invalid | No-op | No-op |
| `Backspace` | Delete filter char before cursor or metafilter | Return to token input if needed, then delete edit char before cursor | No-op | No-op |
| `ctrl+h` | Same as Backspace | Same as Backspace | No-op | No-op |
| `ctrl+s` | Open accept confirmation if zero collisions | No-op | No-op | No-op |
| `ctrl+c` | Enter exit confirmation | Enter exit confirmation | Enter exit confirmation | Send SIGINT |
| `y` / `n` | Insert into filter at cursor | Insert into buffer at cursor | Set choice | Set choice |
| Other printable | Insert into filter at cursor | Insert into buffer at cursor | No-op | No-op |

Unlisted keys and control sequences:

- Any key not listed in this matrix MUST be ignored and MUST NOT mutate root state.
- If the terminal environment cannot distinguish `Shift+↑` or `Shift+↓` from normal arrow keys, the
  implementation MUST still support `PgUp` and `PgDn` as reliable page-movement equivalents. It MUST
  NOT reinterpret indistinguishable normal arrow events as page movement. Portability tests MUST drive
  page movement with `PgUp`/`PgDn`.

### 5.1 Readline-Style Input Bindings

The filter input line in `BROWSING` and token input line in `EDITING` MUST support the readline-style
bindings below. Implementations MUST normalize common `bind -P` function names, byte sequences, or
semantic key events into these actions before dispatching.

App-specific bindings in the main key matrix MUST take precedence over readline names where the same
key is reserved by the TUI:

- `Tab` / `ctrl+i` in `BROWSING` MUST toggle the collision metafilter, not autocomplete.
- `Tab` / `ctrl+i` in `EDITING` MUST complete ghost text, not generic readline completion.
- `ctrl+s` in `BROWSING` MUST submit when collisions are zero, not start readline forward search.
- `ctrl+c` MUST follow the TUI cancellation/exit contract, not readline signal defaults.
- `↑` and `↓` MUST follow the TUI row/source/confirmation navigation contract, not readline history.

Text-editing actions:

| Readline function family | Typical keys/sequences | Filter input behavior | Edit input behavior |
|---|---|---|---|
| `accept-line` | `Enter`, `ctrl+j`, `ctrl+m` | Dispatch as `Enter` and edit selected row if possible. | Dispatch as `Enter` and submit only when validation is `VALID`. |
| `complete` | `Tab`, `ctrl+i` | Toggle `filter.collisionOnly`. | Complete ghost text when available; otherwise no-op. |
| `backward-char` | `ctrl+b`, left-arrow escape sequences | Move `filter.cursor` left by one character; clamp at 0. | Move `edit.cursor` left by one character when `focusRegion = TOKEN_INPUT`; no-op in `SOURCE_LIST`. |
| `forward-char` | `ctrl+f`, right-arrow escape sequences | Move `filter.cursor` right by one character; clamp at `filter.text.length`. | Move `edit.cursor` right by one character when `focusRegion = TOKEN_INPUT`; clamp at `edit.buffer.length`; no-op in `SOURCE_LIST`. |
| `beginning-of-line` | `ctrl+a`, Home escape sequences | Set `filter.cursor = 0`. | Set `edit.cursor = 0` when `focusRegion = TOKEN_INPUT`; no-op in `SOURCE_LIST`. |
| `end-of-line` | `ctrl+e`, End escape sequences | Set `filter.cursor = filter.text.length`. | Set `edit.cursor = edit.buffer.length` when `focusRegion = TOKEN_INPUT`; no-op in `SOURCE_LIST`. |
| `backward-delete-char` | `Backspace`, `ctrl+h`, `ctrl+?` / DEL | Delete character before `filter.cursor`; if empty at cursor 0, clear active metafilter. | Return to token input if needed, then delete character before `edit.cursor`. |
| `delete-char` | `ctrl+d`, Delete escape sequences | Delete character at `filter.cursor`; no-op at end. | Delete character at `edit.cursor`; no-op at end. |
| `kill-line` | `ctrl+k` | Delete from `filter.cursor` through end of `filter.text`. | Delete from `edit.cursor` through end of `edit.buffer`. |
| `unix-line-discard` | `ctrl+u` | Delete from start of `filter.text` through `filter.cursor`; set cursor to 0. | Delete from start of `edit.buffer` through `edit.cursor`; set cursor to 0. |
| `backward-kill-line` | `ctrl+x ctrl+?` | Same as `unix-line-discard`. | Same as `unix-line-discard`. |
| `kill-word` | `meta+d` | Delete from cursor through the end of the next token. | Delete from cursor through the end of the next token. |
| `backward-kill-word`, `unix-word-rubout` | `meta+backspace`, `ctrl+w` | Delete from the start of the previous token through cursor. | Delete from the start of the previous token through cursor. |
| `clear-screen`, `redraw-current-line` | `ctrl+l`, terminal redraw events | Re-render current state only; MUST NOT mutate root state. | Re-render current state only; MUST NOT mutate root state. |
| `abort` | `ctrl+g` | No-op. It MUST NOT act like `Esc` or `ctrl+c`. | No-op. It MUST NOT act like `Esc` or `ctrl+c`. |
| `quoted-insert` | `ctrl+q`, `ctrl+v` | No-op. Quoted insertion is not supported. | No-op. Quoted insertion is not supported. |
| `undo` / `revert-line` | `ctrl+_`, `ctrl+x ctrl+u`, `meta+r` | No-op. Undo is not part of the storyboard contract. | No-op. Undo is not part of the storyboard contract. |
| `transpose-chars`, `transpose-words`, case transforms | `ctrl+t`, `meta+t`, `meta+c`, `meta+l`, `meta+u` | No-op. Text transformation is not supported. | No-op. Text transformation is not supported. |
| Completion variants | `meta+?`, `meta+=`, `meta+!`, `meta+/`, `meta+~`, `meta+$`, `meta+@` | No-op. | No-op. |
| Search/history variants | `ctrl+r`, readline `forward-search-history`, `meta+n`, `meta+p`, `meta+<`, `meta+>` | No-op, except `ctrl+s` where the main matrix defines TUI submit behavior. | No-op. |
| Yank/kill-ring variants | `ctrl+y`, `meta+y`, `meta+.`, `meta+_`, `meta+ctrl+y` | No-op. Paste is handled by the terminal as ordinary printable input if it arrives as characters. | No-op. Paste is handled by the terminal as ordinary printable input if it arrives as characters. |
| Keyboard macro, shell expansion, glob, alias, dump, and vi-mode functions | `ctrl+x...`, `meta+...`, vi readline names | No-op unless another row in this table maps the exact input to a TUI event. | No-op unless another row in this table maps the exact input to a TUI event. |

Word-boundary actions MUST use ASCII token boundaries:

```text
wordChar = [A-Za-z0-9_-]
```

`kill-word` MUST first skip non-word characters at or after the cursor, then delete through the next
contiguous run of word characters. `backward-kill-word` and `unix-word-rubout` MUST first skip non-word
characters before the cursor, then delete the previous contiguous run of word characters.

After any filter-input readline mutation:

```text
filter.cursor = clamp(filter.cursor, 0, filter.text.length)
filter.raw = (filter.collisionOnly ? "!" : "") + filter.text
parse/filter visible rows
clamp selection
```

After any edit-input readline mutation:

```text
if focusRegion == SOURCE_LIST:
  focusRegion = TOKEN_INPUT
  sourcePointerIndex = null
  sourceEntryBuffer = null

edit.cursor = clamp(edit.cursor, 0, edit.buffer.length)
validate via config.targetPolicy.validate(edit.concreteValue, context)
recompute collisions using edit.buffer for edited mapping
```

Every edit-input readline mutation MUST exit `SOURCE_LIST` first, clear `sourcePointerIndex`, clear
`sourceEntryBuffer`, apply the mutation to `edit.buffer`, clamp `edit.cursor`, validate, and recompute
collisions. Every filter-input readline mutation MUST parse/filter, clamp selection, and clamp
`filter.cursor`.

Tests MUST cover the supported aliases (`ctrl+j`, `ctrl+m`, `ctrl+i`, `ctrl+?`, `ctrl+p`, `ctrl+n`,
`ctrl+b`, `ctrl+f`, `ctrl+a`, `ctrl+e`, `ctrl+d`, `ctrl+k`, `ctrl+u`, `ctrl+w`) and at least one no-op
from each no-op family above. No-op tests MUST assert that root state and rendered output are unchanged.

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
| Token max display | `9..(8 + config.targetPolicy.maxTokenLength)` | Storyboard commodity fixture: 24 display columns, columns 9..32. |
| Edit cursor at offset L | `9 + L` | Reverse-video character at offset L, or reverse-video space when L is at end. In the storyboard commodity fixture, offset 24 is column 33. |
| Validation icon normal | Cursor column + 2 | `✓` or `✗`, except max-length cap below. |
| Validation icon max cap | `10 + config.targetPolicy.maxTokenLength` | In the storyboard commodity fixture, at 24 chars the icon MUST remain at column 34. |
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

For browsing text filters, `{cursor}` MUST render at `filter.cursor` within `filter.text`. If
`filter.cursor == filter.text.length`, the cursor MUST be a reverse-video space after the visible query.
If `filter.cursor < filter.text.length`, the cursor MUST cover the character at `filter.cursor`. The
metafilter `!` prefix is not part of `filter.text` and MUST NOT be counted by `filter.cursor`.

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
4. `edit.cursor = edit.buffer.length`.
5. `focusRegion = TOKEN_INPUT`.
6. `sourcePointerIndex = null`.
7. `sourceEntryBuffer = null`.

Entering, submitting, or cancelling `EDITING` MUST NOT clear or mutate `filter.raw`,
`filter.collisionOnly`, `filter.text`, or `filter.cursor`. Returning to `BROWSING` from edit mode MUST
preserve the pre-edit filter so the next printable browsing key inserts at the preserved cursor. Frame
13 depends on this: after editing from filter `1` with the cursor at the end, returning to browsing and
typing `2` yields filter text `12`.

Ghost text is derived, not stored. When `mapping.targetValue === null`, `edit.cursor == edit.buffer.length`,
and `edit.buffer` is a prefix of `mapping.defaultSourceValue`, the input line MUST display the remaining
suffix of `defaultSourceValue` as ghost text. When `edit.cursor` is not at the end of the buffer, no
ghost text MUST render. When `mapping.targetValue !== null`, no ghost text MUST render even if the
literal `targetValue` is a prefix of `defaultSourceValue`.

The reverse-video cursor MUST render at `edit.cursor`. If ghost text is active and `edit.cursor` is at
the end of the buffer, the cursor MUST cover the next ghost character. If no ghost text is active and
`edit.cursor == edit.buffer.length`, the cursor MUST be a reverse-video space after the buffer. If
`edit.cursor < edit.buffer.length`, the cursor MUST cover the character at `edit.cursor`. Frame 4
displays `A` as the cursor and `T-T` as dim ghost text for row 3 because its `targetValue` is null.
Frame 9 displays `APPLE` as ghost text when row 1's `targetValue` is null. If row 1 later has literal
`targetValue = "APPL"`, re-entering edit mode MUST display `APPL` with the cursor after `L` and no
ghost `E`.

`ghostValue`, `ghostCursor`, and `ghostSourceLabel` MUST NOT be stored in `EditState`; all three are
derivable from the selected mapping and `edit.buffer`.

### 7.2 Streaming Insert Algorithm

On printable character `ch` in `EDITING`:

```text
if focusRegion == SOURCE_LIST:
  focusRegion = TOKEN_INPUT
  sourcePointerIndex = null
  sourceEntryBuffer = null

candidateBuffer = buffer with ch inserted at edit.cursor

if displayWidth(candidateBuffer) > config.targetPolicy.maxTokenLength:
  discard ch
  set maxLengthFlashUntil
  set error to config.targetPolicy.validate(candidateBuffer, context).errorMessage
  render capped invalid icon
  return

buffer = candidateBuffer
edit.cursor += length(ch)
validate via config.targetPolicy.validate(edit.concreteValue, context)
recompute collisions using buffer for edited mapping
```

Printable characters that are invalid under `config.targetPolicy.validate`, including `!` in the
storyboard commodity fixture, MUST still be inserted into `edit.buffer` at `edit.cursor` when
`config.targetPolicy.maxTokenLength` has not been reached. They MUST produce validation `INVALID`,
render `✗`, show the policy-provided validation error, and keep `Enter` submit gated. Implementations
MUST NOT silently discard, sanitize, or transform invalid printable characters except for characters
rejected by the configured maximum display width.

Ghost behavior:

- Typing a character that keeps `buffer` as a prefix of `defaultSourceValue` MUST continue rendering
  the remaining suffix as ghost text when `targetValue` is null and `edit.cursor` is at the end of the
  buffer.
- Typing a character that makes `buffer` no longer a prefix of `defaultSourceValue` MUST make
  `edit.ghostSuffix` derive to empty; no separate deviation flag is stored.
- If later Backspace returns `buffer` to a prefix of `defaultSourceValue` while `targetValue` is null and
  `edit.cursor` is at the end of the buffer, ghost text MUST reappear.
- Backspace MUST delete the character before `edit.cursor` when `edit.cursor > 0` and then decrement
  `edit.cursor`.
- If Backspace is pressed while `focusRegion = SOURCE_LIST`, the pointer MUST first return to
  `TOKEN_INPUT`, clear `sourcePointerIndex`, clear `sourceEntryBuffer`, and then delete one buffer
  character before `edit.cursor` from the current autofilled buffer.
- If `edit.cursor == 0`, Backspace MUST do nothing.

Frame 5 requirement: typing `A`, `T`, `T` over ghost `AT-T` produces buffer `ATT`; the third character
makes `buffer` no longer a prefix of `defaultSourceValue`, so ghost text disappears,
`edit.cursor == 3`, validation is `✓`, and rows 2 and 3 have no collision icons.

Frame 12b backspace requirement: from source-list focus with buffer `APPLE`, Backspace MUST return focus
to `TOKEN_INPUT`, clear `sourcePointerIndex`, clear `sourceEntryBuffer`, delete the final `E`, set
`edit.cursor = 4`, and render `APPL` plus ghost `E` as `APPL*E*` because the mapping's `targetValue`
is still null.

### 7.3 Tab Autocomplete

In `EDITING`, `Tab` MUST:

1. If `edit.ghostSuffix` is non-empty, set `buffer` to `edit.renderedValue` and set
   `edit.cursor = buffer.length`.
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
  `sourcePointerIndex`, clear `sourceEntryBuffer`, set `edit.cursor = buffer.length`, and set
  `focusRegion = TOKEN_INPUT`.
- When `focusRegion = SOURCE_LIST` and `↓` is pressed while
  `sourcePointerIndex == activeSources.length - 1`, the cursor has moved below the last source. The
  implementation MUST restore `buffer = sourceEntryBuffer`, clear `sourcePointerIndex`, clear
  `sourceEntryBuffer`, set `edit.cursor = buffer.length`, and set `focusRegion = TOKEN_INPUT`.
- When `focusRegion = SOURCE_LIST` and movement remains within the list, `↑` and `↓` MUST move
  `sourcePointerIndex` by -1 or +1.
- Movement MUST set `focusRegion = SOURCE_LIST`.
- Movement MUST autofill `buffer` with the pointed source's `effectiveValue`.
- Movement MUST set `edit.cursor = buffer.length` after autofill.
- Printable typing, Backspace, and `ctrl+h` while `focusRegion = SOURCE_LIST` MUST exit source-list
  navigation, clear `sourcePointerIndex`, and clear `sourceEntryBuffer` before applying the edit.
- Exact matches between `buffer` and a source `effectiveValue` MUST NOT create or move
  `sourcePointerIndex` while `focusRegion = TOKEN_INPUT`.

Frame 12a: `↓` from frame 9 points at `cmdty_id: "AAPL"` and fills `AAPL`.
Frame 12b: `↑` from frame 9 wraps to `user_symbol: "APPLE"` and fills `APPLE`.

### 7.5 Target Validation

Target validation is an injected policy. The TUI component MUST call `config.targetPolicy.validate`
whenever the edit buffer, ghost/default target, source selection, or target-relevant context changes.
The component MUST NOT hard-code target-name grammar, allowed characters, maximum length, error
precedence, or error message text.

Validation inputs:

```text
validationValue =
  if edit.buffer is non-empty:
    edit.buffer
  else if mapping.targetValue == null:
    mapping.defaultSourceValue
  else:
    mapping.targetValue

context.isConcreteBuffer = edit.buffer is non-empty
context.isGhostOnlyDefault = edit.buffer is empty and mapping.targetValue == null
context.mapping = active mapping
```

Display and gating:

- The validation icon and error message MUST be the values returned by `config.targetPolicy.validate`.
- `✓` MUST render when policy validation returns `status = VALID`.
- `✗` MUST render when policy validation returns `status = INVALID`.
- `Enter` MUST submit only when validation returns `status = VALID` and the value is a concrete buffer
  value, source selection, or autocomplete selection. Ghost-only default text can be policy-valid for
  display, but MUST NOT by itself show the submit affordance.
- `config.targetPolicy.maxTokenLength` MUST control the input cap, the max-length cursor position, and
  the capped validation-icon column. The component MUST NOT assume 24 columns except in the storyboard
  commodity fixture.

Storyboard commodity fixture validation:

- Frame 10: after typing the first `4`, the commodity target policy MUST return error
  `must start with A-Z`; `✗` MUST appear two spaces to the right of the reverse-video cursor.
- Frame 11: after the 24th character, the cursor reaches the configured max target boundary and `✗`
  MUST render at the capped icon column. A 25th character MUST be discarded, flash `✗` at the capped
  icon column, and set transient error `24 chars max`.
- The max-length flash and policy-provided max-length error MUST be visible on the immediate render
  after the discarded over-limit character. The storyboard does not require a wall-clock fade duration;
  implementations MUST clear the transient max-length error on the next accepted edit-buffer mutation,
  source navigation event, mode exit, or validation-result change. Golden tests MUST assert the
  immediate render and MUST NOT depend on real-time timer expiry.

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
- In `LAYOUT_BLOCKED`, the footer text MUST be
  `  Enlarge terminal to edit sources  ·  esc cancel`.
- At terminal height 7 with the storyboard fixture, the footer separator MUST collapse, the effective
  `bodyCapacity` MUST be 2, the full two-source edit block MUST render, and the normal editing footer
  MUST render immediately after the second source row.
- At terminal height 6 with the storyboard fixture, the footer separator MUST collapse, the effective
  `bodyCapacity` MUST be 1, only the first row of the active edit block MUST render, and the blocked
  footer text MUST render immediately after that body row.
- At terminal height 5 with the storyboard fixture, the footer separator MUST collapse, the effective
  `bodyCapacity` MUST be 0, no body rows MUST render, and the blocked footer text MUST render
  immediately after the table header.
- At terminal height 11 with the storyboard fixture, `bodyCapacity` MUST be 5. Editing ordinal 9 MUST
  render the two-row edit anchor for ordinal 9, then ordinal 10, then ordinal 11. The renderer MUST NOT
  backfill ordinals 1 through 8 above the edit anchor, and the normal editing footer MUST render two
  rows below ordinal 11 when the footer separator is visible.

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
6. The user changing the accept choice MUST persist within the current confirmation visit until another
   confirmation key changes it or the visit ends, but MUST NOT affect the `NO` default applied when a
   later confirmation visit starts.

Frame 6 is the automatic zero-collision accept entry with `N` selected. Frame 14 is a later accept
confirmation visit that also defaults to `N`. Frame 15 is the terminal accepted-output state after the
user changes frame 14 to `Y` and presses `Enter`.

## 10. Golden-State Acceptance Tests

All golden tests MUST assert app state, visible rows, prompt/footer, and render. Render assertions MUST
use a virtual terminal emulator (pyte) to separate geometry from style: geometry assertions use
`screen.display` (ANSI-stripped), style assertions use pyte cell attributes (`bold`, `reverse`). SGR 2
(dim/faint) is not tracked by pyte and MUST be verified by inspecting the raw ANSI output directly. Each
frame MUST also have a snapshot test comparing the full plain-text display against a committed reference
file; snapshots are regenerated with `pytest --update-snapshots`.

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
| Confirmation default regression | Change an accept or exit prompt to `YES`, leave confirmation, re-enter any y/n confirmation, and assert `confirmation.choice=NO` immediately on entry. Also assert the renderer does not reset choice during redraw inside the same confirmation visit. |
| `ctrl+c` dispatcher absent | Assert `ctrl+c` in `BROWSING` enters exit confirmation, in `EDITING` cancels edit, in `ACCEPT` cancels batch, and second `ctrl+c` in `EXIT` emits SIGINT. |
| Filtering underspecified | Assert Tab and `!` both toggle collision metafilter; query text matches ordinal/token only; source text does not match; empty results clear selection; `ctrl+s` still opens accept confirmation with zero collisions. |
| Edit input insertion contradiction | Assert frame 4 to 5 end-cursor insertion produces `ATT`, not `AT-TATT` or `ATTT`; ghost disappears when buffer no longer prefixes `defaultSourceValue`. |
| Lossy domain model | Unit-test collision groups, source effective values, literal `targetValue`, derived `currentTargetValue`, default source, and live edited target as separate fields. |
| Missing sorting rules | Change row 3 target to `ATT`; assert order remains row 2 then row 3 and does not resort by new target. |
| Layout not deterministic | Golden-render all frames at 15x75; assert row numbers for header, prompt, table header, footer, blank filler, and no alternate screen sequences. |
| Injected validation incomplete | Assert a test `targetPolicy` controls grammar cases, `✓`/`✗`, submit gating, maximum display width, and over-limit discard/flash; assert the storyboard commodity fixture still enforces the 24-column commodity policy. |
| Source sanitization hard-coded | Provide sources with caller-supplied `originalValue` and `sanitizedValue`; assert `effectiveValue`, source display arrows, default source value, ghost text, and source selection use those supplied fields exactly and no sanitization function is invoked by the TUI. |
| Source selection incomplete | Assert `↑`/`↓` enter source navigation at last/first active source, autofill by `sourcePointerIndex`, moving above the first source or below the last source restores `sourceEntryBuffer`, and typing/backspace exits source navigation. |
| Refactored mapping semantics | Assert `targetValue = null` enters edit mode with empty buffer plus `defaultSourceValue` ghost text; assert literal `targetValue = defaultSourceValue` enters edit mode with that value pre-filled and commits back as a literal string. |
| Derived ghost semantics | Assert frame 12b Backspace changes `APPLE` to `APPL`, returns focus to token input, clears source navigation, and renders ghost `E`; assert submitting stores literal `APPL` and re-entering edit mode shows no ghost. |
| Portability of page keys | In a test harness that does not distinguish shifted arrows, assert `PgUp`/`PgDn` perform page movement and normal arrows still perform one-row movement. |
| Unsupported key handling | Send an unlisted control sequence in each mode and assert root state and render output do not change. |
| Readline-style key aliases | Assert `ctrl+j`/`ctrl+m` dispatch as `Enter`, `ctrl+i` as `Tab`, `ctrl+?` as Backspace, `ctrl+p`/`ctrl+n` as up/down, `ctrl+b`/`ctrl+f` as left/right, `ctrl+a`/`ctrl+e` as line-boundary movement, `ctrl+d` as forward delete, `ctrl+k`/`ctrl+u`/`ctrl+w` as filter/edit line deletion, and representative readline search/yank/macro functions are no-ops. |
| Edit filter preservation | Enter edit from an active text filter, cancel or submit, type another browsing character, and assert it inserts at the preserved filter cursor. |
| Invalid printable edit characters | Type `!` in `EDITING`; assert it is inserted into `edit.buffer`, validation is `INVALID`, `✗` renders, `Enter` is gated, and no sanitization occurs. |

## 11. Non-Goals and Assumption Resolution

### 11.1 Non-Goals

- This contract does not define color values.
- This contract does not define mouse behavior.
- This contract does not define alternate datasets beyond the fields and algorithms above.
- This contract does not define persistence format after `ACCEPTED`, `SKIPPED`, or `SIGINT`.
- This contract does not require a specific terminal library.
- This contract does not implement a full readline editor. It defines only the readline-style aliases
  and no-op families listed in `5.1 Readline-Style Input Bindings`.
- This contract does not define a wall-clock duration for max-length error fade. Implementers only need
  the immediate render and deterministic clearing behavior defined in validation.

### 11.2 Assumption Resolution Log

| Former assumption/question | Resolution |
|---|---|
| ASCII case-insensitive filtering was an assumption. | Resolved in `3.3 Filter Query Parser`: matching MUST be ASCII case-insensitive, lowercase queries MUST match uppercase targets, and tests MUST include a lowercase query. |
| `ctrl+c` in `EDITING` was inferred from the header. | Resolved in `4.2 Transition Table` and `5. Key Handling Matrix`: `ctrl+c` in `EDITING` MUST cancel edit, preserve filter, clear edit state, and return to `BROWSING`. |
| `ctrl+c` in accept confirmation was inferred from the header. | Resolved in `4.2 Transition Table` and `5. Key Handling Matrix`: `ctrl+c` in `CONFIRMING ACCEPT` MUST enter exit confirmation (same as `ctrl+c` in `BROWSING`); only `CONFIRMING EXIT` arms second-`ctrl+c` SIGINT. |
| Leaving accept confirmation with `NO` selected was inferred from frames 7a to 7b. | Resolved in `4.2 Transition Table` and `8.4 Confirming Scrolling`: `Enter` with `choice == NO` MUST return to `BROWSING`, and selected row MUST become the first visible row at the current `scrollOffset`. |
| Frame 13 preserving filter `1` before appending `2` had an omitted intermediate path. | Resolved in `7.1 Entering Edit Mode`: entering, submitting, or cancelling `EDITING` MUST preserve filter state and cursor, so returning to browsing and typing `2` inserts at the preserved end cursor. |
| Readline shortcuts other than Backspace and `ctrl+h` were undefined. | Resolved in `5.1 Readline-Style Input Bindings` and `11.1 Non-Goals`: common readline aliases are normalized to filter/edit input events, and unsupported readline families are explicit no-ops. |
| `Shift+↑`/`Shift+↓` portability was undefined. | Resolved in `5. Key Handling Matrix`: implementations MUST support `PgUp`/`PgDn` as reliable page equivalents and MUST NOT reinterpret indistinguishable normal arrows as page movement. |
| Max-length error fade timing was undefined. | Resolved in `7.5 Validation` and `11.1 Non-Goals`: immediate render is required, deterministic clearing is defined, and wall-clock fade duration is out of scope. |
| Printable invalid characters such as `!` in edit mode were undefined beyond validation failure. | Resolved in `7.2 Streaming Insert Algorithm`: invalid printable characters MUST insert into `edit.buffer`, produce validation `INVALID`, render `✗`, gate submit, and must not be silently sanitized or discarded except by the configured maximum display width. |

## 12. Implementation Targets and Development Method

### 12.1 Language/Runtime Target

- **Implementation Language**: Python 3.
- **Runtime Environment**: Standard Unix/macOS terminal environments. The application must not assume specific proprietary terminal features beyond standard ANSI escape sequences.
- **Preferred TUI Library**: The architecture requires the use of `blessed` for input/rendering. `blessed` is chosen because it provides raw terminal capabilities (input capturing, precise Unicode string width calculations, and basic ANSI styling) without imposing a conflicting widget lifecycle or state management architecture. This strictly aligns with the requirement for pure, centralized root state projections.

### 12.2 Testing and Execution Method

- **TDD/BDD Execution**: Implementers MUST follow Test-Driven Development (TDD) or Behavior-Driven Development (BDD). Failing tests MUST be written first for each behavior slice before implementing the logic.
- **Golden-Render Tests**: The implementation MUST include golden-render tests for storyboard frames 1a through 15.
- **Behavioral Tests**: The implementation MUST include behavioral tests covering all state transitions, key handling, filtering logic, editing algorithms, input validation, scrolling limits, and collision resolution semantics defined in this specification.
- **Local Execution**: All tests MUST be runnable locally with a single documented command (e.g., `pytest`).
- **Acceptance Criteria**: Every implementation story or task MUST include specific acceptance tests before the code implementation begins.

### 12.3 Story Handoff Expectations

- **Behavioral Slicing**: Epics and stories MUST be sliced by testable behavior (e.g., "Filter by text", "Handle Backspace in Edit Mode"), not solely by UI component (e.g., "Implement the Footer").
- **Acceptance Criteria**: Each story MUST include clear Given/When/Then acceptance criteria.
- **Contract Traceability**: Each story MUST identify the specific golden frames or behavioral contracts from this specification that it covers and implements.
