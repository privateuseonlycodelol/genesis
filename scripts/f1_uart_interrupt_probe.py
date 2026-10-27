#!/usr/bin/env python3
"""Timed UART probe for a boot-time key or interrupt window on the F1.

Sends candidate keys while the router boots and logs every received byte, with a
sent-marker per key. Never sends b or B, which enter BOOT-P. Stops at the first
console, login, or Linux console marker, or at the timeout. Writes nothing to flash.

Default mode rotates through KEY_CYCLE, one key every 0.5 s. --keys a --interval 0.1
repeats one key quickly, to approximate holding it down at power-on.

Usage: f1_uart_interrupt_probe.py SERIAL_DEVICE LOG_FILE [--timeout SECONDS]
       [--keys KEYS] [--interval SECONDS]
"""
import argparse
import os
import select
import termios
import time

# Default rotation. Space and Ctrl+C were tested earlier with no interrupt.
KEY_CYCLE = (b"\r", b"\n", b"\x1b", b"\t", b"\x01", b"\x7f")
# Keys a caller may pass with --keys. b and B are excluded on purpose.
ALLOWED_KEYS = frozenset(KEY_CYCLE + (b"a", b" ", b"\x03"))
FORBIDDEN_SEND = frozenset({b"b", b"B"})
DEFAULT_INTERVAL = 0.5
STOP_MARKERS = (b"=>", b"U-Boot>", b"login:", b"activate this console", b"mount_root:")


def is_allowed(byte: bytes) -> bool:
    """True only for keys in ALLOWED_KEYS, and never for b or B."""
    return byte in ALLOWED_KEYS and byte not in FORBIDDEN_SEND


def parse_keys(text: str) -> tuple[bytes, ...]:
    """Turns a --keys string such as 'a' or 'a\\t' into single-byte keys, rejecting b and B."""
    keys = tuple(char.encode("ascii") for char in text)
    refused = [key for key in keys if not is_allowed(key)]
    if refused:
        raise ValueError(f"refused key(s): {refused}")
    return keys


def should_stop(received: bytes) -> bool:
    """True when the received stream shows a console, login, or Linux console marker."""
    return any(marker in received for marker in STOP_MARKERS)


def configure_serial(fd: int, baud: int = 115200) -> None:
    speed = getattr(termios, f"B{baud}")
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def run(device: str, logfile: str, timeout: float, keys: tuple[bytes, ...], interval: float) -> int:
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY)
    received = b""
    start = time.monotonic()
    key_index = 0
    try:
        configure_serial(fd)
        with open(logfile, "ab", buffering=0) as log:
            log.write(f"# probe start {time.strftime('%Y-%m-%d %H:%M:%S')} keys={keys!r} interval={interval}\n".encode())
            next_send = start
            while time.monotonic() - start < timeout:
                readable, _, _ = select.select([fd], [], [], 0.02)
                if readable:
                    data = os.read(fd, 4096)
                    received += data
                    log.write(data)
                    if should_stop(received[-512:]):
                        log.write(b"\n# stop: console, login, or Linux marker seen\n")
                        return 0
                if time.monotonic() >= next_send:
                    key = keys[key_index % len(keys)]
                    key_index += 1
                    if is_allowed(key):
                        os.write(fd, key)
                        log.write(f"# sent {key!r}\n".encode())
                    next_send = time.monotonic() + interval
            log.write(b"\n# stop: timeout\n")
            return 1
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("device")
    parser.add_argument("logfile")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--keys", default=None, help="Keys to send, e.g. 'a'. Default: built-in rotation.")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Seconds between keys.")
    args = parser.parse_args()
    keys = parse_keys(args.keys) if args.keys else KEY_CYCLE
    return run(args.device, args.logfile, args.timeout, keys, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
