#!/usr/bin/env python3
"""
resize_demo.py — Watch the TUI table reflow as the terminal height changes.

Runs the TUI inside a pty, steps through a sequence of heights via
TIOCSWINSZ + SIGWINCH, captures each rendered frame, and prints them
to stdout with a pause between steps.  No mouse or keyboard needed.

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

HEIGHTS: list[int] = [8, 14, 24, 35]   # terminal heights to step through
WIDTH:   int       = 100               # fixed column width for all frames
PAUSE:   float     = 1.5              # seconds to hold each frame


# ─── Helpers ──────────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\033\[[^a-zA-Z]*[a-zA-Z]")


def _set_winsize(fd: int, h: int, w: int) -> None:
    """Apply TIOCSWINSZ to *fd* (sets window size; on master also sends SIGWINCH)."""
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", h, w, 0, 0))


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text).replace("\r", "")


def _last_frame(text: str) -> str:
    """Return the last fully-rendered table frame (everything after the last header)."""
    clean  = _strip_ansi(text)
    marker = "cmdty:id"
    idx    = clean.rfind(marker)
    return clean[idx:] if idx != -1 else clean


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    rows   = make_rows(LARGE_FIXTURE)
    n      = len(rows)

    master, slave = pty.openpty()
    slave_out = os.fdopen(os.dup(slave), "w", buffering=1, closefd=True)

    # Set the initial window size before run() reads it.
    _set_winsize(master, HEIGHTS[0], WIDTH)

    chunks:     list[bytes]                    = []
    drain_stop: threading.Event                = threading.Event()

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
        for h in HEIGHTS:
            # Resize the pty slave window and deliver SIGWINCH to this process.
            # run() is on the main thread so its SIGWINCH handler fires and
            # calls refresh() before os.read() retries.
            _set_winsize(master, h, WIDTH)
            os.kill(os.getpid(), signal.SIGWINCH)
            time.sleep(PAUSE)

            # Capture and print the latest frame (ANSI stripped for legibility).
            text  = b"".join(chunks).decode("utf-8", errors="replace")
            frame = _last_frame(text).strip()
            vp    = min(max(3, h - 6), n)
            sep   = "─" * 70
            print(f"\n{sep}")
            print(f"  Terminal height : {h:3d} rows")
            print(f"  Viewport        : {vp:3d} data rows  (min 3, clamped to {n})")
            print(sep)
            print(frame)

        # Exit the TUI after the last frame has been displayed.
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
    # (which calls signal.signal()) is installed correctly.
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
