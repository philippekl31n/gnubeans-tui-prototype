#!/usr/bin/env python3
"""
test_tui.py — Behavioral and layout tests for tui_prototype.py.

Tests are written against the #6 (Rich-renderer) design:
  - Rich table with box=SIMPLE_HEAD (header underline only, no outer frame)
  - N + 2 lines per table render (header + rule + N data rows)
  - Two-line footer: list[str] of length 2 (hint line + prompt line)
  - Amber #FFAA00 + ≠ glyph for collision rows
  - Red #FF4466 + ✗ glyph for invalid rows
  - Green #04B575 + ✓ glyph for confirmed-ok rows
  - Bold #ECFD65 + ▸ glyph in indicator column for the editing row
  - Indicator column (·/✓/≠/✗/▸) present in every data row

Run with:  python3 -m pytest test_tui.py -v
"""

from __future__ import annotations

import io
import os
import pty
import re
import select
import sys
import threading
import time
import unittest
from typing import Optional

import pytest

from tui_prototype import (
    FIXTURE,
    LARGE_FIXTURE,
    Display,
    Row,
    build_footer,
    build_table,
    emit_warnings,
    make_rows,
    recompute,
)
import tui_prototype


# ─── ANSI helper ──────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\033\[[^a-zA-Z]*[a-zA-Z]")


def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ─── PTY driver ───────────────────────────────────────────────────────────────

def _drive(
    keystrokes: list[bytes],
    rows: Optional[list[Row]] = None,
    timeout: float = 5.0,
) -> tuple[Optional[str], bytes]:
    """
    Run the TUI with scripted keyboard input through a pty.

    Creates a pty master/slave pair.  The slave fd is used for both the
    TUI's keyboard input (stdin_fd=slave) and its rendered output
    (output=slave_out, a text file wrapping a dup of slave).  All TUI
    output flows slave_out → slave → pty kernel → master.

    A background *drain thread* continuously reads from the master fd so
    the pty kernel buffer never fills up and blocks the TUI's write calls
    (which would otherwise deadlock against the main thread sleeping
    between keystroke sends).

    Keystrokes are written to master with 60 ms gaps.

    Returns (result_str, raw_output_bytes).
    """
    if rows is None:
        rows = make_rows(FIXTURE)

    master, slave = pty.openpty()

    # Duplicate slave so closing slave_out doesn't close the fd that
    # tty.setraw() / termios are still operating on.
    slave_out = os.fdopen(os.dup(slave), "w", buffering=1, closefd=True)

    result: list[Optional[str]] = [None]
    exc: list[Optional[BaseException]] = [None]
    chunks: list[bytes] = []
    _drain_stop = threading.Event()

    def _runner() -> None:
        try:
            result[0] = tui_prototype.run(rows, stdin_fd=slave, output=slave_out)
        except BaseException as e:  # noqa: BLE001
            exc[0] = e

    def _drainer() -> None:
        """Continuously empty the master fd so the TUI can write freely."""
        while not _drain_stop.is_set():
            r, _, _ = select.select([master], [], [], 0.05)
            if r:
                try:
                    chunks.append(os.read(master, 4096))
                except OSError:
                    break

    t = threading.Thread(target=_runner, daemon=True)
    dt = threading.Thread(target=_drainer, daemon=True)
    t.start()
    dt.start()

    # Allow the TUI to render its initial frame before sending any input.
    time.sleep(0.20)

    for key in keystrokes:
        try:
            os.write(master, key)
        except OSError:
            break
        time.sleep(0.06)

    t.join(timeout=timeout)

    # Close slave_out and let the drainer flush the remaining tail.
    try:
        slave_out.close()
    except OSError:
        pass
    time.sleep(0.20)
    _drain_stop.set()
    dt.join(timeout=1.0)

    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass

    # Surface any exception raised inside the runner thread so tests fail
    # loudly instead of silently returning result=None.
    if exc[0] is not None:
        raise exc[0]

    # Guard: if the runner thread is still alive the TUI hung; surface it.
    if t.is_alive():
        raise TimeoutError(
            f"TUI runner thread did not finish within {timeout}s timeout"
        )

    return result[0], b"".join(chunks)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Inline / layout tests  (PTY-based)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInlineLayout(unittest.TestCase):
    """Verify the TUI renders inline without alternate-screen takeover."""

    # ── tests 4a/4b ───────────────────────────────────────────────────────────

    def test_no_alternate_screen_on(self) -> None:
        """Raw output must not contain the alternate-screen-on sequence."""
        _, raw = _drive([b"\x03"])
        self.assertNotIn(b"\033[?1049h", raw)

    def test_no_alternate_screen_off(self) -> None:
        """Raw output must not contain the alternate-screen-restore sequence."""
        _, raw = _drive([b"\x03"])
        self.assertNotIn(b"\033[?1049l", raw)

    # ── test 5 ────────────────────────────────────────────────────────────────

    def test_table_header_appears_in_output(self) -> None:
        """Column header 'cmdty:id' must appear in the captured output."""
        _, raw = _drive([b"\x03"])
        clean = strip_ansi(raw.decode("utf-8", errors="replace"))
        self.assertIn("cmdty:id", clean)

    def test_no_box_corners_in_borderless_design(self) -> None:
        """SIMPLE_HEAD box style must produce no outer box corners (┏ ┗ ┓ ┘)."""
        _, raw = _drive([b"\x03"])
        text = raw.decode("utf-8", errors="replace")
        self.assertNotIn("\u250f", text)  # ┏ top-left corner must be absent
        self.assertNotIn("\u2513", text)  # ┓ top-right corner must be absent

    # ── test 6 (unit version) ─────────────────────────────────────────────────

    def test_no_blank_lines_in_rendered_frame(self) -> None:
        """Display.show() must not produce consecutive blank lines."""
        rows = make_rows(FIXTURE)
        collisions, _ = recompute(rows)
        table_lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        footer_lines = build_footer("select", "", 0, None, collisions, set(), len(rows))
        buf = io.StringIO()
        Display(output=buf).show(table_lines, footer_lines)
        self.assertNotIn("\n\n", strip_ansi(buf.getvalue()))

    def test_footer_immediately_follows_last_table_line(self) -> None:
        """No blank lines appear between the last data row and the footer.

        In the #6 borderless design there is no bottom border line;
        table_lines[-1] is the last data row itself.
        """
        rows = make_rows(FIXTURE)
        collisions, _ = recompute(rows)
        table_lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        footer_lines = build_footer("select", "", 0, None, collisions, set(), len(rows))
        buf = io.StringIO()
        Display(output=buf).show(table_lines, footer_lines)
        clean = strip_ansi(buf.getvalue())
        last_data_line = strip_ansi(table_lines[-1])  # last data row (no border in #6)
        idx = clean.rfind(last_data_line)
        self.assertNotEqual(idx, -1, "Last table line not found in output")
        after = clean[idx + len(last_data_line):]
        self.assertFalse(
            after.startswith("\n\n"),
            "Blank line found between last table line and footer",
        )

    def test_no_blank_line_between_last_data_row_and_footer_pty(self) -> None:
        """PTY output: the line after the row-4 data must not be blank.

        Display.show() writes each line as b'\\033[2K\\r{content}\\n', so
        splitting on '\\n' and stripping leading '\\r' gives the actual
        content lines without spurious blank lines.

        In the #6 borderless design there is no bottom border; the hint line
        of the two-line footer follows the last data row directly.
        """
        _, raw = _drive([b"\x03"])
        text = raw.decode("utf-8", errors="replace")
        # Strip ANSI, split on \n, remove the leading \r that Display.show()
        # places at the start of each line (it moves to column 0, not a newline).
        clean = strip_ansi(text)
        lines = [part.lstrip("\r") for part in clean.split("\n")]
        # Locate the last occurrence of the line containing "1003057".
        idx = None
        for i, line in enumerate(lines):
            if "1003057" in line:
                idx = i
        self.assertIsNotNone(idx, "Row containing '1003057' not found in PTY output")
        # The line immediately after must not be blank.
        # Current design: bottom border (└─…) appears there.
        # Post-#6: footer hint line appears there directly.
        next_line = lines[idx + 1] if idx is not None and idx + 1 < len(lines) else ""
        self.assertTrue(
            next_line.strip(),
            f"Blank line found immediately after row-4 data line (index {idx})",
        )

    # ── test 7 ────────────────────────────────────────────────────────────────

    def test_cursor_up_emitted_on_rerender(self) -> None:
        """A second keystroke causes Display to emit a cursor-up escape."""
        _, raw = _drive([b"1", b"\x03"])
        self.assertRegex(raw.decode("utf-8", errors="replace"), r"\033\[\d+A")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Cancellation tests  (PTY-based)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCancellation(unittest.TestCase):

    def test_ctrl_c_returns_cancelled(self) -> None:
        result, _ = _drive([b"\x03"])
        self.assertEqual(result, "cancelled")

    def test_escape_returns_cancelled(self) -> None:
        result, _ = _drive([b"\x1b"])
        self.assertEqual(result, "cancelled")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Interaction flow tests  (PTY-based)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInteractionFlows(unittest.TestCase):

    def test_select_edit_then_cancel(self) -> None:
        """Open row 3 for editing, Esc back to select, then Esc to cancel."""
        result, _ = _drive([
            b"3", b"\r",  # type "3" → sel_buf; Enter → edit mode on row 3
            b"\x1b",      # Esc → back to select mode
            b"\x1b",      # Esc → cancel session
        ])
        self.assertEqual(result, "cancelled")

    def test_edit_confirm_accept(self) -> None:
        """Resolve the two collision rows, then accept all."""
        # On entry to edit mode the buffer is pre-filled with the current
        # currency value ("AT-T", 4 chars).  Backspace × 4 clears it.
        BS = b"\x7f"
        keystrokes: list[bytes] = (
            # Row 1 → ATANDT
            [b"1", b"\r"] + [BS] * 4 +
            [b"A", b"T", b"A", b"N", b"D", b"T", b"\r"] +
            # Row 2 → ATT
            [b"2", b"\r"] + [BS] * 4 +
            [b"A", b"T", b"T", b"\r"] +
            # rows 3 & 4 are already valid and collision-free → accept
            [b"a"]
        )
        result, _ = _drive(keystrokes, timeout=8.0)
        self.assertEqual(result, "accepted")

    def test_edit_all_four_rows_then_accept(self) -> None:
        """Edit all four rows explicitly before accepting — mirrors plan step 11."""
        # Row 3 (VBMPX) and row 4 (C1003057) are already valid; we still open
        # them to confirm the edit→select→accept round-trip with every row.
        BS = b"\x7f"
        keystrokes: list[bytes] = (
            # Row 1 → ATANDT  (clears 4-char "AT-T")
            [b"1", b"\r"] + [BS] * 4 +
            [b"A", b"T", b"A", b"N", b"D", b"T", b"\r"] +
            # Row 2 → ATT    (clears 4-char "AT-T")
            [b"2", b"\r"] + [BS] * 4 +
            [b"A", b"T", b"T", b"\r"] +
            # Row 4 → CTHREE (clears 8-char "C1003057")
            [b"4", b"\r"] + [BS] * 8 +
            [b"C", b"T", b"H", b"R", b"E", b"E", b"\r"] +
            # Row 3 → VBMPX  (confirmed unchanged; clears 5-char "VBMPX")
            [b"3", b"\r"] + [BS] * 5 +
            [b"V", b"B", b"M", b"P", b"X", b"\r"] +
            # All four rows confirmed, zero collisions → accept
            [b"a"]
        )
        result, _ = _drive(keystrokes, timeout=12.0)
        self.assertEqual(result, "accepted")

    def test_accept_blocked_while_collisions_remain(self) -> None:
        """Pressing 'a' with active collisions must NOT cause run() to return."""
        rows = make_rows(FIXTURE)  # rows 1 & 2 both map to AT-T (collision)
        master, slave = pty.openpty()
        slave_out = os.fdopen(os.dup(slave), "w", buffering=1, closefd=True)
        result: list[Optional[str]] = [None]
        drain_stop = threading.Event()

        def _runner() -> None:
            result[0] = tui_prototype.run(rows, stdin_fd=slave, output=slave_out)

        def _drainer() -> None:
            while not drain_stop.is_set():
                r, _, _ = select.select([master], [], [], 0.05)
                if r:
                    try:
                        os.read(master, 4096)
                    except OSError:
                        break

        t = threading.Thread(target=_runner, daemon=True)
        dt = threading.Thread(target=_drainer, daemon=True)
        t.start()
        dt.start()
        time.sleep(0.20)  # let TUI draw the initial frame

        os.write(master, b"a")   # collisions exist → must be a no-op
        time.sleep(0.35)

        self.assertTrue(
            t.is_alive(),
            "run() returned despite active collisions — 'a' must be blocked",
        )

        # Cleanup: send Ctrl+C so the thread exits cleanly.
        os.write(master, b"\x03")
        t.join(timeout=2.0)
        drain_stop.set()
        dt.join(timeout=1.0)
        try:
            slave_out.close()
        except OSError:
            pass
        for fd in (master, slave):
            try:
                os.close(fd)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# 4. build_table unit tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildTable(unittest.TestCase):

    def _rows(self) -> list[Row]:
        return make_rows(FIXTURE)

    def test_line_count_simple_head_design(self) -> None:
        """SIMPLE_HEAD / no-edge design: 1 header + 1 rule + N data rows = N + 2."""
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        self.assertEqual(len(lines), len(rows) + 2)  # = 6 for N=4

    def test_collision_row_uses_amber_and_ne_glyph(self) -> None:
        """Collision rows show ≠ in the indicator column; no red \033[31;1m wrap."""
        rows = self._rows()
        collisions, _ = recompute(rows)  # rows 1 & 2 collide on AT-T
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # In the #6 design: lines[0]=header, lines[1]=rule, lines[2]=row.num=1
        row1_line = lines[2]
        self.assertIn("\u2260", strip_ansi(row1_line))  # ≠ present
        self.assertNotIn("\033[31;1m", row1_line)       # raw red wrap absent

    def test_collision_row_has_no_checkmark(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # lines[2] = data row for row.num=1 (AT&T, collision)
        self.assertNotIn("\u2713", strip_ansi(lines[2]))  # ✓ absent

    def test_confirmed_row_uses_green_and_check_glyph(self) -> None:
        """Confirmed-ok rows show ✓ in the indicator column; no \033[32;1m wrap."""
        rows = self._rows()
        rows[2].confirmed = True   # row 3 = VBMPX, no collision
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # In the #6 design: lines[0]=header, lines[1]=rule, lines[4]=row.num=3
        row3_line = lines[4]
        self.assertIn("\u2713", strip_ansi(row3_line))   # ✓ present
        self.assertNotIn("\033[32;1m", row3_line)        # raw green wrap absent

    def test_confirmed_ok_row_has_checkmark(self) -> None:
        rows = self._rows()
        rows[2].confirmed = True
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # lines[4] = data row for row.num=3 (VBMPX) in #6 design
        self.assertIn("\u2713", strip_ansi(lines[4]))  # ✓ present

    def test_editing_row_shows_edit_buffer(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        # edit_row=3 means row.num=3 (VBMPX); in #6 design lines[4]=row.num=3
        self.assertIn("NEWVAL", strip_ansi(lines[4]))

    def test_editing_row_has_right_arrow_glyph(self) -> None:
        """Editing row shows ▸ (U+25B8) in the indicator column, not ▇."""
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        # edit_row=3 → row.num=3 (VBMPX); in #6 design lines[4]=row.num=3
        self.assertIn("\u25b8", strip_ansi(lines[4]))   # ▸ in indicator column
        self.assertNotIn("\u2587", strip_ansi(lines[4]))  # ▇ block cursor gone

    def test_non_editing_row_no_block_cursor(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        # lines[2] = data row for row.num=1 (AT&T) — not the editing row
        self.assertNotIn("\u2587", strip_ansi(lines[2]))  # ▇ block cursor absent
        self.assertNotIn("\u25b8", strip_ansi(lines[2]))  # ▸ edit indicator absent

    def test_viewport_slicing_limits_data_rows(self) -> None:
        """viewport_h=2 yields exactly 2 data rows in the output."""
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, 2, 0, "", collisions)
        # #6 design: 1 header + 1 rule + 2 data = 4
        self.assertEqual(len(lines), 4)

    def test_indicator_glyphs_present_in_new_design(self) -> None:
        """Every data row carries an indicator glyph in the leftmost column."""
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # In the #6 design: lines[0]=header, lines[1]=rule, lines[2..5]=data rows
        data_lines = lines[2: 2 + len(rows)]
        # Collision rows (row.num 1 & 2) must carry ≠
        for line in data_lines[:2]:
            self.assertIn("\u2260", strip_ansi(line),
                          "Expected ≠ in collision row indicator column")
        # Clean, unconfirmed rows (row.num 3 & 4) must carry · (dim dot)
        for line in data_lines[2:]:
            clean = strip_ansi(line)
            self.assertIn("\u00b7", clean,
                          "Expected · in clean-unconfirmed row indicator column")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. build_footer unit tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildFooter(unittest.TestCase):

    def _collisions_invalid(self) -> tuple[set[int], set[int]]:
        return recompute(make_rows(FIXTURE))

    # ── test 18 ───────────────────────────────────────────────────────────────

    def test_footer_is_list_of_two_lines(self) -> None:
        """build_footer() must return list[str] with exactly 2 elements."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "", 0, None, collisions, invalid, 4)
        self.assertIsInstance(footer, list)
        self.assertEqual(len(footer), 2)

    # ── test 19 ───────────────────────────────────────────────────────────────

    def test_select_unresolved_excludes_accept_all(self) -> None:
        """Hint line (index 0) must omit 'accept all' when collisions remain."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "", 0, None, collisions, invalid, 4)
        self.assertNotIn("accept all", strip_ansi(footer[0]))

    def test_select_zero_unresolved_includes_accept_all(self) -> None:
        """Hint line (index 0) must include 'accept all' when nothing is unresolved."""
        footer = build_footer("select", "", 0, None, set(), set(), 4)
        self.assertIn("accept all", strip_ansi(footer[0]))

    # ── test 20 ───────────────────────────────────────────────────────────────

    def test_select_footer_contains_sel_buf(self) -> None:
        """Typed digits must appear on the prompt line (index 1), after the › glyph."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "42", 0, None, collisions, invalid, 4)
        self.assertIn("42", strip_ansi(footer[1]))
        self.assertIn("\u203a", footer[1])  # › prompt glyph on line 1

    def test_empty_buffer_prompt_shows_dim_placeholder(self) -> None:
        """When no digits typed yet the prompt line shows a · placeholder before the cursor."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "", 0, None, collisions, invalid, 4)
        self.assertIn("\u00b7", strip_ansi(footer[1]))  # · placeholder present
        self.assertIn("\u203a", footer[1])              # › prompt glyph still there

    # ── test 21 ───────────────────────────────────────────────────────────────

    def test_edit_error_text_appears_in_footer(self) -> None:
        """Error message text must appear on the hint line (index 0)."""
        collisions, invalid = self._collisions_invalid()
        err = '"BAD!" \u2014 must start with A\u2013Z'
        footer = build_footer("edit", "", 1, err, collisions, invalid, 4)
        self.assertIn("BAD!", strip_ansi(footer[0]))

    def test_edit_error_uses_amber_warning_badge(self) -> None:
        """Error state: ⚠ badge on line 0; no full-line red \033[31;1m wrap."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, "bad symbol", collisions, invalid, 4)
        self.assertIn("\u26a0", strip_ansi(footer[0]))  # ⚠ present on hint line
        self.assertNotIn("\033[31;1m", footer[0])       # no full-line red wrap

    # ── test 22 ───────────────────────────────────────────────────────────────

    def test_edit_clean_contains_confirm_and_cancel(self) -> None:
        """Hint line (index 0) must contain confirm and cancel hints."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, None, collisions, invalid, 4)
        clean = strip_ansi(footer[0])
        self.assertIn("confirm", clean)
        self.assertIn("cancel", clean)

    def test_edit_clean_contains_unresolved_count(self) -> None:
        """Hint line (index 0) must contain the unresolved count."""
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, None, collisions, invalid, 4)
        self.assertIn("unresolved", strip_ansi(footer[0]))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Display cursor-movement tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDisplay(unittest.TestCase):
    """Unit tests for Display.show() cursor-up rewrite behaviour."""

    _TABLE = ["header", "rule", "row1", "row2", "row3"]
    # Two-line footer as specified by #6: hint line + prompt line.
    _FOOTER = [
        "  \u2191\u2193 scroll  \u00b7  type a row number",
        "  \u203a  _",
    ]

    # ── test 23 ───────────────────────────────────────────────────────────────

    def test_first_render_no_cursor_up(self) -> None:
        """The very first show() call must not emit a cursor-up escape."""
        buf = io.StringIO()
        d = Display(output=buf)
        d.show(self._TABLE, self._FOOTER)
        self.assertNotRegex(buf.getvalue(), r"\033\[\d+A")

    # ── test 24 ───────────────────────────────────────────────────────────────

    def test_second_render_emits_cursor_up(self) -> None:
        """The second show() call must emit at least one cursor-up escape."""
        buf = io.StringIO()
        d = Display(output=buf)
        d.show(self._TABLE, self._FOOTER)
        buf.truncate(0); buf.seek(0)
        d.show(self._TABLE, self._FOOTER)
        self.assertRegex(buf.getvalue(), r"\033\[\d+A")

    def test_second_render_cursor_up_count(self) -> None:
        """N in \\033[NA must equal len(table_lines) + len(footer_lines) - 1.

        The -1 accounts for the last footer line having no trailing \\n, so
        the cursor ends on that line rather than one below it.
        For _TABLE (5 lines) + _FOOTER (2 lines): expected N = 5 + 2 - 1 = 6.
        """
        buf = io.StringIO()
        d = Display(output=buf)
        d.show(self._TABLE, self._FOOTER)
        buf.truncate(0); buf.seek(0)
        d.show(self._TABLE, self._FOOTER)
        m = re.search(r"\033\[(\d+)A", buf.getvalue())
        self.assertIsNotNone(m, "No cursor-up escape found on second render")
        n = int(m.group(1))  # type: ignore[union-attr]
        expected = len(self._TABLE) + len(self._FOOTER) - 1
        self.assertEqual(n, expected)

    def test_second_render_starts_with_carriage_return(self) -> None:
        """Rewrite prefix must start with \\r to go to column 0."""
        buf = io.StringIO()
        d = Display(output=buf)
        d.show(self._TABLE, self._FOOTER)
        buf.truncate(0); buf.seek(0)
        d.show(self._TABLE, self._FOOTER)
        self.assertTrue(buf.getvalue().startswith("\r\033["))


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Warning output tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmitWarnings(unittest.TestCase):
    """Tests for emit_warnings() using the FIXTURE (4-row standard input)."""

    def _capture(self) -> list[str]:
        rows = make_rows(FIXTURE)
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            emit_warnings(rows)
        finally:
            sys.stdout = old
        text = buf.getvalue().rstrip("\n")
        return text.split("\n")

    # ── test 25 ───────────────────────────────────────────────────────────────

    def test_exactly_four_warning_lines(self) -> None:
        self.assertEqual(len(self._capture()), 4)

    def test_lines_0_and_1_are_commodity_warnings(self) -> None:
        lines = self._capture()
        self.assertTrue(lines[0].startswith("WARNING: commodity"), lines[0])
        self.assertTrue(lines[1].startswith("WARNING: commodity"), lines[1])

    def test_line_2_is_collision_warning(self) -> None:
        lines = self._capture()
        self.assertTrue(lines[2].startswith("WARNING: collision"), lines[2])

    def test_line_3_is_commodity_warning(self) -> None:
        lines = self._capture()
        self.assertTrue(lines[3].startswith("WARNING: commodity"), lines[3])

    def test_collision_warning_names_both_source_ids(self) -> None:
        lines = self._capture()
        self.assertIn('"AT&T"', lines[2])
        self.assertIn('"AT[T]"', lines[2])

    def test_collision_warning_names_currency(self) -> None:
        lines = self._capture()
        self.assertIn('"AT-T"', lines[2])


# ═══════════════════════════════════════════════════════════════════════════════
# 8. LARGE_FIXTURE state-composition tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLargeFixture(unittest.TestCase):
    """Verify that LARGE_FIXTURE has the required spread of initial row states."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = make_rows(LARGE_FIXTURE)
        cls.collisions, cls.invalid = recompute(cls.rows)

    def test_large_fixture_is_importable(self) -> None:
        """LARGE_FIXTURE must be importable from tui_prototype."""
        self.assertIsInstance(LARGE_FIXTURE, list)

    def test_large_fixture_has_at_least_20_rows(self) -> None:
        self.assertGreaterEqual(len(LARGE_FIXTURE), 20)

    def test_large_fixture_has_at_least_two_collision_pairs(self) -> None:
        """recompute() must surface at least 4 collision row-nums (2 pairs × 2 rows)."""
        self.assertGreaterEqual(len(self.collisions), 4,
            f"Expected ≥4 collision row nums; got {self.collisions}")

    def test_large_fixture_has_invalid_rows(self) -> None:
        """recompute() must surface at least one invalid row num."""
        self.assertGreater(len(self.invalid), 0,
            "Expected at least one invalid row (currency not matching Beancount pattern)")

    def test_large_fixture_invalid_row_uses_cross_glyph_in_table(self) -> None:
        """The invalid row must show ✗ in the indicator column of build_table()."""
        lines = build_table(
            self.rows, "select", 0, len(self.rows), 0, "", self.collisions, self.invalid
        )
        data_lines = lines[2:]
        invalid_nums = self.invalid
        found = False
        for row in self.rows:
            if row.num in invalid_nums:
                line_idx = row.num - 1
                if line_idx < len(data_lines):
                    if "\u2717" in strip_ansi(data_lines[line_idx]):
                        found = True
                        break
        self.assertTrue(found, "No ✗ glyph found in invalid row's rendered line")

    def test_large_fixture_has_pre_confirmed_rows(self) -> None:
        """make_rows(LARGE_FIXTURE) must produce at least one confirmed=True row."""
        confirmed = [r for r in self.rows if r.confirmed]
        self.assertGreater(len(confirmed), 0,
            "Expected at least one pre-confirmed row; found none")

    def test_large_fixture_confirmed_rows_show_check_glyph(self) -> None:
        """Pre-confirmed, non-collision rows show ✓ in the indicator column."""
        confirmed_ok = [
            r for r in self.rows
            if r.confirmed and r.num not in self.collisions and r.num not in self.invalid
        ]
        self.assertGreater(len(confirmed_ok), 0, "No confirmed-ok rows to check")
        lines = build_table(
            self.rows, "select", 0, len(self.rows), 0, "", self.collisions, self.invalid
        )
        data_lines = lines[2:]
        for row in confirmed_ok:
            line_idx = row.num - 1
            if line_idx < len(data_lines):
                self.assertIn("\u2713", strip_ansi(data_lines[line_idx]),
                    f"Expected ✓ in confirmed row {row.num}")

    def test_large_fixture_has_clean_unconfirmed_rows(self) -> None:
        """make_rows(LARGE_FIXTURE) must include rows that are not confirmed, not in
        collision, and not invalid."""
        clean = [
            r for r in self.rows
            if not r.confirmed
            and r.num not in self.collisions
            and r.num not in self.invalid
        ]
        self.assertGreater(len(clean), 0,
            "Expected at least one clean unconfirmed row")

    def test_large_fixture_clean_rows_show_dot_glyph(self) -> None:
        """Clean unconfirmed rows show · in the indicator column."""
        clean = [
            r for r in self.rows
            if not r.confirmed
            and r.num not in self.collisions
            and r.num not in self.invalid
        ]
        lines = build_table(
            self.rows, "select", 0, len(self.rows), 0, "", self.collisions, self.invalid
        )
        data_lines = lines[2:]
        for row in clean:
            line_idx = row.num - 1
            if line_idx < len(data_lines):
                self.assertIn("\u00b7", strip_ansi(data_lines[line_idx]),
                    f"Expected · in clean unconfirmed row {row.num}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
