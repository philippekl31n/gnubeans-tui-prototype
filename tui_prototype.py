#!/usr/bin/env python3
"""
tui_prototype.py — Interactive Beancount commodity symbol editor.

Renders inline in the terminal — no full-screen takeover, no TUI frame.
The table appears immediately below any pre-flight warnings and stays in
the scrollback buffer after exit.

Visual design (task #6):
  - Rich table with box.SIMPLE_HEAD (header underline only, no outer frame)
  - Indicator column: ·/✓/≠/✗/▸ glyphs with semantic colour slots
  - Two-line footer: hint/status line above, › prompt line below
  - Colour slots: amber #FFAA00 (collision), red #FF4466 (invalid),
    green #04B575 (confirmed), bright yellow #ECFD65 (editing)
"""

from __future__ import annotations

import io
import os
import re
import select
import signal
import sys
import termios
import threading
import tty
from dataclasses import dataclass
from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text


# ─── Symbol logic ─────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"^[A-Z]([A-Z0-9\-]{0,22}[A-Z0-9])?$")


def is_valid_currency(s: str) -> bool:
    """True if *s* is a valid Beancount currency symbol."""
    return bool(s and _CURRENCY_RE.match(s))


def suggest_currency(raw: str) -> str:
    """Sanitise an arbitrary commodity id into a valid Beancount currency."""
    s = raw.upper()
    s = re.sub(r"[^A-Z0-9\-]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    if not s:
        return "UNKNOWN"
    if not s[0].isalpha():
        s = "C" + s
    while s and not s[-1].isalnum():
        s = s[:-1]
    return s[:24] or "UNKNOWN"


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class Row:
    num: int
    cmdty_id: str
    user_symbol: str
    suggested: str
    currency: str
    confirmed: bool = False


FIXTURE: list[tuple[str, str]] = [
    ("AT&T",    ""),
    ("AT[T]",   ""),
    ("VBMPX",   ""),
    ("1003057", ""),
]

# Larger fixture (24 rows) for paging and resize tests.
#
# States encoded via the (cmdty_id, user_symbol) pairs:
#   user_symbol = ""          → clean unconfirmed (·); currency = suggest_currency(cmdty_id)
#   user_symbol = valid sym   → pre-confirmed (✓); currency = user_symbol, confirmed=True
#   user_symbol = invalid sym → invalid (✗); currency = user_symbol, confirmed=False,
#                               recompute() surfaces row.num in the *invalid* set
#
# Row spread:
#   rows  1-2  : collision pair 1 — "AT&T" and "AT[T]" both → "AT-T"       (≠)
#   rows  3-4  : collision pair 2 — "APPLE INC"/"APPLE_INC" → "APPLE-INC"  (≠)
#   row   5    : invalid user_symbol "NOT-VALID!" — flagged by recompute()  (✗)
#   rows  6-12 : pre-confirmed (user_symbol == valid currency)               (✓)
#   rows 13-24 : clean unconfirmed (empty user_symbol)                       (·)
LARGE_FIXTURE: list[tuple[str, str]] = [
    ("AT&T",       ""),           # 1  → AT-T       ≠ collision pair 1
    ("AT[T]",      ""),           # 2  → AT-T       ≠ collision pair 1
    ("APPLE INC",  ""),           # 3  → APPLE-INC  ≠ collision pair 2
    ("APPLE_INC",  ""),           # 4  → APPLE-INC  ≠ collision pair 2
    ("BADCMDTY",   "NOT-VALID!"), # 5  currency="NOT-VALID!" → invalid per recompute()  ✗
    ("GOOGL",      "GOOGL"),      # 6  pre-confirmed  ✓
    ("AMZN",       "AMZN"),       # 7  pre-confirmed  ✓
    ("NVDA",       "NVDA"),       # 8  pre-confirmed  ✓
    ("TSLA",       "TSLA"),       # 9  pre-confirmed  ✓
    ("MSFT",       "MSFT"),       # 10 pre-confirmed  ✓
    ("META",       "META"),       # 11 pre-confirmed  ✓
    ("NFLX",       "NFLX"),       # 12 pre-confirmed  ✓
    ("VBMPX",      ""),           # 13 · clean unconfirmed
    ("INTC",       ""),           # 14 · clean unconfirmed
    ("AMD",        ""),           # 15 · clean unconfirmed
    ("QCOM",       ""),           # 16 · clean unconfirmed
    ("AVGO",       ""),           # 17 · clean unconfirmed
    ("AAPL",       ""),           # 18 · clean unconfirmed
    ("BRKB",       ""),           # 19 · clean unconfirmed
    ("JPM",        ""),           # 20 · clean unconfirmed
    ("1003057",    ""),           # 21 · clean unconfirmed (numeric-start; WARNING emitted)
    ("WMT",        ""),           # 22 · clean unconfirmed
    ("UNH",        ""),           # 23 · clean unconfirmed
    ("BAC",        ""),           # 24 · clean unconfirmed
]


def make_rows(pairs: list[tuple[str, str]]) -> list[Row]:
    """Build a list of Row objects from (cmdty_id, user_symbol) pairs.

    When *user_symbol* is non-empty it is used as the initial *currency*
    value and the row is marked confirmed=True if the symbol is valid,
    confirmed=False if it is invalid (so recompute() surfaces it in the
    *invalid* set).  When *user_symbol* is empty, *currency* defaults to
    suggest_currency(cmdty_id) and confirmed=False.
    """
    rows = []
    for i, (cid, usym) in enumerate(pairs, 1):
        sug = suggest_currency(cid)
        if usym:
            currency  = usym
            confirmed = is_valid_currency(usym)
        else:
            currency  = sug
            confirmed = False
        rows.append(Row(i, cid, usym or "(not set)", sug, currency, confirmed=confirmed))
    return rows


def recompute(rows: list[Row]) -> tuple[set[int], set[int]]:
    """Return (collision_row_nums, invalid_row_nums)."""
    seen: dict[str, list[int]] = {}
    for r in rows:
        seen.setdefault(r.currency, []).append(r.num)
    collisions = {n for nums in seen.values() if len(nums) > 1 for n in nums}
    invalid = {r.num for r in rows if not is_valid_currency(r.currency)}
    return collisions, invalid


def emit_warnings(rows: list[Row]) -> None:
    """Print pre-flight WARNINGs (streaming order: invalid then collision per row)."""
    seen: dict[str, list[str]] = {}
    reported: set[str] = set()
    for r in rows:
        if not is_valid_currency(r.cmdty_id):
            print(
                f'WARNING: commodity "{r.cmdty_id}" is not a valid Beancount symbol'
                f' \u2014 suggesting "{r.suggested}"'
            )
        seen.setdefault(r.suggested, []).append(r.cmdty_id)
        if len(seen[r.suggested]) > 1 and r.suggested not in reported:
            reported.add(r.suggested)
            parts = " and ".join(f'"{i}"' for i in seen[r.suggested])
            print(
                f'WARNING: collision \u2014 {parts} both produce the Beancount currency'
                f' "{r.suggested}". Assign distinct symbols in the plan.'
            )


# ─── Semantic colour slots ─────────────────────────────────────────────────────

_CLR_CONFIRMED = "#04B575"   # Charm soft green
_CLR_COLLISION = "#FFAA00"   # Amber  (warning severity)
_CLR_INVALID   = "#FF4466"   # Charm hot-pink red
_CLR_EDITING   = "#ECFD65"   # Charm bright yellow


# ─── Rendering bridge ─────────────────────────────────────────────────────────

def _term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def _render(renderable, width: int) -> list[str]:
    """Render a Rich renderable to a list of ANSI-coded strings (one per line).

    Rich always appends a trailing newline after each print(); we strip the
    resulting trailing empty element after splitting on '\\n'.

    ``color_system="truecolor"`` is set explicitly so Rich never queries the
    terminal for color support (which would block in a pty test context).
    """
    buf = io.StringIO()
    con = Console(
        file=buf,
        force_terminal=True,
        color_system="truecolor",
        width=width,
        highlight=False,
    )
    con.print(renderable)
    lines = buf.getvalue().split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


# ─── Rendering ────────────────────────────────────────────────────────────────

def build_table(
    rows: list[Row],
    mode: str,
    vstart: int,
    viewport_h: int,
    edit_row: int,
    edit_buf: str,
    collisions: set[int],
    invalid: Optional[set[int]] = None,
) -> list[str]:
    """Return Rich-rendered ANSI lines for the visible portion of the table.

    Line layout (SIMPLE_HEAD, show_edge=False):
      lines[0]           — header row (column labels)
      lines[1]           — underline rule (─────)
      lines[2..2+N-1]    — data rows

    Total = N + 2 for N visible rows.
    """
    if invalid is None:
        invalid = set()
    width = _term_width()
    visible = rows[vstart: vstart + viewport_h]

    tbl = Table(
        box=box.SIMPLE_HEAD,
        padding=(0, 2),
        show_edge=False,
        row_styles=["", "dim"],
        header_style="bold",
    )
    tbl.add_column("",             no_wrap=True)           # indicator glyph
    tbl.add_column("#",            justify="right", no_wrap=True)
    tbl.add_column("cmdty:id",     no_wrap=True)
    tbl.add_column("user_symbol",  no_wrap=True)
    tbl.add_column("CURRENCY",     no_wrap=True)

    for row in visible:
        editing      = mode == "edit" and edit_row == row.num
        collision    = row.num in collisions
        confirmed_ok = row.confirmed and row.num not in collisions
        is_invalid   = row.num in invalid

        if editing:
            # ▸ in indicator; ▇ cursor lives in the footer prompt, not the table
            tbl.add_row(
                Text("\u25b8", style=f"bold {_CLR_EDITING}"),      # ▸
                str(row.num),
                row.cmdty_id,
                row.user_symbol,
                Text(edit_buf, style=f"bold {_CLR_EDITING}"),
                style=f"bold {_CLR_EDITING}",
            )
        elif collision:
            # ≠ + amber + strikethrough on CURRENCY; other cells default/dim
            tbl.add_row(
                Text("\u2260", style=_CLR_COLLISION),               # ≠
                str(row.num),
                row.cmdty_id,
                row.user_symbol,
                Text(row.currency, style=f"{_CLR_COLLISION} strike"),
            )
        elif confirmed_ok:
            # ✓ + soft green on all cells
            tbl.add_row(
                Text("\u2713", style=_CLR_CONFIRMED),               # ✓
                str(row.num),
                row.cmdty_id,
                row.user_symbol,
                row.currency,
                style=_CLR_CONFIRMED,
            )
        elif is_invalid:
            # ✗ + hot-pink red on indicator + CURRENCY; other cells default
            tbl.add_row(
                Text("\u2717", style=_CLR_INVALID),                 # ✗
                str(row.num),
                row.cmdty_id,
                row.user_symbol,
                Text(row.currency, style=_CLR_INVALID),
            )
        else:
            # · dim dot; cells get alternating dim from row_styles
            tbl.add_row(
                Text("\u00b7", style="dim"),                        # ·
                str(row.num),
                row.cmdty_id,
                row.user_symbol,
                row.currency,
            )

    return _render(tbl, width)


def build_footer(
    mode: str,
    sel_buf: str,
    edit_row: int,
    edit_err: Optional[str],
    collisions: set[int],
    invalid: set[int],
    n_rows: int,
) -> list[str]:
    """Return a 2-element list [hint_line, prompt_line] as ANSI strings.

    Line 0 (hint): dim italic prose with bold key names; amber ⚠ on error.
    Line 1 (prompt): bold › glyph followed by the active input buffer.
    """
    width = _term_width()
    unresolved = len(collisions | invalid)

    # ── hint line ─────────────────────────────────────────────────────────────
    if mode == "select":
        hint = Text(no_wrap=True)
        hint.append("\u2191\u2193", style="bold")          # ↑↓
        hint.append(" scroll  \u00b7  type a row number", style="dim italic")
        if not unresolved:
            hint.append("  \u00b7  ", style="dim italic")
            hint.append("a", style="bold")
            hint.append("  accept all", style="dim italic")
    else:  # edit mode
        if edit_err:
            hint = Text(no_wrap=True)
            hint.append("\u26a0", style=f"bold {_CLR_COLLISION}")  # ⚠ amber badge
            hint.append(f"  {edit_err}", style="dim italic")
        else:
            hint = Text(no_wrap=True)
            hint.append("\u21b5", style="bold")            # ↵
            hint.append(" confirm  \u00b7  ", style="dim italic")
            hint.append("esc", style="bold")
            hint.append(
                " cancel  \u00b7  \u2191\u2193 move row  \u00b7  ",
                style="dim italic",
            )
            hint.append(str(unresolved), style="bold")
            hint.append(" unresolved", style="dim italic")

    # ── prompt line ───────────────────────────────────────────────────────────
    prompt = Text(no_wrap=True)
    prompt.append("\u203a  ", style="bold")                # ›
    # sel_buf is normalised by the caller: sel_buf in select mode, edit_buf in edit
    if sel_buf:
        prompt.append(sel_buf, style="bold")
    else:
        prompt.append("\u00b7", style="dim")               # · dim placeholder when empty
    prompt.append("\u2587", style="dim")                   # ▇ cursor

    hint_lines   = _render(hint,   width)
    prompt_lines = _render(prompt, width)
    return [
        hint_lines[0]   if hint_lines   else "",
        prompt_lines[0] if prompt_lines else "",
    ]


# ─── Inline display ───────────────────────────────────────────────────────────

class Display:
    """Renders and updates the table+footer inline in the terminal.

    On the first call to show(), lines are printed normally.  On subsequent
    calls the cursor is moved back up and lines are overwritten in place so
    the widget stays anchored in the scrollback buffer.

    The optional *output* argument controls where rendered text is sent;
    it defaults to sys.stdout.  Pass an explicit file object (e.g. a pty
    slave fd wrapped with os.fdopen) to capture output in tests.
    """

    def __init__(self, output=None) -> None:
        self._prev_n = 0   # total lines printed on the previous render
        self._out = output if output is not None else sys.stdout

    def show(self, table_lines: list[str], footer_lines: list[str]) -> None:
        """Overwrite the widget in place.

        Cursor-up count = len(table_lines) + len(footer_lines) - 1.
        The -1 accounts for the last footer line having no trailing \\n,
        so the cursor ends on that line rather than one line below.
        """
        n = len(table_lines) + len(footer_lines) - 1
        buf = ""
        if self._prev_n > 0:
            # Return to start of first table line:
            # \r  → go to column 0 of the footer line (current position)
            # \033[NA → move up N lines to the first table line
            buf += f"\r\033[{self._prev_n}A"
        for line in table_lines:
            buf += f"\033[2K\r{line}\n"          # clear + overwrite, then newline
        for i, line in enumerate(footer_lines):
            if i < len(footer_lines) - 1:
                buf += f"\033[2K\r{line}\n"      # hint line: trailing newline
            else:
                buf += f"\033[2K\r{line}"        # prompt line: no trailing newline
        self._out.write(buf)
        self._out.flush()
        self._prev_n = n


# ─── Raw keyboard input ───────────────────────────────────────────────────────

def _readb(fd: int, timeout: float = 0.05) -> bytes:
    r, _, _ = select.select([fd], [], [], timeout)
    return os.read(fd, 1) if r else b""


def read_key(fd: int) -> str:
    """Block until a keypress and return a key-name string."""
    ch = os.read(fd, 1)
    if ch == b"\x1b":
        ch2 = _readb(fd)
        if ch2 == b"[":
            ch3 = _readb(fd)
            if ch3 == b"A": return "up"
            if ch3 == b"B": return "down"
            if ch3 == b"C": return "right"
            if ch3 == b"D": return "left"
            if ch3 == b"5": _readb(fd); return "pageup"
            if ch3 == b"6": _readb(fd); return "pagedown"
        return "escape"
    if ch in (b"\r", b"\n"): return "enter"
    if ch in (b"\x7f", b"\x08"): return "backspace"
    if ch == b"\x03": return "ctrl_c"
    try:
        return ch.decode("utf-8")
    except UnicodeDecodeError:
        return ""


# ─── Interactive loop ─────────────────────────────────────────────────────────

def run(rows: list[Row], *, stdin_fd: Optional[int] = None, output=None) -> str:
    """Run the interactive editor. Returns 'accepted' or 'cancelled'.

    Keyword arguments
    -----------------
    stdin_fd : int | None
        File descriptor to use for keyboard input.  When *None* (default)
        falls back to ``sys.stdin.fileno()``.  Pass a pty slave fd in tests
        to drive the TUI without touching the real terminal.
    output : file-like | None
        Where rendered text is written.  When *None* (default) falls back to
        ``sys.stdout``.  Pass an explicit file object in tests to capture
        TUI output independently of the process's stdout.
    """
    n = len(rows)
    try:
        # Prefer the size of stdin_fd (the pty slave in tests / the real tty in
        # production) so that programmatic TIOCSWINSZ resizes are seen correctly.
        # A freshly-opened pty with no TIOCSWINSZ applied returns 0 rows;
        # treat that as "unknown" and fall through to the process-level query.
        _init_fd = stdin_fd if stdin_fd is not None else sys.stdout.fileno()
        _h = os.get_terminal_size(_init_fd).lines
        if _h <= 0:
            raise OSError("terminal reports zero rows")
        viewport_h = max(3, _h - 6)       # leave headroom above for warnings
    except OSError:
        try:
            viewport_h = max(3, os.get_terminal_size().lines - 6)
        except OSError:
            viewport_h = 10
    viewport_h = min(viewport_h, n)       # no need to be taller than the data

    mode     = "select"
    sel_buf  = ""
    edit_buf = ""
    edit_row = 0
    edit_err: Optional[str] = None
    vstart   = 0
    collisions, invalid = recompute(rows)
    display  = Display(output=output)

    def refresh() -> None:
        tbl = build_table(
            rows, mode, vstart, viewport_h, edit_row, edit_buf, collisions, invalid
        )
        buf_for_footer = edit_buf if mode == "edit" else sel_buf
        ftr = build_footer(mode, buf_for_footer, edit_row, edit_err, collisions, invalid, n)
        display.show(tbl, ftr)

    def scroll_to(row_num: int) -> None:
        nonlocal vstart
        idx = row_num - 1
        if idx < vstart:
            vstart = idx
        elif idx >= vstart + viewport_h:
            vstart = idx - viewport_h + 1
        vstart = max(0, vstart)

    def scroll_by(delta: int) -> None:
        nonlocal vstart
        vstart = max(0, min(max(0, n - viewport_h), vstart + delta))

    refresh()

    fd = stdin_fd if stdin_fd is not None else sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    result = "cancelled"

    # SIGWINCH: recompute viewport_h when the terminal window is resized.
    # signal.signal() may only be called from the main thread; skip silently
    # when run() is invoked from a background thread (e.g. in PTY tests).
    _SIGWINCH = getattr(signal, "SIGWINCH", None)
    _old_sigwinch = None
    _in_main_thread = threading.current_thread() is threading.main_thread()

    if _SIGWINCH is not None and _in_main_thread:
        def _handle_sigwinch(signum, frame):  # noqa: ANN001
            nonlocal viewport_h, vstart
            try:
                # Query the size of the actual fd being used (the pty slave in
                # tests; the real tty in production).  Fall back to the process-
                # wide terminal size if the fd query raises OSError.
                new_lines = os.get_terminal_size(fd).lines
            except OSError:
                try:
                    new_lines = os.get_terminal_size().lines
                except OSError:
                    return
            viewport_h = min(max(3, new_lines - 6), n)
            vstart = min(vstart, max(0, n - viewport_h))
            refresh()

        _old_sigwinch = signal.signal(_SIGWINCH, _handle_sigwinch)

    try:
        tty.setraw(fd)

        while True:
            try:
                key = read_key(fd)
            except InterruptedError:
                continue

            if mode == "select":
                page = max(1, viewport_h)
                if key in ("escape", "ctrl_c"):
                    result = "cancelled"; break
                elif key in ("up", "pageup"):
                    scroll_by(-page)
                elif key in ("down", "pagedown"):
                    scroll_by(page)
                elif key == "backspace":
                    sel_buf = sel_buf[:-1]
                elif key == "enter":
                    if sel_buf:
                        try:
                            row_num = int(sel_buf)
                        except ValueError:
                            row_num = 0
                        sel_buf = ""
                        if 1 <= row_num <= n:
                            edit_row = row_num
                            edit_buf = rows[row_num - 1].currency
                            edit_err = None
                            mode = "edit"
                            scroll_to(row_num)
                elif key == "a":
                    if not (collisions | invalid):
                        result = "accepted"; break
                elif key.isdigit():
                    sel_buf += key

            else:  # cell-edit mode
                page = max(1, viewport_h)
                if key == "escape":
                    mode = "select"; edit_buf = ""; edit_err = None; edit_row = 0
                elif key == "enter":
                    if not edit_err and is_valid_currency(edit_buf):
                        rows[edit_row - 1].currency = edit_buf
                        rows[edit_row - 1].confirmed = True
                        collisions, invalid = recompute(rows)
                        mode = "select"; edit_buf = ""; edit_err = None; edit_row = 0
                elif key == "up":
                    if edit_row > 1:
                        edit_row -= 1
                        edit_buf = rows[edit_row - 1].currency
                        edit_err = None
                        scroll_to(edit_row)
                elif key == "down":
                    if edit_row < n:
                        edit_row += 1
                        edit_buf = rows[edit_row - 1].currency
                        edit_err = None
                        scroll_to(edit_row)
                elif key == "pageup":
                    scroll_by(-page)
                elif key == "pagedown":
                    scroll_by(page)
                elif key == "backspace":
                    edit_buf = edit_buf[:-1]
                    edit_err = (
                        None if not edit_buf or is_valid_currency(edit_buf)
                        else f'"{edit_buf}" \u2014 must start with A\u2013Z; only A\u2013Z 0\u20139 \u2013 allowed'
                    )
                elif len(key) == 1 and key.isprintable() and key != "\t":
                    edit_buf += key.upper()
                    edit_err = (
                        None if is_valid_currency(edit_buf)
                        else f'"{edit_buf}" \u2014 must start with A\u2013Z; only A\u2013Z 0\u20139 \u2013 allowed'
                    )
                elif key == "ctrl_c":
                    result = "cancelled"; break

            refresh()

    finally:
        if _SIGWINCH is not None and _in_main_thread and _old_sigwinch is not None:
            signal.signal(_SIGWINCH, _old_sigwinch)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()   # leave cursor on a fresh line after the footer

    return result


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    rows = make_rows(FIXTURE)
    emit_warnings(rows)
    result = run(rows)
    if result == "accepted":
        print("Accepted \u2014 final currency map:")
        for r in rows:
            print(f"  {r.cmdty_id!r:12s}  \u2192  {r.currency}")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    main()
