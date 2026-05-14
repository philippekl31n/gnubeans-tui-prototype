#!/usr/bin/env python3
"""
tui_prototype.py — Interactive Beancount commodity symbol editor.

Renders inline in the terminal — no full-screen takeover, no TUI frame.
The table appears immediately below any pre-flight warnings and stays in
the scrollback buffer after exit.
"""

from __future__ import annotations

import os
import re
import select
import sys
import termios
import tty
from dataclasses import dataclass
from typing import Optional


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


# ─── ANSI helpers ─────────────────────────────────────────────────────────────

def _a(codes: str, t: str) -> str:
    return f"\033[{codes}m{t}\033[0m"

def red(t: str)   -> str: return _a("31;1", t)
def green(t: str) -> str: return _a("32;1", t)
def dim(t: str)   -> str: return _a("2",    t)
def bold(t: str)  -> str: return _a("1",    t)


# ─── Rendering ────────────────────────────────────────────────────────────────

def build_table(
    rows: list[Row],
    mode: str,
    vstart: int,
    viewport_h: int,
    edit_row: int,
    edit_buf: str,
    collisions: set[int],
) -> list[str]:
    """Return ANSI-coloured lines for the visible portion of the table."""
    n = len(rows)
    visible = rows[vstart: vstart + viewport_h]

    w_n = max(4, len(str(n)))
    w_c = max(8,  max((len(r.cmdty_id)   for r in rows), default=8))
    w_s = max(11, max((len(r.user_symbol) for r in rows), default=11))
    w_u = max(24, max((len(r.currency) + 3 for r in rows), default=24))

    def p(s: str, w: int) -> str:
        return s.ljust(w)[:w]

    H, h = "\u2501", "\u2500"  # ━ ─
    out: list[str] = []
    out.append(
        f"\u250f{H*(w_n+2)}\u2533{H*(w_c+2)}\u2533{H*(w_s+2)}\u2533{H*(w_u+2)}\u2513"
    )
    out.append(bold(
        f"\u2503 {p('#',w_n)} \u2503 {p('cmdty:id',w_c)} \u2503"
        f" {p('user_symbol',w_s)} \u2503 {p('CURRENCY',w_u)} \u2503"
    ))
    out.append(
        f"\u2521{H*(w_n+2)}\u2547{H*(w_c+2)}\u2547{H*(w_s+2)}\u2547{H*(w_u+2)}\u2529"
    )

    for row in visible:
        editing      = mode == "edit" and edit_row == row.num
        collision    = row.num in collisions
        confirmed_ok = row.confirmed and row.num not in collisions

        if editing:
            cur_cell = p(edit_buf + "\u2587", w_u)   # ▇ block cursor
        elif confirmed_ok:
            cur_cell = p(row.currency + " \u2713", w_u)  # ✓
        else:
            cur_cell = p(row.currency, w_u)

        line = (
            f"\u2502 {p(str(row.num),w_n)} \u2502 {p(row.cmdty_id,w_c)} \u2502"
            f" {p(row.user_symbol,w_s)} \u2502 {cur_cell} \u2502"
        )

        if collision:
            out.append(red(line))
        elif confirmed_ok:
            out.append(green(line))
        else:
            out.append(line)

    out.append(
        f"\u2514{h*(w_n+2)}\u2534{h*(w_c+2)}\u2534{h*(w_s+2)}\u2534{h*(w_u+2)}\u2518"
    )
    return out


def build_footer(
    mode: str,
    sel_buf: str,
    edit_row: int,
    edit_err: Optional[str],
    collisions: set[int],
    invalid: set[int],
    n_rows: int,
) -> str:
    if mode == "select":
        unresolved = len(collisions | invalid)
        hint = (
            "[ row number to edit ]"
            if unresolved else
            "[ row number to edit \u00b7 a accept all ]"
        )
        return f"{dim(hint)}: {bold(sel_buf)}\u2587"
    else:
        unresolved = len(collisions | invalid)
        pos = f"Row {edit_row} of {n_rows} \u00b7 {unresolved} unresolved"
        if edit_err:
            return f"{red(edit_err)}  {dim(pos)}"
        inst = "Enter to confirm \u00b7 Esc to cancel \u00b7 \u2191\u2193 move row"
        return f"{dim(inst)}  {dim(pos)}"


# ─── Inline display ───────────────────────────────────────────────────────────

class Display:
    """Renders and updates the table+footer inline in the terminal.

    On the first call to show(), lines are printed normally.  On subsequent
    calls the cursor is moved back up and lines are overwritten in place so
    the widget stays anchored in the scrollback buffer.
    """

    def __init__(self) -> None:
        self._prev_n = 0   # number of table lines already printed

    def show(self, table_lines: list[str], footer: str) -> None:
        n = len(table_lines)
        buf = ""
        if self._prev_n > 0:
            # Return to start of first table line:
            # \r  → go to column 0 of the footer line (current position)
            # \033[N]A → move up N lines to the first table line
            buf += f"\r\033[{self._prev_n}A"
        for line in table_lines:
            buf += f"\033[2K\r{line}\n"   # clear + overwrite each table line
        buf += f"\033[2K\r{footer}"        # clear + overwrite footer (no \n)
        sys.stdout.write(buf)
        sys.stdout.flush()
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

def run(rows: list[Row]) -> str:
    """Run the interactive editor. Returns 'accepted' or 'cancelled'."""
    n = len(rows)
    try:
        term_h = os.get_terminal_size().lines
        viewport_h = max(3, term_h - 6)   # leave headroom above for warnings
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
    display  = Display()

    def refresh() -> None:
        tbl = build_table(rows, mode, vstart, viewport_h, edit_row, edit_buf, collisions)
        ftr = build_footer(mode, sel_buf, edit_row, edit_err, collisions, invalid, n)
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

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    result = "cancelled"

    try:
        tty.setraw(fd)

        while True:
            key = read_key(fd)

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
