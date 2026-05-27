# Mapping Resolution TUI

A reusable Python terminal component for resolving mapping collisions through
keyboard-driven review, source-assisted editing, validation, and confirmation.
The component renders inline — no alternate screen, no full-screen takeover —
so terminal history stays visible above the frame.

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.11 |
| `uv` | any recent release |

Install `uv` with pip or Homebrew:

```
pip install uv
# or
brew install uv
```

## Setup

```
git clone <repo-url>
cd <repo-dir>
uv sync --group dev
```

## Storyboard demo

```
uv run demo storyboard
```

Renders the initial browsing frame loaded with the 11-commodity storyboard
fixture (`tests/fixtures/storyboard.py`). The fixture
exercises bootstrap sort order and includes one AT-T collision (indexes 2
and 3). The frame renders inline into the terminal scroll buffer; the shell
prompt returns immediately.

## Test suite

```
uv run pytest tests/
```

The automated golden render and BDD behaviour tests are the authoritative
acceptance checks. The demo command is a visual aid only.

Golden render tests use **pyte** as a virtual terminal emulator: `screen.display`
provides ANSI-stripped geometry for content assertions, and
`screen.buffer[row][col].bold` / `.reverse` provide cell-level style assertions.
Each frame also has a snapshot test that compares the full plain-text display
against a committed reference file in `tests/golden/snapshots/`.

To regenerate snapshots after an intentional renderer change:

```
uv run pytest tests/golden/ --update-snapshots
```
