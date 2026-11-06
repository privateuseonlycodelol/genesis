#!/usr/bin/env python3
"""Observe serial console output during a warm router reboot.

Opens /dev/cu.usbserial-0001, initiates a graceful reboot via f1_restart_router.py,
and logs all serial traffic during the reboot cycle to analyze mount_root behavior
on a non-upgrade boot.
"""

import argparse
import os
import select
import subprocess
import sys
import termios
import time
from pathlib import Path


def set_serial_115200(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch serial output during warm reboot")
    parser.add_argument("--uart", default="/dev/cu.usbserial-0001", help="Serial device path")
    parser.add_argument("--timeout", type=int, default=120, help="Observation duration in seconds")
    parser.add_argument("--router-url", default="http://192.168.1.1", help="Router base URL")
    parser.add_argument("--no-reboot", action="store_true", help="Only observe without triggering reboot")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path("artifacts/uart") / f"warm-reboot-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "console.log"

    print(f"[*] Opening serial console on {args.uart}...")
    try:
        fd = os.open(args.uart, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        set_serial_115200(fd)
    except Exception as e:
        print(f"[-] Failed to open serial port {args.uart}: {e}")
        return 1

    if not args.no_reboot:
        print(f"[*] Triggering graceful reboot via {args.router_url}...")
        reboot_script = Path(__file__).resolve().parent / "f1_restart_router.py"
        res = subprocess.run(
            [sys.executable, str(reboot_script), "--base", args.router_url, "--yes"],
            capture_output=True,
            text=True,
        )
        print(f"[*] Reboot response: {res.stdout.strip()}")
        if res.stderr.strip():
            print(f"[!] Reboot stderr: {res.stderr.strip()}")

    print(f"[*] Observing console for {args.timeout}s, writing to {log_file}...")
    start_time = time.time()
    with open(log_file, "wb") as log:
        while time.time() - start_time < args.timeout:
            r, _, _ = select.select([fd], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(fd, 4096)
                    if chunk:
                        log.write(chunk)
                        log.flush()
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                except BlockingIOError:
                    pass
                except Exception as e:
                    print(f"\n[-] Error reading UART: {e}", file=sys.stderr)
                    break

    os.close(fd)
    print(f"\n[*] Observation complete. Log saved to {log_file} ({log_file.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
