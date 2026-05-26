---
stepsCompleted: [1, 2]
inputDocuments:
  - "/Users/phlip/Projects/gnubeans-tui-prototype/tui_architecture_spec.md"
  - "/Users/phlip/Projects/gnubeans-tui-prototype/_bmad-output/planning-artifacts/architecture.md"
---

# gnubeans-tui-prototype - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for gnubeans-tui-prototype, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The TUI MUST browse a dataset of entity mappings in a stable display order derived from default source value, original source value, and ordinal.

FR2: The TUI MUST model root application state centrally, including mode, mappings, filter, selection, edit state, confirmation state, terminal state, and result state.

FR3: The TUI MUST derive visible rows, collision groups, unresolved collision counts, prompt text, footer text, validation display positions, ghost text, and render lines from root state rather than storing them as component state.

FR4: The TUI MUST support configurable entity labels, mapping labels, column labels, source labels, prompts, created output text, target validation rules, and target maximum display width.

FR5: The TUI MUST initialize mappings from caller-supplied sources, default source labels, original values, sanitized values, and optional target overrides without computing or mutating source sanitization.

FR6: The TUI MUST compute each source effective value as `sanitizedValue ?? originalValue`, derive default source values, and derive current target values as `targetValue ?? defaultSourceValue`.

FR7: The TUI MUST detect collision groups by equal derived current target values and render unresolved collision indicators for all rows in those groups.

FR8: The TUI MUST recompute collisions live while editing so collision indicators and zero-collision confirmation eligibility update immediately.

FR9: The TUI MUST provide browsing-mode filter input with cursor-aware printable insertion, deletion, cursor movement, line editing, and ASCII case-insensitive matching.

FR10: The TUI MUST support a collision-only metafilter toggled by `Tab` or `!` in browsing mode and rendered as a leading `!` in the prompt.

FR11: The filter matcher MUST match only ordinal strings and current target tokens, never source labels, source original values, source sanitized values, or source display text.

FR12: Empty filtered results MUST clear selection, render one blank table body line, and display the no-matching-rows footer.

FR13: Selection MUST track mappings by stable ordinal, clamp to visible rows after filter changes, and keep the selected row visible during browsing movement.

FR14: Browsing mode MUST handle row movement, page movement, entering edit mode, accept confirmation entry when collisions are zero, blocked accept entry when collisions remain, and exit confirmation entry.

FR15: Edit mode MUST initialize from the selected mapping with an empty buffer when `targetValue` is null and with the literal target value when present.

FR16: Edit mode MUST preserve the active browsing filter, metafilter, and filter cursor across entering, submitting, and cancelling edits.

FR17: Edit mode MUST derive ghost suffixes from the default source value when the buffer is a prefix at the cursor end and the mapping has no literal target override.

FR18: Edit mode MUST support cursor-aware printable insertion, deletion, readline-style editing operations, tab autocomplete from ghost text, and submit gating through validation.

FR19: Invalid printable edit characters MUST be inserted when within the configured maximum display width, produce invalid validation state, render the invalid icon, and block submit.

FR20: Over-limit edit input MUST be discarded, show the configured max-length error immediately, keep the capped validation icon position, and clear deterministically on the next accepted edit-related change or mode exit.

FR21: Edit mode MUST support source-list navigation with reversible entry buffers, source pointer movement, autofill from active source effective values, and exit from source navigation on typing or deletion.

FR22: Committing a valid edit MUST store the submitted concrete value literally in `targetValue`, even when it equals the default source value.

FR23: A valid edit commit that resolves the final collision MUST enter accept confirmation with choice reset to `NO`.

FR24: Confirmation mode MUST distinguish accept confirmation from exit confirmation with separate prompts, result semantics, and `ctrl+c` behavior.

FR25: Every y/n confirmation MUST default to `NO` on entry through root state initialization, while preserving the selected choice between key events during the active confirmation visit.

FR26: Accept confirmation MUST support y/n choice changes, left/right toggling, scroll-only row movement, page scrolling, returning to browsing on `NO`, accepting on `YES`, cancelling on `ctrl+c`, and storyboard-compatible frame 6 footer rendering.

FR27: Exit confirmation MUST support y/n choice changes, left/right toggling, scroll-only row movement, page scrolling, returning to browsing on `NO`, skipping on `YES`, and SIGINT on second armed `ctrl+c`.

FR28: The key dispatcher MUST implement the specified key handling matrix for browsing, editing, accept confirmation, and exit confirmation.

FR29: The input layer MUST normalize the specified readline-style aliases to TUI actions and treat unsupported readline/search/yank/macro/vi families as no-ops.

FR30: Unsupported keys and unlisted control sequences MUST leave root state and rendered output unchanged.

FR31: The renderer MUST project the canonical 15x75 storyboard frame geometry, including header, prompt, blank separators, table header, table body, footer, and blank filler lines.

FR32: The renderer MUST render inline without entering the alternate screen buffer and MUST clear all previously drawn frame lines on each redraw.

FR33: The renderer MUST use Unicode display width rather than byte length for layout, cursor placement, truncation decisions, and golden geometry.

FR34: The renderer MUST apply the specified column positions for row cursor, ordinal, collision marker, token, edit cursor, validation icon, source divider, source text, and source pointer.

FR35: The renderer MUST render configured header, prompt, footer, edit, source display, confirmation, empty-result, layout-blocked, and terminal accepted-output templates.

FR36: The renderer MUST strip ANSI from geometry assertions while preserving inspectable bold, dim, and reverse-video style spans for tests.

FR37: Body capacity, footer separator visibility, scroll offsets, anchored browsing/editing body allocation, confirmation windows, and page sizes MUST be derived from terminal dimensions.

FR38: Editing layout MUST keep the edited row's full source block visible when possible and render `LAYOUT_BLOCKED` when the edit block cannot fit.

FR39: `LAYOUT_BLOCKED` MUST preserve editing state, render the blocked footer, ignore hidden edit mutations while blocked, and return to normal edit rendering when terminal height is sufficient.

FR40: Accepted terminal result rendering MUST show the configured created message on row 1, `❯` on row 2, and cleared blank lines through the frame.

FR41: The implementation MUST include the storyboard commodity fixture configuration and dataset needed to reproduce frames 1a through 15.

### NonFunctional Requirements

NFR1: The implementation MUST use Python 3.

NFR2: The implementation MUST use the `blessed` library for terminal input, ANSI styling, terminal capabilities, and display width support.

NFR3: The TUI MUST render inline in the current terminal stream and MUST NOT use the alternate screen buffer.

NFR4: Mutable application state MUST be centralized in root state; reducers, selectors, and renderers MUST remain pure except for the event loop side effects.

NFR5: State data structures MUST be immutable Python dataclasses, with updates returned through replacement rather than mutation.

NFR6: Reducer logic MUST NOT import or use `blessed`, terminal I/O, or ANSI rendering concerns.

NFR7: Renderer logic MUST NOT mutate application state.

NFR8: Selectors MUST be the only layer responsible for derived display math, visible-row selection, collision derivation, ghost text, and body allocation.

NFR9: The synchronous event loop MUST be the sole owner of terminal side effects, `term.inkey()`, output flushing, and process exit handling.

NFR10: Terminal cleanup MUST be protected by `try/finally` or equivalent safety handling so terminal modes are restored before tracebacks or exits.

NFR11: Layout MUST be computed by Unicode display width, and ANSI style sequences MUST NOT count toward display width.

NFR12: Lines MUST NOT wrap; over-width logical lines remain single-line terminal content.

NFR13: Tests MUST be runnable locally with a single documented command such as `pytest`.

NFR14: Implementation MUST follow strict TDD/BDD: failing tests are written and observed before production code for each behavior slice.

NFR15: Golden-render tests MUST cover all storyboard frames 1a through 15.

NFR16: Behavioral tests MUST cover state transitions, key handling, filtering, editing algorithms, validation, scrolling limits, layout blocking, source navigation, confirmation flows, unsupported keys, readline aliases, and collision semantics.

NFR17: Stories MUST be sliced by testable behavior rather than by UI component and include Given/When/Then acceptance criteria.

### Additional Requirements

- The first implementation story MUST initialize the Python project structure and dependencies, including `blessed`, `pytest`, and `pytest-bdd`.
- The implementation SHOULD follow the documented module boundaries: `lib/config.py`, `lib/state.py`, `lib/actions.py`, `lib/reducer.py`, `lib/selectors.py`, `lib/renderer.py`, and `lib/loop.py`.
- Tests SHOULD live under top-level `tests/`, with BDD features under `tests/features/`, step definitions under `tests/step_defs/`, and focused unit tests under `tests/unit/`.
- Action types MUST be typed Python dataclasses rather than untyped dictionaries.
- State class fields and files MUST use Python `snake_case`; dataclass/type definitions MUST use `PascalCase`; selector functions MUST be prefixed with `select_`.
- The data flow MUST be `loop` reads `term.inkey()` -> dispatches typed action -> reducer returns new state -> selectors compute view -> renderer projects terminal frame -> loop writes output.
- The project MUST provide a storyboard fixture config matching commodity names, labels, prompts, source labels, target policy, and the 11-row dataset.
- The commodity target policy MUST enforce a 24-column max display width, start/end character rules, allowed character rules, and documented error precedence.
- Implementation MUST support equivalent configurations for other entity types and source labels without changing state machine, render pipeline, key handling, or component internals.
- Source normalization remains outside the TUI component; callers supply `originalValue` and optional `sanitizedValue`.
- Golden tests MUST assert app state, visible rows, prompt/footer, render geometry, and style spans.
- Golden tests MUST include frame-specific requirements for frames 1a, 1b, 2, 3, 4, 5, 6, 7a, 7b, 7c, 8, 9, 10, 11, 12a, 12b, 13, 14, and 15.
- Defect-prevention tests MUST cover distinct confirmation intents, confirmation default-on-entry behavior, confirmation choice persistence within a visit, `ctrl+c` dispatching, filtering scope, edit insertion with ghost text, domain model semantics, stable sorting, deterministic layout, injected validation, source sanitization boundaries, source selection, literal target semantics, derived ghost behavior, page-key portability, unsupported keys, readline aliases, filter preservation, and invalid printable edit characters.
- The implementation MUST not require background asynchronous data loading for the current prototype.

### UX Design Requirements

UX-DR1: The TUI MUST reproduce the storyboarded frames 1a through 15 as golden-rendered visual acceptance examples.

UX-DR2: The canonical visual fixture MUST support a 15-row by 75-column frame with exact row allocation and column geometry.

UX-DR3: Header text MUST communicate review count, collision count when applicable, submit/cancel shortcuts, or exit shortcut according to state.

UX-DR4: Prompt text MUST communicate filtering, editing, accept confirmation, or exit confirmation state using the configured labels and prompts.

UX-DR5: Footer text MUST communicate the currently valid keyboard affordances and errors for browsing, editing, confirming, empty results, and blocked layout states.

UX-DR6: Browsing rows MUST visually identify the selected row with `▸` and unresolved collision rows with `!`.

UX-DR7: Editing rows MUST visually distinguish token-input focus, source-list focus, ghost text, validation icons, source dividers, and inactive context rows.

UX-DR8: Confirmation views MUST remove row cursors, keep the review table scrollable, and visually emphasize the active y/n choice.

UX-DR9: Text filtering MUST render a visible prompt cursor at the filter cursor position, including a reverse-video trailing space at the end.

UX-DR10: Edit input MUST render a reverse-video cursor over the current character, next ghost character, or trailing space depending on cursor and ghost state.

UX-DR11: Source displays MUST distinguish missing sources, original values, and caller-supplied sanitized values using the specified text formats.

UX-DR12: Empty filter results MUST render a blank body row and no selected row cursor.

UX-DR13: Layout-blocked editing MUST visibly instruct the user to enlarge the terminal and preserve normal cancel affordances.

UX-DR14: The accepted final frame MUST replace the interactive table with the configured created-message output and cleared frame lines.

UX-DR15: Visual styling MUST expose bold, dim, and reverse-video spans for test inspection without affecting geometry.

### FR Coverage Map

FR1: Epic 1 - Stable mapping review order
FR2: Epic 1 - Root state model
FR3: Epic 1 - Derived selectors
FR4: Epic 1 - Configurable labels/prompts/policies
FR5: Epic 1 - Caller-supplied source initialization
FR6: Epic 1 - Effective/default/current target derivation
FR7: Epic 1 - Collision group detection
FR8: Epic 3 - Live collision recomputation while editing
FR9: Epic 2 - Browsing filter input
FR10: Epic 2 - Collision-only metafilter
FR11: Epic 2 - Filter matching scope
FR12: Epic 2 - Empty result behavior
FR13: Epic 2 - Selection and scrolling identity
FR14: Epic 2 - Browsing key transitions
FR15: Epic 3 - Edit initialization
FR16: Epic 3 - Filter preservation through edit
FR17: Epic 3 - Ghost suffix derivation
FR18: Epic 3 - Edit input and submit gating
FR19: Epic 3 - Invalid printable insertion
FR20: Epic 3 - Over-limit edit handling
FR21: Epic 3 - Source-list navigation
FR22: Epic 3 - Literal target commit
FR23: Epic 3 - Auto accept confirmation on final collision resolution
FR24: Epic 4 - Distinct confirmation kinds
FR25: Epic 4 - Confirmation default-on-entry and in-visit choice persistence
FR26: Epic 4 - Accept confirmation behavior
FR27: Epic 4 - Exit confirmation behavior
FR28: Epic 2 - Key matrix dispatch
FR29: Epic 2 - Readline alias normalization
FR30: Epic 2 - Unsupported key no-ops
FR31: Epic 5 - Canonical frame geometry
FR32: Epic 5 - Inline redraw and clearing
FR33: Epic 5 - Unicode display width layout
FR34: Epic 5 - Column positioning
FR35: Epic 5 - Render templates
FR36: Epic 5 - ANSI/style testability
FR37: Epic 5 - Body capacity and dynamic layout
FR38: Epic 5 - Editing anchor visibility
FR39: Epic 5 - Layout blocked behavior
FR40: Epic 4 - Accepted terminal result
FR41: Epic 1 - Storyboard fixture dataset/config

## Epic List

### Epic 1: Review Mapping Data Reliably

Users can load the storyboard commodity fixture, see mappings in deterministic order, understand source/default/target values, and identify unresolved collisions from derived state.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR41

### Epic 2: Browse, Filter, and Navigate Mappings

Users can narrow the mapping list, view collision-only rows, move selection predictably, page through rows, handle empty results, and rely on unsupported keys doing nothing.

**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14, FR28, FR29, FR30

### Epic 3: Edit Target Tokens and Resolve Collisions

Users can edit mappings with ghost text, validation, max-length behavior, source autofill, literal commit semantics, filter preservation, and live collision recomputation through final collision resolution.

**FRs covered:** FR8, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23

### Epic 4: Confirm, Exit, and Complete the Review

Users can submit or exit the review through distinct confirmation flows, with correct defaults, scrolling, cancellation, skip, SIGINT, and final accepted output behavior.

**FRs covered:** FR24, FR25, FR26, FR27, FR40

### Epic 5: Render the Terminal Experience Exactly

Users get the storyboarded inline terminal UI with exact geometry, styling, clearing behavior, dynamic body allocation, layout blocking, and golden-render coverage.

**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36, FR37, FR38, FR39

## Epic 1: Review Mapping Data Reliably

Users can load the storyboard commodity fixture, see mappings in deterministic order, understand source/default/target values, and identify unresolved collisions from derived state.

### Story 1.1: Initialize Python TDD Project Skeleton

As a developer,
I want a Python 3 project skeleton with the required TUI and test dependencies,
So that every behavior slice can be implemented through strict failing-first TDD/BDD.

**Acceptance Criteria:**

**Given** the repository has no implementation skeleton for the TUI component
**When** the developer starts this story
**Then** they first add a failing test that proves the expected package/module entry points do not yet exist
**And** they capture the failing test output before writing production code.

**Given** the failing skeleton test exists
**When** the developer implements the minimum project structure
**Then** the repository contains the agreed module boundaries: `lib/config.py`, `lib/state.py`, `lib/actions.py`, `lib/reducer.py`, `lib/selectors.py`, `lib/renderer.py`, and `lib/loop.py`
**And** test directories exist for unit, BDD, and golden-render coverage.

**Given** the project dependencies are installed
**When** the developer runs the documented local test command
**Then** Python 3, `blessed`, `pytest`, and `pytest-bdd` are available
**And** the skeleton test passes.

**Given** the architecture requires pure core logic
**When** the skeleton modules are created
**Then** `reducer.py`, `selectors.py`, and `state.py` contain no terminal I/O or `blessed.Terminal` usage
**And** any `blessed` usage is reserved for terminal-facing modules such as `renderer.py` or `loop.py`.

**Given** future stories require repeatable verification
**When** this story is complete
**Then** the repository documents the single local test command, such as `pytest`
**And** the test layout is ready for failing-first unit, BDD, and golden-render tests.

### Story 1.2: Model Root State and Storyboard Fixture Data

As a developer,
I want immutable root state models and the storyboard commodity fixture represented in Python,
So that the TUI can start from a complete, testable review state without hidden component state.

**Acceptance Criteria:**

**Given** Story 1.1 has established the project skeleton
**When** the developer starts this story
**Then** they first write failing tests for the required root state dataclasses, fixture config, and fixture dataset
**And** no production state model code is written until those tests fail.

**Given** the TUI state model is implemented
**When** tests instantiate the root app state
**Then** it includes config, mode, mappings, filter, selection, edit, confirmation, terminal, and result state
**And** `edit` is `None` outside editing mode.

**Given** confirmation state is part of the root app state
**When** tests inspect the confirmation model
**Then** it includes confirmation kind, selected choice, and second-`ctrl+c` arming state
**And** the model supports reducer-owned choice between key events without requiring the renderer to initialize, reset, or store confirmation choice.

**Given** the storyboard commodity fixture is loaded
**When** tests inspect the fixture config
**Then** it contains the commodity entity labels, mapping labels, target/source column labels, accept/exit prompts, created message, source labels `cmdty_id` and `user_symbol`, and the commodity target policy hook.

**Given** the storyboard fixture dataset is loaded
**When** tests inspect mappings 1 through 11
**Then** all 11 mappings from `tui_architecture_spec.md` are present with their required ordinals, source labels, original values, sanitized values, default source labels, and initial `targetValue = None`
**And** row 1 includes both `cmdty_id: "AAPL"` and `user_symbol: "APPLE"`
**And** rows 2 and 3 initialize to the same current target candidate `AT-T` for collision testing
**And** row 4 includes the caller-supplied sanitized value that produces `C100-F`
**And** rows 5 through 11 are present for filtering, scrolling, and golden-render coverage.

**Given** the architecture requires caller-owned source normalization
**When** tests inspect source records
**Then** each source stores caller-supplied `originalValue` and `sanitizedValue` only
**And** the TUI fixture loader does not compute or mutate sanitized values.

**Given** the implementation uses immutable state objects
**When** tests attempt to mutate state dataclass fields directly
**Then** mutation fails or is prevented by frozen dataclass behavior
**And** future changes must be expressed through explicit state replacement.

### Story 1.3: Derive Source, Default, and Target Values

As a developer,
I want pure selectors for source and target derivation,
So that review behavior is computed consistently from root state without duplicated mutable fields.

**Acceptance Criteria:**

**Given** Story 1.2 has implemented immutable state and fixture data
**When** the developer starts this story
**Then** they first write failing selector tests for source effective values, default source values, current target values, active sources, and invalid fixture invariants
**And** selector implementation begins only after the tests fail.

**Given** a source has both `originalValue` and `sanitizedValue`
**When** the effective source value selector is called
**Then** it returns `sanitizedValue`
**And** it does not mutate either stored source field.

**Given** a source has `sanitizedValue = None`
**When** the effective source value selector is called
**Then** it returns `originalValue`.

**Given** a mapping has a valid `defaultSourceLabel`
**When** the default source selector is called
**Then** it returns the matching source from that mapping
**And** the default source value selector returns that source's effective value.

**Given** a mapping has `targetValue = None`
**When** the current target value selector is called
**Then** it returns the default source value.

**Given** a mapping has a literal `targetValue`
**When** the current target value selector is called
**Then** it returns that literal target value
**And** it does not canonicalize a value equal to the default source back to `None`.

**Given** a mapping contains sources with missing values
**When** the active sources selector is called
**Then** it returns only sources whose effective value is not `None`
**And** it preserves the mapping's source display order.

**Given** fixture data violates entity invariants
**When** validation tests construct duplicate source labels, unknown source labels, unknown default source labels, missing default sources, or a sanitized value for a missing original value
**Then** the implementation reports the invariant failure deterministically
**And** no derived selector silently repairs the invalid data.

### Story 1.4: Sort Mappings and Detect Initial Collisions

As a reviewer,
I want mappings displayed in deterministic order with unresolved collisions identified,
So that I can immediately see which mappings need attention before editing.

**Acceptance Criteria:**

**Given** Stories 1.1 through 1.3 have established fixture data and derived target selectors
**When** the developer starts this story
**Then** they first write failing tests for stable display sorting, collision grouping, unresolved collision counts, and collision row membership
**And** production selector logic is implemented only after those tests fail.

**Given** the storyboard fixture mappings are loaded
**When** the base display order selector is called
**Then** mappings are sorted by default source value
**And** ties are broken by ASCII order of the default source's original value
**And** remaining ties are broken by original ordinal.

**Given** rows 2 and 3 both derive current target value `AT-T`
**When** collision groups are selected
**Then** the implementation returns one collision group containing ordinals 2 and 3
**And** the unresolved collision count is `1`.

**Given** a mapping's current target value is unique
**When** unresolved collision ordinals are selected
**Then** that mapping's ordinal is not included
**And** only rows belonging to collision groups are marked unresolved.

**Given** a later story changes a mapping's literal target value
**When** the stable base display order selector is called again
**Then** ordering remains based on initialization/default-source sort rules
**And** target edits do not dynamically reorder rows.

**Given** collision selectors are pure derived state
**When** tests call them repeatedly against the same root state
**Then** they return the same collision groups and counts
**And** they do not store `collisionGroups`, `unresolvedCollisions`, or `unresolvedCollisionCount` as mutable root or component state.

**Given** collision indicators will later be rendered by row projection
**When** tests request row-level collision metadata
**Then** ordinals 2 and 3 expose an unresolved collision marker
**And** all other storyboard fixture rows expose no collision marker.
