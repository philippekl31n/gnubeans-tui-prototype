#!/usr/bin/env python3
"""
resize_demo.py — Watch the TUI table reflow as the terminal height changes.

Runs the TUI inside a pty, steps through a sequence of heights via
TIOCSWINSZ + SIGWINCH, captures each rendered frame, and prints it to
stdout (ANSI stripped) with a clear header.  No mouse or keyboard needed.

Usage:
    python3 resize_demo.py
"""
from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import threading
import time

import tui_prototype
from tui_prototype import LARGE_FIXTURE, make_rows


# ─── Configuration ────────────────────────────────────────────────────────────

HEIGHTS:   list[int] = [8, 14, 24, 35]   # terminal heights to step through
WIDTH:     int       = 100               # fixed column width for all frames
STEP_WAIT: float     = 1.5              # seconds to wait after each SIGWINCH


# ─── Helpers ──────────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\033\[[^a-zA-Z]*[a-zA-Z]")


def _set_winsize(fd: int, h: int, w: int) -> None:
    """Apply TIOCSWINSZ to *fd* to set the pty window size."""
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", h, w, 0, 0))


def _strip(text: str) -> str:
    """Strip all ANSI escape sequences and bare carriage returns."""
    return _ANSI_RE.sub("", text).replace("\r", "")


def _extract_frame(text: str) -> str:
    """Return the last complete table frame from *text* (header onward)."""
    marker = "cmdty:id"
    idx = text.rfind(marker)
    return text[idx:].strip() if idx != -1 else text.strip()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    rows = make_rows(LARGE_FIXTURE)
    n    = len(rows)

    master, slave = pty.openpty()
    slave_out = os.fdopen(os.dup(slave), "w", buffering=1, closefd=True)

    # Apply the initial window size *before* run() reads os.get_terminal_size().
    _set_winsize(master, HEIGHTS[0], WIDTH)

    chunks:    list[bytes] = []
    drain_stop = threading.Event()

    def _drainer() -> None:
        while not drain_stop.is_set():
            r, _, _ = select.select([master], [], [], 0.05)
            if r:
                try:
                    chunks.append(os.read(master, 4096))
                except OSError:
                    break

    def _controller() -> None:
        time.sleep(0.4)   # wait for the initial frame to render

        # Track the byte offset at the START of each step so we extract
        # only the bytes written AFTER the SIGWINCH for that height.
        prev_offset = sum(len(c) for c in chunks)

        for h in HEIGHTS:
            # Resize the pty window.
            _set_winsize(master, h, WIDTH)

            # Send SIGWINCH to set the pending-signal flag (may land on any
            # thread since os.kill targets the process, not a specific thread).
            os.kill(os.getpid(), signal.SIGWINCH)

            # Write a harmless null byte so os.read(slave,1) returns on the
            # main thread regardless of which thread received SIGWINCH.
            # Python checks pending signals as soon as os.read() returns and
            # reacquires the GIL, so _handle_sigwinch fires and viewport_h
            # is updated before read_key() yields the null byte to the loop.
            time.sleep(0.02)   # brief gap: let SIGWINCH arrive first
            os.write(master, b"\x00")

            # Give the handler + refresh() time to execute and the drainer
            # time to read all new bytes before we snapshot.
            time.sleep(STEP_WAIT)

            # Snapshot only the bytes written since the previous step.
            all_raw     = b"".join(chunks)
            step_raw    = all_raw[prev_offset:]
            prev_offset = len(all_raw)

            step_text = _strip(step_raw.decode("utf-8", errors="replace"))
            frame     = _extract_frame(step_text)

            # Fallback: if the step slice didn't contain a table header
            # (e.g. the drainer raced ahead of us), scan the full stream.
            if not frame:
                full_text = _strip(all_raw.decode("utf-8", errors="replace"))
                frame     = _extract_frame(full_text)

            vp  = min(max(3, h - 6), n)
            sep = "─" * 70
            print(f"\n{sep}")
            print(f"  Terminal height : {h:3d} rows")
            print(f"  Viewport        : {vp:3d} data rows  (min 3, clamped to {n})")
            print(sep)
            print(frame if frame else "(no table output captured)")

        # Exit the TUI after all frames have been printed.
        time.sleep(0.2)
        try:
            os.write(master, b"\x03")   # Ctrl+C → run() returns "cancelled"
        except OSError:
            pass

    dt = threading.Thread(target=_drainer,    daemon=True)
    ct = threading.Thread(target=_controller, daemon=True)
    dt.start()
    ct.start()

    # run() MUST be called from the main thread so that its SIGWINCH handler
    # (which calls signal.signal()) is installed and active during the demo.
    tui_prototype.run(rows, stdin_fd=slave, output=slave_out)

    ct.join(timeout=3.0)
    try:
        slave_out.close()
    except OSError:
        pass
    time.sleep(0.2)
    drain_stop.set()
    dt.join(timeout=1.0)
    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
