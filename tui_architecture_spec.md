# Gnubeans TUI Prototype: Software Design Specification

## 1. Domain Models

The application operates on core business entities. These domain models are decoupled from UI state and represent a generic mapping/resolution vocabulary so the UX can be abstracted across different batch resolution use cases.

```typescript
// Global Enums & Types
enum AppMode { BROWSING, FILTERING, EDITING, CONFIRMING }

type ValidationStatus = 'VALID' | 'INVALID' | 'UNCHECKED';

// Core Business Entities
interface ResolutionSource {
  type: string;            // e.g., "cmdty_id", "category", "raw_string"
  original: string | null; // e.g., "AT&T", "OldName", or null for "(not set)"
  sanitized?: string;      // e.g., "AT-T", "NewName"
}

interface ResolutionMapping {
  id: number;              // Ordinal
  targetValue: string;     // The proposed/edited target value
  isCollision: boolean;    // Tracks unresolved state
  sources: ResolutionSource[];
}
```

---

## 2. Component Specifications

The UI follows a strict reactive component tree architecture. Data is separated into **Props** (inherited from parents, read-only) and **Local State** (owned and mutated internally). Events flow up; props flow down.

### 2.1 Root Layout
The "Smart Container" that manages vertical stacking, holds the global UI state, and orchestrates cross-component events.

- **Child Hierarchy:** `HeaderComponent` → `PromptComponent` → `TableComponent` → `ShortcutsFooter`.
- **Data Contracts:**
  - **Local State:** 
    - `mode: AppMode`
    - `mappings: ResolutionMapping[]`
    - `windowHeight: number`
    - `filterQuery: string`
- **Events:**
  - **Terminal Resize (`SIGWINCH`)**
    - **Trigger**: OS sends `SIGWINCH`.
    - **State Mutation**: `LocalState.windowHeight = newHeight`.
    - **Reaction**: Triggers a global layout recalculation. Passes the new height down to children.
  - **Global Keyboard Dispatcher (Input Routing Matrix)**
    - **Trigger**: Any raw terminal keystroke caught by the global event loop.
    - **Reaction**: The RootLayout intercepts and routes keys based on `LocalState.mode`:
      - **BROWSING**: 
        - `↑` / `↓` / `PgUp` / `PgDn`: Routed to `TableComponent` to paginate.
        - Alphanumerics, `Tab`, `!`, `↵`: Mutates `mode = FILTERING` (and sets `filterQuery`), triggering a prop cascade.
      - **FILTERING**:
        - Alphanumerics, `Backspace`, line-editing commands (e.g., `^W`, `^U`): Mutates `filterQuery`, triggering a prop cascade.
        - `↑` / `↓`: Routed to `TableComponent` to move the `▸` selection pointer.
        - `PgUp` / `PgDn`: Routed to `TableComponent` to paginate and reposition the selection pointer.
        - `↵` (if matches exist): Mutates `mode = EDITING`.
        - `esc`: Clears `filterQuery` and mutates mode to `CONFIRMING` (if 0 unresolved collisions) or `BROWSING`.
      - **EDITING**:
        - Alphanumerics, `Backspace`, line-editing commands: Routed to `TableComponent` to mutate `LocalState.editTokenBuffer`.
        - `↑` / `↓`: Routed to `TableComponent` to autofill the buffer from source rows.
        - `↵` / `esc`: Routed to `TableComponent` to submit or cancel the edit.
      - **CONFIRMING**:
        - `←` / `→` or `y`/`n` (case-insensitive): Mutates `LocalState.acceptAllConfirm`.
        - `↵`: If `acceptAllConfirm` is `Y`, submits the final batch resolution. If `N`, mutates mode to `FILTERING` (if `filterQuery` is not empty) or `BROWSING`.
        - `↑` / `↓` / `PgUp` / `PgDn`: Routed to `TableComponent` to paginate.
  - **Exiting Edit Mode (Submit or Cancel)**
    - **Trigger**: TableComponent emits a submit or cancel event.
    - **State Mutation**: If submitted, updates `LocalState.mappings`. The fallback mode is then determined:
      - If all collisions across the mapping array are resolved, `LocalState.mode = CONFIRMING`.
      - Else, `LocalState.mode = FILTERING` (conserving the search results and maintaining the user's row selection pointer).

### 2.2 Header Component
Displays summary statistics at the top of the viewport.

- **Data Contracts**:
  - **Props**: `mappings: ResolutionMapping[]` (Inherited from `RootLayout.mappings`)
- **Template**: `❯ Reviewing {total} items. {unresolved} unresolved collision{s}.`
- **Styling**: `❯ ` is **bold**. `{s}` pluralization logic applies ("s" for != 1, "" for 1).

### 2.3 Prompt Component
A dynamic area providing context or interactive prompts.

- **Data Contracts**:
  - **Props**: `mode: AppMode`, `filterQuery: string` (Inherited from `RootLayout`)
  - **Local State**: `acceptAllConfirm: boolean` (Default `true`)
- **Templates & Styling**:
  - **Mode: BROWSING** (and empty FILTERING)
    - **Template**: `  Filter: Tab to view collisions`
    - **Styling**: Padding left: 2. `Filter: ` (normal). `T` (**reverse-video**). `ab to view collisions` (dimmed).
  - **Mode: FILTERING (Active)**
    - **Template**: `  Filter: {Props.filterQuery}_`
    - **Styling**: Padding left: 2. `_` is a **reverse-video** space representing the cursor.
  - **Mode: EDITING**
    - **Template**: `  Editing mapping for "{original_target}":`
    - **Styling**: Padding left: 2. Normal text.
  - **Mode: CONFIRMING**
    - **Template**: `  Accept all? [{y_n}]`
    - **Styling**: Padding left: 2. Active boolean choice reflects `LocalState.acceptAllConfirm` via **uppercase and bold** styling (e.g., `[**Y**/n]` or `[y/**N**]`).
- **Events**:
  - **Typing the Filter Query**
    - **Trigger**: User types any alphanumeric character `[char]` or `Backspace` when `Props.mode === FILTERING`.
    - **Reaction**: Emits request to `RootLayout` to append `[char]` to, or remove a character from, `filterQuery`.
  - **Toggle Confirmation**
    - **Trigger**: User presses `←`, `→`, or types `y`/`n` (case-insensitive) when `Props.mode === CONFIRMING`.
    - **State Mutation**: Sets or toggles `LocalState.acceptAllConfirm` accordingly.
  - **Submitting Confirmation**
    - **Trigger**: User presses `↵` when `Props.mode === CONFIRMING`.
    - **Reaction**: If `LocalState.acceptAllConfirm` is `Y`, emits Final Batch Submission. If `N`, emits request to `RootLayout` to fall back to `FILTERING` (if `filterQuery` is not empty) or `BROWSING`.

### 2.4 Table Component (and TableRow)
The core data view, managing its own complex pagination and editing lifecycles.

- **Child Hierarchy:** `TableHeader` → `TableBody` (List of `TableRow`s).
- **Data Contracts**:
  - **Props**: `mappings: ResolutionMapping[]`, `mode: AppMode`, `filterQuery: string`, `availableHeight: number` (Inherited from `RootLayout`)
  - **Local State**: 
    - `selectedIndex: number | null` (null when `Props.mode` is BROWSING or CONFIRMING)
    - `scrollOffset: number`
    - `editTokenBuffer: string`
    - `editValidationStatus: ValidationStatus`
    - `editErrorMessage: string | null`
- **Templates & Styling:**
  - **Placement & Margins**: Rendered with 1 empty line of vertical margin above and below, separating it visually from the Prompt and Footer.
  - **Table Header**: `   #   Target Value               Source Data`
  - **Columns**: `0-2`: Indicator spacing | `3-4`: `#` Ordinal | `5-6`: Spacing | `7`: Collision indicator (`!` or space) | `8-33`: Target (26 chars max) | `34+`: Source.
  - **TableRow (BROWSING / FILTERING / CONFIRMING)**
    - **Template**: `{ind} {ord}  {col_ind}{target_padded} {source_string}`
    - **Styling**: `{ind}` is `▸` at col 1 if it matches `LocalState.selectedIndex`. `{col_ind}` is `!` if the mapping's `isCollision` is true. Text matching `Props.filterQuery` is **bolded**.
  - **TableRow (FILTERING - Empty Results)**
    - **Template**: An empty, blank row is rendered directly beneath the table headers.
    - **Styling**: No data or pointers are rendered.
  - **TableRow (EDITING - Active Row)**
    - **Template Line 1**: `{ind} {ord}  {col_ind}{input}{cursor} {icon} {pad} {src_ind} ┃ {source_1}`
    - **Template Line 2+**: `{err_msg} {pad} {src_ind} ┃ {source_n}`
    - **Styling**: `{ind}` starts as `▸` and jumps to a source line (via `{src_ind}`) ONLY upon arrow keypress or explicit buffer match. `{cursor}` is a reverse-video block `_`. `{icon}` caps at col 33 and reflects intrinsic buffer validity (`✓` or `✗`). `{err_msg}` renders on subsequent lines if the error stack is not empty.
  - **TableRow (EDITING - Inactive Rows)**
    - **Styling**: All other unedited rows become **super dim**.

- **Events:**
  - **Reacting to Prop Updates (Filtering & Recalculation)**
    - **Trigger**: `Props.filterQuery` or `Props.mappings` updates from the parent.
    - **State Mutation**: The table automatically re-evaluates all mappings against `Props.filterQuery` to derive the visible `filteredRows`.
    - **Reaction**: If the row at `LocalState.selectedIndex` is filtered out (e.g. after a submit), or if this is the initial switch to `FILTERING`, `LocalState.selectedIndex` clamps to `min(LocalState.selectedIndex || 0, filteredRows.length - 1)` so the `{ind}` pointer (`▸`) falls seamlessly onto the nearest valid row.
  - **Reacting to Terminal Resize (Viewport Recalculation)**
    - **Trigger**: `Props.availableHeight` updates from the parent (ultimately via OS `SIGWINCH`).
    - **Reaction**: Recalculates the maximum number of visible rows. If the terminal shrinks and the active `LocalState.selectedIndex` (or the actively edited row) falls outside the new visible bounds, the table automatically adjusts `LocalState.scrollOffset` to guarantee the active row remains visible on-screen.
  - **Entering Edit Mode**
    - **Trigger**: User presses `↵` on a selected row when `Props.mode === FILTERING`.
    - **State Mutation**: Emits request to `RootLayout` to set `mode = EDITING`. Mutates `LocalState.editTokenBuffer` to initialize. `LocalState.selectedIndex` locks.
  - **Typing in Edit Mode**
    - **Trigger**: User types an alphanumeric character `[char]` or erases chars during `EDITING`.
    - **State Mutation**: 
      - *Clear transient state*: Empty `LocalState.editErrorMessage` and cancel async UI timers.
      - *If typing*: Append `[char]` to `LocalState.editTokenBuffer` (max 24 chars).
      - *Transient Feedback*: If capped at 24 chars, discard the keystroke and set `LocalState.editErrorMessage = "Error: 24 chars max"`. Additionally, momentarily flash `✗` in the `{icon}` slot. Trigger a 2000ms async timer to clear the message and restore the `{icon}` to its intrinsic validation state.
      - *Run intrinsic validation*: Update `LocalState.editValidationStatus`.
  - **Navigation & Pagination**
    - **Trigger**: User presses `↑`, `↓`, `PgUp`, or `PgDn`.
    - **State Mutation**: 
      - In `BROWSING`/`CONFIRMING`: Paginates `LocalState.scrollOffset`.
      - In `FILTERING`: `↑` / `↓` adjusts `LocalState.selectedIndex`, shifting `LocalState.scrollOffset` dynamically if selection moves off-screen. `PgUp` / `PgDn` paginates `LocalState.scrollOffset` by the viewport height and automatically sets `LocalState.selectedIndex` to the first visible row of the newly drawn page.
      - In `EDITING`: `↑` / `↓` autofills `LocalState.editTokenBuffer` with the string from the adjacent source data row.
  - **Submitting or Canceling an Edit**
    - **Trigger**: User presses `↵` (when `LocalState.editValidationStatus === VALID`) or `esc`.
    - **Reaction**: If submitted, emits the updated mapping to `RootLayout`. If canceled, discards changes. Emits an exit signal so `RootLayout` can transition to the appropriate fallback mode. Clears local edit states.
  - **Canceling a Filter**
    - **Trigger**: User presses `esc` during `FILTERING`.
    - **Reaction**: Emits request to `RootLayout` to explicitly clear `filterQuery` and fall back to either `CONFIRMING` (if 0 unresolved collisions) or `BROWSING` mode.

### 2.5 Shortcuts Footer
Context-aware keybindings that update reactively.

- **Data Contracts**:
  - **Props**: `mode: AppMode` (Inherited from `RootLayout`)
- **Placement**: Anchored exactly 2 lines below the last drawn row of `TableBody`.
- **Templates**:
  - *Browsing*: `  Type to filter  ·  ↑↓ prev/next page  ·  ↵ select row`
  - *Filtering*: `  Type to filter  ·  ↑↓ prev/next row  ·  ↵ edit selected`
  - *Editing*: `  Enter a value  ·  ↑↓ select  ·  ↵ submit  ·  esc cancel`
  - *Empty Filter*: `  Error: no matching rows  ·  esc back`
  - *Confirming (Y)*: `  ↑↓ prev/next page  ·  ↵ confirm`
  - *Confirming (N)*: `  ↑↓ prev/next page  ·  ↵ edit mappings`
