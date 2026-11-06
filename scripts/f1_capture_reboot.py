#!/usr/bin/env python3
"""Capture UART output while triggering a clean software reboot of Telia F1.

Logs all U-Boot, kernel, init, mount_root, and userspace messages during reboot
to verify whether rootfs_data (volume 20) mounts and how the overlay behaves.
"""
from __future__ import annotations

import argparse
import os
import select
import subprocess
import sys
import termios
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def capture_uart(device: str, log_file: Path, stop_event: threading.Event):
    try:
        fd = os.open(device, os.O_RDWR | os.O_NOCTTY)
        attrs = termios.tcgetattr(fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = termios.B115200
        attrs[5] = termios.B115200
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 5
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except Exception as e:
        print(f"[UART] Failed to open {device}: {e}", file=sys.stderr)
        return

    print(f"[UART] Logging {device} -> {log_file}")
    with open(log_file, "wb") as f:
        while not stop_event.is_set():
            rlist, _, _ = select.select([fd], [], [], 0.5)
            if rlist:
                try:
                    data = os.read(fd, 4096)
                    if not data:
                        break
                    f.write(data)
                    f.flush()
                    # Also write to stdout unbuffered
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
                except OSError:
                    break

    try:
        os.close(fd)
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/cu.usbserial-0001", help="Serial device")
    parser.add_argument("--base", default="http://192.168.1.1", help="Router base URL")
    parser.add_argument("--duration", type=int, default=120, help="Capture duration in seconds")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "artifacts" / "uart" / time.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / f"router-reboot-{stamp}.log"

    stop_event = threading.Event()
    t = threading.Thread(target=capture_uart, args=(args.device, log_file, stop_event))
    t.daemon = True
    t.start()

    time.sleep(2)
    print("\n[*] Triggering router restart via scripts/f1_restart_router.py...")
    cmd = [sys.executable, str(ROOT / "scripts" / "f1_restart_router.py"), "--base", args.base, "--yes"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"[*] Restart trigger returned {res.returncode}:")
    print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip(), file=sys.stderr)

    print(f"[*] Waiting {args.duration}s for boot sequence to complete...")
    start_time = time.time()
    try:
        while time.time() - start_time < args.duration:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user.")

    stop_event.set()
    t.join(timeout=3)
    print(f"\n[*] Capture complete. Saved to: {log_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
