---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments: ["tui_architecture_spec.md"]
workflowType: 'architecture'
project_name: 'gnubeans-tui-prototype'
user_name: 'Philippe'
date: '2026-05-26'
lastStep: 8
status: 'complete'
completedAt: '2026-05-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- Browse and filter a dataset of entity mappings with real-time updates.
- Edit target tokens with inline validation, ghost-text autocomplete, and source-list navigation.
- Implement specialized modes for accepting or exiting with y/n confirmation flows.
- Strict readline-style key bindings for text inputs.

**Non-Functional Requirements:**
- **Inline Rendering**: Must render directly in the terminal stream, avoiding the alternate screen buffer. The UI must expand dynamically to fill the available terminal window width and height.
- **State Architecture**: All mutable state must reside in a centralized root store with pure derived selectors for rendering.
- **Display Math**: Layout calculations must be strictly based on Unicode display width, not byte length.

**Scale & Complexity:**
- Primary domain: Terminal UI (Python)
- Complexity level: High (strict custom constraints over standard TUI library behaviors)
- Estimated architectural components: 4-5 core components (State Store, Input Engine, Renderer, Validation/Compute Logic)

### Technical Constraints & Dependencies
- Must run in standard terminal emulators without relying on an alternate screen buffer.
- Requires a Python library or mechanism capable of capturing raw keystrokes (including complex modifier combos) while allowing strict frame-by-frame redraws.

### Cross-Cutting Concerns Identified
- Pure derived view state computation
- Unicode string width alignment
- Terminal event handling (specifically suppressing default behaviors and intercepting readline keys)

## Starter Template Evaluation

### Primary Technology Domain

CLI / Terminal UI (Python) based on project requirements analysis.

### Starter Options Considered

1. **Textual**: A modern, powerful Python TUI framework with CSS-like styling. It now supports `inline=True` for inline rendering. However, its state management and event-driven component model heavily conflict with the strict requirement for a pure, centralized root state projection.
2. **prompt_toolkit**: An excellent library for building advanced CLIs. It supports inline rendering and complex readline keybindings. However, bending its internal layout engine and application loop to exactly match the precise, custom interaction requirements can be unnecessarily complex.
3. **blessed**: A thin, robust wrapper around terminal capabilities. It provides the exact primitives needed (raw keystroke reading via `inkey()`, ANSI styling, accurate Unicode string width calculations) without imposing a conflicting state management architecture or widget lifecycle.

### Selected Starter: blessed

**Rationale for Selection:**
The specification strictly mandates that "All mutable application state MUST be owned by the root/app state. Renderers and components MUST be pure projections of root state plus derived selectors." Higher-level frameworks like Textual enforce their own component-level state and lifecycles, which violates this requirement. `blessed` provides exactly what is needed—terminal control, raw input capturing, and string width math—while leaving us in complete control of the strict state machine and event loop. It also seamlessly supports the required inline rendering by simply avoiding the `fullscreen()` context manager.

**Initialization Command:**

```bash
uv add blessed pytest pytest-bdd
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python 3

**Styling Solution:**
ANSI escape sequences managed via `blessed` string formatters (e.g., `term.bold`, `term.dim`, `term.reverse`).

**Build Tooling:**
Standard Python packaging (managed via `uv` as present in the project).

**Testing Framework:**
`pytest` and `pytest-bdd` for pure state transition testing (since the UI is a pure projection, the logic is highly testable headlessly without rendering overhead).

**Code Organization:**
Strict Redux-like architecture:
- State definitions and pure transition logic
- Derived selectors for view state and display math
- Pure string projection renderer utilizing `blessed`
- A main input loop using `term.cbreak()` and `term.hidden_cursor()`

**Development Experience:**
Fast, inline iteration. We can run the script and immediately see the results in our current terminal scrollback, exactly simulating the integration environment.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Event Loop Architecture
- Code Organization
- Behavior-Driven Development (BDD) Testing Strategy

**Important Decisions (Shape Architecture):**
- State Management Implementation (Custom pure Redux-like implementation vs third-party library)

**Deferred Decisions (Post-MVP):**
- Background asynchronous data loading (deferring since the current PRD mandates strict synchronous UI state reactions).

### Frontend Architecture

**Decision: Event Loop Structure**
- Choice: Synchronous Blocking Loop
- Version: Python 3 standard library
- Rationale: The TUI prototype is entirely reactive to user keyboard input. Without complex background network polling mentioned in the PRD, avoiding `asyncio` drastically simplifies state transitions, debugging, and testing. 

**Decision: Code Organization**
- Choice: Modular Architecture
- Rationale: The architectural spec explicitly calls out pure derived selectors and headless state transitions. Splitting the codebase into distinct modules (`state.py`, `selectors.py`, `reducer.py`, `renderer.py`, `loop.py`) enforces strict unidirectional boundaries and makes unit testing the state machine with `pytest` trivial, completely avoiding terminal mocking overhead.

### Decision Impact Analysis

**Implementation Sequence:**
1. Scaffold project with `uv` and set up the modular directory structure.
2. Implement core immutable state models (types and dataclasses) in `state.py`.
3. Implement pure `reducer` functions for state transitions (handling readline keys and logic).
4. Implement pure `selectors` to compute derived view states and strict Unicode display math.
5. Build the `renderer` pure projection functions using `blessed`.
6. Connect the pieces via the synchronous event `loop.py`.

**Cross-Component Dependencies:**
- The Renderer depends strictly on the output of Selectors, isolating it entirely from raw Root State data.
- The Event Loop bridges the components by reading keystrokes, dispatching actions to the Reducer, and piping the new State to the Renderer.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
4 areas where AI agents could make different choices

### Naming Patterns

**State Variables Naming Conventions:**
- State class fields MUST use Python standard `snake_case` (e.g., `scroll_offset`, `focus_region`).
- Dataclass/Type definitions MUST use `PascalCase` (e.g., `AppState`, `FilterState`).

**Event Naming Conventions:**
- Action types MUST be declared as `PascalCase` dataclasses to represent the action payload strictly (e.g., `ActionKeyPress(key: str)`, `ActionSubmit()`).

**Code Naming Conventions:**
- Files MUST use `snake_case` (e.g., `state.py`, `reducer.py`).
- Derived state functions (selectors) MUST be prefixed with `select_` (e.g., `select_visible_rows(state)`).

### Structure Patterns

**Project Organization:**
- The core modular files MUST reside in the root or a `lib/` module.
- All unit tests MUST live in a top-level `tests/` directory.

**File Structure Patterns:**
- `state.py`: Exclusively pure data structures (`@dataclass(frozen=True)`).
- `reducer.py`: Pure functions transitioning state `(State, Action) -> State`.
- `selectors.py`: Pure functions computing derived data `(State) -> DerivedData`.
- `renderer.py`: Pure rendering functions `(State, DerivedData) -> List[str]`.

### Format Patterns

**Data Exchange Formats:**
- Actions are strictly typed dataclasses, avoiding untyped dictionaries.
- Input keystrokes from `blessed` MUST be passed as structured `ActionKeyPress` objects to the reducer; the reducer handles the readline normalization.

### Process Patterns

**Error Handling Patterns:**
- **Terminal Safety**: The main event loop MUST be wrapped in a generic `try/finally` or `try/except` block to ensure terminal configurations are properly restored before dumping python tracebacks to stdout.
- **Validation**: User input validation within the Reducer MUST NOT crash the application; it MUST set an error string inside `state.edit.validation` to be rendered in the footer.

### Enforcement Guidelines

**All AI Agents MUST:**
- **Immutability**: Never mutate state objects directly. Always return a new instance using `dataclasses.replace(state, ...)`.
- **Display Separation**: Never place terminal rendering strings (ANSI) inside the Reducer or State. ANSI is strictly the domain of `renderer.py`.
- **Pure Logic**: Never read from `blessed.Terminal` or perform I/O inside `reducer.py`.

### Pattern Examples

**Good Examples:**
```python
# Selectors (pure data projection, no terminal ANSI):
def select_visible_rows(state: AppState) -> List[Mapping]:
    return [m for m in state.mappings if ...]

# Reducer (immutable updates):
def reduce(state: AppState, action: Action) -> AppState:
    if isinstance(action, ActionKeyPress):
        # Good: Using dataclasses.replace to return a new copy
        new_filter = replace(state.filter, text=state.filter.text + action.key)
        return replace(state, filter=new_filter)
```

**Anti-Patterns:**
```python
# ANTI-PATTERN: Mutating state directly
state.filter.text += action.key

# ANTI-PATTERN: Embedding view/ANSI concerns in state or reducer
state.error_message = term.red("Invalid input!") # State should only store "Invalid input!"
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
gnubeans-tui-prototype/
├── README.md
├── pyproject.toml
├── uv.lock
├── tui_prototype.py     # Main entry point that sets up config and starts the loop
├── lib/                 # Core modular implementation
│   ├── __init__.py
│   ├── config.py        # AppConfig data model and storyboard fixture configurations
│   ├── state.py         # AppState and pure dataclasses (Mode, Mapping, Source, etc.)
│   ├── actions.py       # Typed Action definitions (e.g. ActionKeyPress)
│   ├── reducer.py       # Pure state transition logic (reduce(state, action) -> state)
│   ├── selectors.py     # Derived state math and Unicode width calculations
│   ├── renderer.py      # Terminal frame ANSI projection using blessed
│   └── loop.py          # The synchronous blocking event loop (term.inkey)
└── tests/
    ├── __init__.py
    ├── features/                # Gherkin feature files
    │   ├── browsing.feature     # e.g. "Given the app is in BROWSING mode..."
    │   ├── editing.feature      # e.g. "When the user types Tab..."
    │   └── confirmation.feature
    ├── step_defs/               # BDD step definitions
    │   ├── conftest.py          # Shared fixtures (e.g., initial AppState)
    │   ├── test_browsing.py
    │   └── test_editing.py
    ├── unit/                    # Fast, isolated unit tests for edge cases
    │   ├── test_reducer.py  
    │   └── test_selectors.py
```

### Architectural Boundaries

**API Boundaries:**
- The application exposes no external APIs. It acts as an interactive CLI script.

**Component Boundaries:**
- `reducer.py` MUST NOT import or use `blessed`. It receives raw string keys enclosed in `ActionKeyPress`.
- `renderer.py` MUST NOT mutate state. It reads `AppState` and returns/prints strings.
- `selectors.py` is the only place display math (Unicode width mapping, ghost text computing) should occur.
- `loop.py` is the sole owner of side effects (blocking on input, flushing output, and exiting).

### Requirements to Structure Mapping

**Feature Mapping:**
- **Text Editing / Readline Bindings**: Logic contained entirely within `lib/reducer.py`, specifically handling `ActionKeyPress` for backspace, tab autocomplete, and character insertion.
- **State Layout & Validation**: Computed in `lib/selectors.py`.
- **Dynamic Inline Rendering**: Handled strictly by `lib/renderer.py` relying on `blessed` formatters, adapting row counts and text truncation based on dynamic terminal dimensions.

### Integration Points

**Internal Communication:**
- **Data Flow**: `loop` reads `term.inkey()` -> Dispatches `Action` -> `reducer` returns new `AppState` -> `selectors` compute view -> `renderer` projects view -> terminal.

### File Organization Patterns

**Configuration Files:**
- `pyproject.toml` tracks the `blessed`, `pytest`, and `pytest-bdd` dependencies.
- `lib/config.py` holds the concrete dataset config simulating the real app integration context.

**Source Organization:**
- Grouped by architectural responsibility (Redux pattern) rather than by feature, as the entire app is essentially one complex UI component.

**Test Organization:**
- BDD steps dispatch actions against the `reducer` headlessly and assert `AppState` results using `pytest-bdd` over `tests/features/`.
- Unit tests run completely decoupled from the terminal by passing dummy actions into the `reducer` and asserting the returned `AppState`.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
The selection of Python 3, `blessed`, and `pytest-bdd` within a Redux-like state architecture is highly compatible. `blessed` handles terminal idiosyncrasies and dynamic sizing (`term.width`, `term.height`) efficiently while staying out of the way of the core business logic, which enables seamless BDD testing without mocking complex I/O.

**Pattern Consistency:**
The implementation patterns strictly enforce separation of concerns. By preventing the `reducer` from returning or interpreting ANSI strings, the pure data flow remains intact, fully supporting the architectural decision for testability.

**Structure Alignment:**
The project structure directly mirrors the architectural patterns. The `lib/` directory isolates state transitions from side effects (`loop.py`), enabling the exact integration points specified.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
All core interactive features (browsing, filtering, editing with autocomplete) are supported by the `reducer`'s state machine.

**Functional Requirements Coverage:**
The complex readline keybindings and dynamic terminal dimension constraints are fully addressed through the combination of `blessed` raw input handling and `selectors` computing exact Unicode widths based on dynamic screen sizes.

**Non-Functional Requirements Coverage:**
The explicit prohibition of the alternate screen buffer is satisfied by avoiding `blessed`'s `fullscreen()` context manager.

### Implementation Readiness Validation ✅

**Decision Completeness:**
All critical decisions (event loop, code organization, testing strategy) are documented with clear rationales.

**Structure Completeness:**
The complete directory structure defines exactly where every piece of logic resides, mapping directly to BDD feature files.

**Pattern Completeness:**
Critical conflict points, particularly around state mutation and rendering responsibilities, have clear enforcement guidelines and anti-patterns established.

### Gap Analysis Results

No critical or important gaps remain. The architecture provides a complete, testable, and robust blueprint for implementing the dynamic TUI prototype.

### Validation Issues Addressed

- Removed the strict 15x75 grid assumption, explicitly noting that the UI expands dynamically to fill terminal height and width.
- The inclusion of `pytest-bdd` during the structuring phase resolved potential ambiguity around how to systematically test complex state transitions (frames) against the architectural specification.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Strict separation of state and rendering eliminates entire classes of terminal bugs.
- BDD testing approach directly maps to the rigorous visual specification frames.
- Lightweight dependencies (`blessed` only for runtime) ensures fast inline performance.

**Areas for Future Enhancement:**
- If the application scales to require background network polling, the synchronous loop will need to be refactored to use `asyncio` or background threads.

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
Initialize the project structure and dependencies: `uv init` followed by `uv add blessed pytest pytest-bdd`, and setup the initial `lib/` and `tests/` directories.
