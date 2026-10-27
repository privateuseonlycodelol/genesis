#!/usr/bin/env python3
"""Watch the router UART and press 'b' for you at the BOOT-P prompt.

Reads the serial port, appends everything to a log, and when a line contains
'Press b to enter BOOT-P' writes a single 'b' before the boot continues. Once per
boot: the flag resets when a new 'U-Boot SPL' line appears. Nothing else is sent.

Only one process may own the serial port. Quit any Screen session on it first
(in that Screen window: Ctrl+A, then K, then Y). Do not type Ctrl+C into the
router console: it interrupts Linux services and can trigger a watchdog reboot.

Usage (from repo root, in Terminal):
  python3 scripts/f1_bootp_autob.py --log ~/Desktop/router-boot-autob.log
  python3 scripts/f1_bootp_autob.py --help
"""
from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import time

PROMPT = "Press b to enter BOOT-P"
BOOT_START = "U-Boot SPL"


def configure_serial(fd: int, baud: int = 115200) -> None:
    speed = getattr(termios, f"B{baud}")
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0  # iflag
    attrs[1] = 0  # oflag
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag
    attrs[3] = 0  # lflag
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


class BootPTrigger:
    """Decides when to send 'b'. Sends at most once per boot, triggering immediately on prompt."""

    def __init__(self) -> None:
        self.buffer = ""
        self.answered = False
        self.sent_count = 0

    def feed(self, chunk: str) -> bool:
        self.buffer += chunk
        if BOOT_START in self.buffer:
            self.answered = False
            idx = self.buffer.rfind(BOOT_START)
            self.buffer = self.buffer[idx:]
        if PROMPT in self.buffer and not self.answered:
            self.answered = True
            self.sent_count += 1
            return True
        if len(self.buffer) > 4096:
            self.buffer = self.buffer[-2048:]
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", default="/dev/cu.usbserial-0001")
    parser.add_argument("--log", required=True, help="file to append the raw UART stream to")
    parser.add_argument("--minutes", type=float, default=10.0, help="stop after this many minutes")
    args = parser.parse_args()

    if not os.path.exists(args.device):
        print(f"serial device not found: {args.device}", file=sys.stderr)
        return 1

    fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY)
    configure_serial(fd)
    trigger = BootPTrigger()
    partial = ""
    deadline = time.time() + args.minutes * 60
    print(f"watching {args.device} for {args.minutes:g} min; log: {args.log}", flush=True)

    with open(args.log, "ab") as log:
        while time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], 1.0)
            if not ready:
                continue
            data = os.read(fd, 4096)
            if not data:
                break
            log.write(data)
            log.flush()
            chunk = data.decode("utf-8", "replace").replace("\r", "")
            if trigger.feed(chunk):
                os.write(fd, b"b")
                stamp = time.strftime("%H:%M:%S")
                note = f"[{stamp}] sent 'b' at BOOT-P prompt (#{trigger.sent_count})\n"
                log.write(note.encode())
                log.flush()
                print(note.strip(), flush=True)

    os.close(fd)
    print(f"stopped; 'b' sent {trigger.sent_count} time(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
