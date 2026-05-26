# Beancount Commodity Symbol Editor TUI

An interactive terminal UI for reviewing and editing Beancount commodity
symbols. The widget renders inline — no full-screen takeover, no alternate
screen — so your existing terminal history stays visible above it. Rows are
colour-coded by state (confirmed ✓, collision ≠, invalid ✗, unconfirmed ·),
and you can scroll, jump to any row by number, and type a corrected symbol
before accepting or cancelling the whole session.

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

`uv sync --group dev` creates a virtual environment and installs all
runtime dependencies (`rich`, `textual`) plus the dev dependency (`pytest`).

## Running the scripts

### Interactive editor — `tui_prototype.py`

```
uv run python3 tui_prototype.py
```

Launches the TUI loaded with the 80-row `LARGE_FIXTURE` dataset. Use the
arrow keys or type a row number to select a row, then type a corrected
Beancount currency symbol. Press Enter to confirm a row, `a` to accept all
(only available once every collision and invalid row is resolved), or Escape /
Ctrl+C to cancel.

### Test suite — `test_tui.py`

```
uv run pytest
```

Runs 55 behavioural and layout tests covering rendering, key-handling,
scrolling, paging, and terminal-resize via PTY and SIGWINCH/TIOCSWINSZ.

### Resize demo — `resize_demo.py`

```
uv run python3 resize_demo.py
```

Automated watchable demo: drives the TUI through four terminal heights
(8, 14, 24, 35 rows) via `TIOCSWINSZ` + `SIGWINCH`, captures each
re-rendered frame, and prints it to stdout with a header showing the
terminal height and the resulting viewport row count. No keyboard input
required — the script exits automatically after all frames are shown.

## Alternative (no uv)

If you prefer plain pip:

```
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Then run any script with:

```
python3 tui_prototype.py
python3 -m pytest test_tui.py -v
python3 resize_demo.py
```
