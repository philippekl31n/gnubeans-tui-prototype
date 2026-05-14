#!/usr/bin/env python3
"""
test_tui.py — Behavioral and layout tests for tui_prototype.py.

Tests are written against the CURRENT design:
  - Hand-rolled ANSI escape codes
  - Full box-border table (┏ top + ┗ bottom, ┡ separator)
  - Single-line footer (str)
  - Red ANSI (\033[31;1m) for collision rows
  - Green ANSI (\033[32;1m) for confirmed-ok rows

Assertions that will change after task #6 (Rich renderer, borderless
SIMPLE_HEAD table, two-line footer, amber=collision / red=invalid semantic
states, indicator glyph column) are marked:

    # TODO: update after #6 — <what changes and how>

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

    def test_box_corners_present_in_current_design(self) -> None:
        # TODO: update after #6 — SIMPLE_HEAD removes outer box corners;
        # assertIn('\u250f') should flip to assertNotIn once #6 is merged.
        _, raw = _drive([b"\x03"])
        text = raw.decode("utf-8", errors="replace")
        self.assertIn("\u250f", text)  # ┏ top-left corner (current design)

    # ── test 6 (unit version) ─────────────────────────────────────────────────

    def test_no_blank_lines_in_rendered_frame(self) -> None:
        """Display.show() must not produce consecutive blank lines."""
        rows = make_rows(FIXTURE)
        collisions, _ = recompute(rows)
        table_lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        footer = build_footer("select", "", 0, None, collisions, set(), len(rows))
        buf = io.StringIO()
        Display(output=buf).show(table_lines, footer)
        self.assertNotIn("\n\n", strip_ansi(buf.getvalue()))

    def test_footer_immediately_follows_last_table_line(self) -> None:
        """No blank lines appear between the bottom border and the footer."""
        rows = make_rows(FIXTURE)
        collisions, _ = recompute(rows)
        table_lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        footer = build_footer("select", "", 0, None, collisions, set(), len(rows))
        buf = io.StringIO()
        Display(output=buf).show(table_lines, footer)
        clean = strip_ansi(buf.getvalue())
        last_border = strip_ansi(table_lines[-1])  # bottom border line
        idx = clean.rfind(last_border)
        self.assertNotEqual(idx, -1, "Bottom border line not found in output")
        after = clean[idx + len(last_border):]
        self.assertFalse(
            after.startswith("\n\n"),
            "Blank line found between table bottom border and footer",
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

    def test_line_count_current_design(self) -> None:
        # TODO: update after #6 — SIMPLE_HEAD/no-edge design gives 2 + N lines
        # (header row + underline rule + N data rows = 6 for N=4).
        # Current box design: 1 top border + 1 header + 1 separator + N data
        # + 1 bottom border = N + 4.  For N=4 → 8 lines.
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        self.assertEqual(len(lines), len(rows) + 4)  # = 8

    def test_collision_row_uses_red_ansi(self) -> None:
        # TODO: update after #6 — collision rows use amber (#FFAA00) + ≠ glyph
        # + strikethrough on the CURRENCY cell; \033[31;1m is removed entirely.
        rows = self._rows()
        collisions, _ = recompute(rows)  # rows 1 & 2 collide on AT-T
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        # Data rows start at index 3 (top-border + header + separator).
        row1_line = lines[3]
        self.assertIn("\033[31;1m", row1_line)

    def test_collision_row_has_no_checkmark(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        self.assertNotIn("\u2713", strip_ansi(lines[3]))  # ✓ absent

    def test_confirmed_ok_row_uses_green_ansi(self) -> None:
        # TODO: update after #6 — confirmed rows use #04B575 colour + ✓ glyph
        # in the indicator column; \033[32;1m is replaced by a Rich colour tag.
        rows = self._rows()
        rows[2].confirmed = True   # row 3 = VBMPX, no collision
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        row3_line = lines[5]  # index 3 (header block) + row-index 2
        self.assertIn("\033[32;1m", row3_line)

    def test_confirmed_ok_row_has_checkmark(self) -> None:
        rows = self._rows()
        rows[2].confirmed = True
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        self.assertIn("\u2713", strip_ansi(lines[5]))  # ✓ present

    def test_editing_row_shows_edit_buffer(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        self.assertIn("NEWVAL", strip_ansi(lines[5]))

    def test_editing_row_has_block_cursor_glyph(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        # TODO: update after #6 — current design shows ▇ (U+2587) inline in
        # the CURRENCY cell; post-#6 uses ▸ (U+25B8) in the indicator column.
        self.assertIn("\u2587", lines[5])  # ▇ block cursor present (raw line)

    def test_non_editing_row_no_block_cursor(self) -> None:
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "edit", 0, len(rows), 3, "NEWVAL", collisions)
        self.assertNotIn("\u2587", strip_ansi(lines[3]))  # row 1 not editing

    def test_viewport_slicing_limits_data_rows(self) -> None:
        """viewport_h=2 yields exactly 2 data rows in the output."""
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, 2, 0, "", collisions)
        # 1 top + 1 header + 1 sep + 2 data + 1 bottom = 6
        self.assertEqual(len(lines), 6)

    def test_no_indicator_glyph_column_in_current_design(self) -> None:
        # TODO: update after #6 — post-#6 adds an indicator column with
        # ·, ✓, ≠, ✗, ▸ glyphs; this test should be removed / replaced.
        rows = self._rows()
        collisions, _ = recompute(rows)
        lines = build_table(rows, "select", 0, len(rows), 0, "", collisions)
        for line in lines[3:3 + len(rows)]:  # data rows only
            clean = strip_ansi(line)
            self.assertNotIn("\u2260", clean)  # ≠ absent in current design
            self.assertNotIn("\u2717", clean)  # ✗ absent in current design


# ═══════════════════════════════════════════════════════════════════════════════
# 5. build_footer unit tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildFooter(unittest.TestCase):

    def _collisions_invalid(self) -> tuple[set[int], set[int]]:
        return recompute(make_rows(FIXTURE))

    # ── test 18 ───────────────────────────────────────────────────────────────

    def test_footer_is_str_in_current_design(self) -> None:
        # TODO: update after #6 — footer becomes list[str] with exactly 2
        # elements (hint line + prompt line).  Replace assertIsInstance(str)
        # with assertIsInstance(list) and assertEqual(len(...), 2).
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "", 0, None, collisions, invalid, 4)
        self.assertIsInstance(footer, str)

    # ── test 19 ───────────────────────────────────────────────────────────────

    def test_select_unresolved_excludes_accept_all(self) -> None:
        # TODO: update after #6 — check line 0 of the 2-element footer list.
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "", 0, None, collisions, invalid, 4)
        self.assertNotIn("accept all", strip_ansi(footer))

    def test_select_zero_unresolved_includes_accept_all(self) -> None:
        # TODO: update after #6 — check line 0 of the 2-element footer list;
        # also assert that the 'a' key is highlighted (bold/colour around it).
        footer = build_footer("select", "", 0, None, set(), set(), 4)
        self.assertIn("accept all", strip_ansi(footer))

    # ── test 20 ───────────────────────────────────────────────────────────────

    def test_select_footer_contains_sel_buf(self) -> None:
        # TODO: update after #6 — sel_buf appears on line 1 (prompt line)
        # which starts with › in the new design.
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("select", "42", 0, None, collisions, invalid, 4)
        self.assertIn("42", strip_ansi(footer))

    # ── test 21 ───────────────────────────────────────────────────────────────

    def test_edit_error_text_appears_in_footer(self) -> None:
        collisions, invalid = self._collisions_invalid()
        err = '"BAD!" \u2014 must start with A\u2013Z'
        footer = build_footer("edit", "", 1, err, collisions, invalid, 4)
        self.assertIn("BAD!", strip_ansi(footer))

    def test_edit_error_uses_red_ansi_current_design(self) -> None:
        # TODO: update after #6 — error becomes an amber ⚠ badge on line 0;
        # NOT a \033[31;1m full-line colour wrap.  After #6:
        #   assertIn('⚠', strip_ansi(footer_lines[0]))
        #   assertNotIn('\033[31;1m', raw_line_0)  (no full-line red wrap)
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, "bad symbol", collisions, invalid, 4)
        self.assertIn("\033[31;1m", footer)  # current: whole footer wrapped red

    # ── test 22 ───────────────────────────────────────────────────────────────

    def test_edit_clean_contains_confirm_and_cancel(self) -> None:
        # TODO: update after #6 — these appear on line 0 of the 2-element list.
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, None, collisions, invalid, 4)
        clean = strip_ansi(footer)
        self.assertIn("confirm", clean)
        self.assertIn("cancel", clean)

    def test_edit_clean_contains_unresolved_count(self) -> None:
        collisions, invalid = self._collisions_invalid()
        footer = build_footer("edit", "", 1, None, collisions, invalid, 4)
        self.assertIn("unresolved", strip_ansi(footer))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Display cursor-movement tests  (no PTY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDisplay(unittest.TestCase):
    """Unit tests for Display.show() cursor-up rewrite behaviour."""

    _TABLE = ["top-border", "header", "separator", "row1", "row2"]
    _FOOTER = "[ row number to edit ]:"

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
        """N in \\033[NA must equal len(table_lines) for the current 1-line footer.

        TODO: update after #6 — footer becomes 2 lines, so the formula changes
        to len(table_lines) + len(footer_lines) - 1 = len(table_lines) + 1.
        The Display._prev_n accounting will be updated in task #6.
        """
        buf = io.StringIO()
        d = Display(output=buf)
        d.show(self._TABLE, self._FOOTER)
        buf.truncate(0); buf.seek(0)
        d.show(self._TABLE, self._FOOTER)
        m = re.search(r"\033\[(\d+)A", buf.getvalue())
        self.assertIsNotNone(m, "No cursor-up escape found on second render")
        n = int(m.group(1))  # type: ignore[union-attr]
        # Current design: _prev_n = len(table_lines); footer has no trailing \n.
        self.assertEqual(n, len(self._TABLE))

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
