#!/usr/bin/env python3
"""
tui_prototype.py — Interactive Beancount commodity symbol editor.

Usage:
    python tui_prototype.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static
from textual import events
from rich.text import Text


# ─── Symbol logic ─────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"^[A-Z]([A-Z0-9'\-\.]{0,22}[A-Z0-9])?$")


def is_valid_currency(s: str) -> bool:
    """Return True if *s* is a valid Beancount currency symbol."""
    return bool(s and _CURRENCY_RE.match(s))


def suggest_currency(raw: str) -> str:
    """Sanitise an arbitrary commodity id into a valid Beancount currency."""
    s = raw.upper()
    s = re.sub(r"[^A-Z0-9'\-\.]", "-", s)
    s = re.sub(r"[-'\.]{2,}", "-", s)
    s = s.strip("-'.")
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
    user_symbol: str   # "(not set)" when absent
    suggested: str     # auto-suggested Beancount currency
    currency: str      # current working value (the editable field)
    confirmed: bool = False


FIXTURE: list[tuple[str, str]] = [
    ("AT&T",    ""),
    ("AT[T]",   ""),
    ("VBMPX",   ""),
    ("1003057", ""),
]


def make_rows(pairs: list[tuple[str, str]]) -> list[Row]:
    rows = []
    for i, (cid, usym) in enumerate(pairs, 1):
        sug = suggest_currency(cid)
        rows.append(Row(i, cid, usym or "(not set)", sug, sug))
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
    """Print pre-flight WARNINGs to stderr before the TUI starts.

    The ordering mirrors what a streaming processor would see:
    - invalid-symbol warning fires as each bad row is encountered
    - collision warning fires as soon as the *second* row that maps to the
      same suggested currency is encountered
    """
    seen: dict[str, list[str]] = {}   # suggested currency → [cmdty_ids]
    reported_collisions: set[str] = set()

    for r in rows:
        if not is_valid_currency(r.cmdty_id):
            print(
                f'WARNING: commodity "{r.cmdty_id}" is not a valid Beancount symbol'
                f' \u2014 suggesting "{r.suggested}"',
                file=sys.stderr,
            )
        seen.setdefault(r.suggested, []).append(r.cmdty_id)
        if len(seen[r.suggested]) > 1 and r.suggested not in reported_collisions:
            reported_collisions.add(r.suggested)
            ids = seen[r.suggested]
            parts = " and ".join(f'"{i}"' for i in ids)
            print(
                f'WARNING: collision \u2014 {parts} both produce the Beancount currency'
                f' "{r.suggested}". Assign distinct symbols in the plan.',
                file=sys.stderr,
            )


# ─── TUI App ──────────────────────────────────────────────────────────────────

class CommodityEditor(App[str]):
    """Two-mode table editor for resolving Beancount commodity symbols."""

    BINDINGS = [
        # Let ctrl+c exit cleanly rather than crashing
        Binding("ctrl+c", "force_quit", "Quit", priority=True, show=False),
    ]

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    #table-area {
        height: 1fr;
        overflow: hidden;
    }
    #footer-area {
        height: 1;
        background: $panel;
    }
    """

    def __init__(self, rows: list[Row]) -> None:
        super().__init__()
        self.rows = rows
        # Mode: "select" (footer input) | "edit" (cell input)
        self.mode: str = "select"
        # Row-selection mode: accumulate typed digits here
        self.sel_buf: str = ""
        # Cell-edit mode: accumulate typed characters here
        self.edit_buf: str = ""
        # 1-based index of the row being edited (0 = none)
        self.edit_row: int = 0
        # Validation error string shown in the footer during cell-edit
        self.edit_err: Optional[str] = None
        # Index (0-based) of the first visible data row
        self.viewport_start: int = 0
        # How many data rows fit in the current terminal height
        self.viewport_h: int = 10
        self.collisions, self.invalid = recompute(rows)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(id="table-area", expand=True)
        yield Static(id="footer-area")

    def on_mount(self) -> None:
        self.viewport_h = max(1, self.app.size.height - 5)
        self._refresh()

    def on_resize(self, event: events.Resize) -> None:
        self.viewport_h = max(1, event.size.height - 5)
        self._refresh()

    # ── Viewport helpers ──────────────────────────────────────────────────────

    def _scroll_to(self, row_num: int) -> None:
        """Ensure the given 1-based row number is visible."""
        idx = row_num - 1
        if idx < self.viewport_start:
            self.viewport_start = idx
        elif idx >= self.viewport_start + self.viewport_h:
            self.viewport_start = idx - self.viewport_h + 1
        self.viewport_start = max(0, self.viewport_start)

    def _scroll_by(self, delta: int) -> None:
        n = len(self.rows)
        limit = max(0, n - self.viewport_h)
        self.viewport_start = max(0, min(limit, self.viewport_start + delta))

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_table(self) -> Text:
        rows = self.rows
        n = len(rows)
        vstart = self.viewport_start
        visible = rows[vstart: vstart + self.viewport_h]

        # Dynamic column widths
        w_n = max(4, len(str(n)))
        w_c = max(8, max((len(r.cmdty_id) for r in rows), default=8))
        w_s = max(11, max((len(r.user_symbol) for r in rows), default=11))
        # +3 for " ✓" suffix and cursor char
        w_u = max(24, max((len(r.currency) + 3 for r in rows), default=24))

        def p(s: str, w: int) -> str:
            return s.ljust(w)[:w]

        H = "\u2501"  # ━ heavy horizontal
        h = "\u2500"  # ─ light horizontal
        top = f"\u250f{H*(w_n+2)}\u2533{H*(w_c+2)}\u2533{H*(w_s+2)}\u2533{H*(w_u+2)}\u2513\n"
        hdr = (
            f"\u2503 {p('#', w_n)} \u2503 {p('cmdty:id', w_c)} \u2503"
            f" {p('user_symbol', w_s)} \u2503 {p('CURRENCY', w_u)} \u2503\n"
        )
        sep = f"\u2521{H*(w_n+2)}\u2547{H*(w_c+2)}\u2547{H*(w_s+2)}\u2547{H*(w_u+2)}\u2529\n"
        bot = f"\u2514{h*(w_n+2)}\u2534{h*(w_c+2)}\u2534{h*(w_s+2)}\u2534{h*(w_u+2)}\u2518\n"

        result = Text(no_wrap=True)
        result.append(top)
        result.append(hdr, style="bold")
        result.append(sep)

        for row in visible:
            editing = self.mode == "edit" and self.edit_row == row.num
            collision = row.num in self.collisions
            # Only show green ✓ when confirmed AND not currently colliding
            confirmed_clean = row.confirmed and row.num not in self.collisions

            if editing:
                cur_cell = p(self.edit_buf + "\u2587", w_u)  # ▇ block cursor
            elif confirmed_clean:
                cur_cell = p(row.currency + " \u2713", w_u)  # ✓
            else:
                cur_cell = p(row.currency, w_u)

            line = (
                f"\u2502 {p(str(row.num), w_n)} \u2502 {p(row.cmdty_id, w_c)} \u2502"
                f" {p(row.user_symbol, w_s)} \u2502 {cur_cell} \u2502\n"
            )

            if collision:
                result.append(line, style="bold red")
            elif confirmed_clean:
                result.append(line, style="bold green")
            elif editing:
                result.append(line, style="bold yellow")
            else:
                result.append(line)

        result.append(bot)
        return result

    def _render_footer(self) -> Text:
        if self.mode == "select":
            unresolved = len(self.collisions | self.invalid)
            if unresolved:
                hint = "[ row number to edit ]"
            else:
                hint = "[ row number to edit \u00b7 a accept all ]"  # ·
            return Text.from_markup(
                f"[dim]{hint}[/dim]: [bold]{self.sel_buf}[/bold]\u2587"
            )
        else:
            n = len(self.rows)
            unresolved = len(self.collisions | self.invalid)
            pos = f"Row {self.edit_row} of {n} \u00b7 {unresolved} unresolved"
            if self.edit_err:
                return Text.from_markup(
                    f"[bold red]{self.edit_err}[/bold red]  [dim]{pos}[/dim]"
                )
            return Text.from_markup(
                f"[dim]Enter to confirm \u00b7 Esc to cancel \u00b7 \u2191\u2193 move row[/dim]"
                f"  [dim]{pos}[/dim]"
            )

    def _refresh(self) -> None:
        self.query_one("#table-area", Static).update(self._render_table())
        self.query_one("#footer-area", Static).update(self._render_footer())

    # ── Key handling ──────────────────────────────────────────────────────────

    async def on_key(self, event: events.Key) -> None:
        event.stop()
        key = event.key
        char = event.character  # actual unicode char, or None for special keys

        if self.mode == "select":
            self._handle_select(key, char)
        else:
            self._handle_edit(key, char)

        self._refresh()

    # ── Row-selection mode ────────────────────────────────────────────────────

    def _handle_select(self, key: str, char: Optional[str]) -> None:
        n = len(self.rows)
        page = max(1, self.viewport_h)

        if key == "escape":
            self.exit("cancelled")
        elif key in ("up", "pageup"):
            self._scroll_by(-page)
        elif key in ("down", "pagedown"):
            self._scroll_by(page)
        elif key == "backspace":
            self.sel_buf = self.sel_buf[:-1]
        elif key == "enter":
            if self.sel_buf:
                try:
                    row_num = int(self.sel_buf)
                except ValueError:
                    row_num = 0
                self.sel_buf = ""
                if 1 <= row_num <= n:
                    self._enter_edit(row_num)
        elif char and char.isdigit():
            self.sel_buf += char
        elif char == "a":
            unresolved = len(self.collisions | self.invalid)
            if unresolved == 0:
                self.exit("accepted")

    def _enter_edit(self, row_num: int) -> None:
        self.edit_row = row_num
        self.edit_buf = self.rows[row_num - 1].currency
        self.edit_err = None
        self.mode = "edit"
        self._scroll_to(row_num)

    # ── Cell-edit mode ────────────────────────────────────────────────────────

    def _handle_edit(self, key: str, char: Optional[str]) -> None:
        n = len(self.rows)
        page = max(1, self.viewport_h)

        if key == "escape":
            # Return to select mode without committing
            self.mode = "select"
            self.edit_buf = ""
            self.edit_err = None
            self.edit_row = 0

        elif key == "enter":
            # Confirm only when edit_buf is non-empty and valid
            if not self.edit_err and is_valid_currency(self.edit_buf):
                self._confirm_edit()

        elif key == "up":
            # Move cursor to previous row; discard uncommitted edit_buf
            if self.edit_row > 1:
                self.edit_row -= 1
                self.edit_buf = self.rows[self.edit_row - 1].currency
                self.edit_err = None
                self._scroll_to(self.edit_row)

        elif key == "down":
            if self.edit_row < n:
                self.edit_row += 1
                self.edit_buf = self.rows[self.edit_row - 1].currency
                self.edit_err = None
                self._scroll_to(self.edit_row)

        elif key == "pageup":
            self._scroll_by(-page)

        elif key == "pagedown":
            self._scroll_by(page)

        elif key == "backspace":
            self.edit_buf = self.edit_buf[:-1]
            self._validate()

        elif char and char.isprintable() and char not in ("\t",):
            self.edit_buf += char.upper()
            self._validate()

    def _validate(self) -> None:
        """Update self.edit_err based on current self.edit_buf."""
        if self.edit_buf and not is_valid_currency(self.edit_buf):
            self.edit_err = (
                f'"{self.edit_buf}" \u2014 must start with A\u2013Z; '
                f"only A\u2013Z 0\u20139 - . ' allowed"
            )
        else:
            self.edit_err = None

    def _confirm_edit(self) -> None:
        row = self.rows[self.edit_row - 1]
        row.currency = self.edit_buf
        row.confirmed = True
        # Re-evaluate all rows reactively
        self.collisions, self.invalid = recompute(self.rows)
        # Return to row-selection mode
        self.mode = "select"
        self.edit_buf = ""
        self.edit_err = None
        self.edit_row = 0

    def action_force_quit(self) -> None:
        self.exit("cancelled")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    rows = make_rows(FIXTURE)
    emit_warnings(rows)

    app = CommodityEditor(rows)
    result = app.run()

    if result == "accepted":
        print("\nAccepted \u2014 final currency map:")
        for r in rows:
            print(f"  {r.cmdty_id!r:12s}  \u2192  {r.currency}")
    elif result == "cancelled":
        print("\nCancelled.")
    else:
        # ctrl+c / window close
        print("\nExited.")


if __name__ == "__main__":
    main()
