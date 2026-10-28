#!/usr/bin/env python3
"""Test whether one CR releases the SPL menu that `a` opens at boot.

Phase 1: send `a` every 0.1 s until the menu line `Use enter to confirm` appears.
Phase 2: stop sending `a`, send one CR, then log everything for a fixed time.
Only `a` and CR are ever sent. Never b or B. Writes nothing to flash.

Usage: f1_menu_release_test.py SERIAL_DEVICE LOG_FILE [--timeout SECONDS] [--after SECONDS]
       [--choice KEYS]   keys sent after the menu, default one CR (e.g. --choice 1)
"""
import argparse
import os
import select
import time

from f1_uart_interrupt_probe import configure_serial, is_allowed

MENU_LINE = b"Use enter to confirm"
SEND_A = b"a"
SEND_CR = b"\r"


ALLOWED_TEST_KEYS = frozenset({b"a", b"1", b"r", b" ", b"\r"})


def parse_choice(text: str) -> tuple[bytes, ...]:
    keys = tuple(char.encode("ascii") for char in text)
    refused = [key for key in keys if key not in ALLOWED_TEST_KEYS]
    if refused:
        raise ValueError(f"refused key(s): {refused}")
    return keys


def run(device: str, logfile: str, timeout: float, after: float, choice: tuple[bytes, ...]) -> int:
    assert is_allowed(SEND_A) and is_allowed(SEND_CR)
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY)
    received = b""
    try:
        configure_serial(fd)
        with open(logfile, "ab", buffering=0) as log:
            log.write(f"# release test start {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode())
            start = time.monotonic()
            next_a = start
            menu_at = None
            while time.monotonic() - start < timeout:
                readable, _, _ = select.select([fd], [], [], 0.02)
                if readable:
                    data = os.read(fd, 4096)
                    received += data
                    log.write(data)
                    if menu_at is None and MENU_LINE in received:
                        menu_at = time.monotonic()
                        log.write(b"\n# phase 2: menu seen, stop a, send one CR\n")
                        for key in choice:
                            os.write(fd, key)
                            log.write(f"# sent {key!r} (after menu)\n".encode())
                            time.sleep(0.2)
                if menu_at is None and time.monotonic() >= next_a:
                    os.write(fd, SEND_A)
                    log.write(b"# sent b'a'\n")
                    next_a = time.monotonic() + 0.1
                if menu_at is not None and time.monotonic() - menu_at >= after:
                    log.write(b"\n# stop: post-CR window elapsed\n")
                    return 0
            log.write(b"\n# stop: timeout\n")
            return 1
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("device")
    parser.add_argument("logfile")
    parser.add_argument("--timeout", type=float, default=150.0)
    parser.add_argument("--after", type=float, default=90.0)
    parser.add_argument("--choice", default="\r", help="Keys after the menu. Allowed: a, r, 1, space, CR. Recovery is 'r 1'.")
    args = parser.parse_args()
    return run(args.device, args.logfile, args.timeout, args.after, parse_choice(args.choice))


if __name__ == "__main__":
    raise SystemExit(main())
