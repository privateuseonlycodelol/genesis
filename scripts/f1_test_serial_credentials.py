#!/usr/bin/env python3
"""Test UART serial console credential and username acceptance for Telia F1 / GCNT-X.

Systematically tests whether sending non-root usernames (e.g. admin, engineer, root,
or specific sequences) to the UART console alters restricted_shell's authentication
state or username parameter before falling back to default root access control.

Pure Python, captures exact raw bytes and echoes on UART.
"""
from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def open_uart(device: str) -> int:
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    # Raw mode
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def drain_uart(fd: int, timeout: float = 0.5) -> bytes:
    buf = bytearray()
    while True:
        rlist, _, _ = select.select([fd], [], [], timeout)
        if not rlist:
            break
        try:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf.extend(chunk)
        except OSError:
            break
    return bytes(buf)


def send_and_capture(fd: int, data: bytes, wait_after: float = 2.0) -> bytes:
    # First write data
    os.write(fd, data)
    # Then capture response
    captured = bytearray()
    deadline = time.time() + wait_after
    while time.time() < deadline:
        remaining = max(0.05, deadline - time.time())
        rlist, _, _ = select.select([fd], [], [], remaining)
        if rlist:
            try:
                chunk = os.read(fd, 4096)
                if chunk:
                    captured.extend(chunk)
            except OSError:
                break
    return bytes(captured)


def run_tests(device: str, out_dir: Path) -> dict[str, bytes]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fd = open_uart(device)
    results = {}
    try:
        print(f"[*] Draining initial UART buffer on {device}...")
        initial = drain_uart(fd, timeout=1.0)
        if initial:
            print(f"    Initial buffer ({len(initial)} B): {initial!r}")
            (out_dir / "00_initial.bin").write_bytes(initial)

        probes = [
            ("01_newline", b"\n"),
            ("02_admin_newline", b"admin\n"),
            ("03_engineer_newline", b"engineer\n"),
            ("04_root_newline", b"root\n"),
            ("05_login_admin_newline", b"login admin\n"),
            ("06_newline_then_admin", b"\nadmin\n"),
            ("07_newline_then_engineer", b"\nengineer\n"),
            ("08_crlf", b"\r\n"),
            ("09_admin_crlf", b"admin\r\n"),
        ]

        for label, payload in probes:
            print(f"[*] Sending probe {label}: {payload!r}...")
            resp = send_and_capture(fd, payload, wait_after=2.0)
            results[label] = resp
            (out_dir / f"{label}.bin").write_bytes(resp)
            print(f"    Received ({len(resp)} B): {resp!r}")
            time.sleep(1.0)

    finally:
        os.close(fd)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/cu.usbserial-0001", help="Serial port")
    parser.add_argument("--out-name", default="uart-credentials-probe", help="Output directory name")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "artifacts" / "uart" / f"{args.out_name}-{stamp}"
    print(f"[*] Starting UART credential tests on {args.device}...")
    results = run_tests(args.device, out_dir)
    print(f"[+] All probes completed. Results saved to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
