#!/usr/bin/env python3
"""Small macOS stdlib UART logger; direct PTY use avoids Screen/cu PTY errors."""
import os
import select
import signal
import sys
import termios
import tty


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


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: f1-uart-capture.py SERIAL_DEVICE LOG_FILE", file=sys.stderr)
        return 2
    device, logfile = sys.argv[1:]
    serial_fd = os.open(device, os.O_RDWR | os.O_NOCTTY)
    old_stdin = termios.tcgetattr(sys.stdin.fileno())
    try:
        configure_serial(serial_fd)
        tty.setcbreak(sys.stdin.fileno())
        with open(logfile, "ab", buffering=0) as log:
            print("UART connected at 115200 baud. Boot the router now; Ctrl+C exits.", flush=True)
            while True:
                readable, _, _ = select.select([serial_fd, sys.stdin.fileno()], [], [])
                if serial_fd in readable:
                    data = os.read(serial_fd, 4096)
                    if data:
                        log.write(data)
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                if sys.stdin.fileno() in readable:
                    key = os.read(sys.stdin.fileno(), 1)
                    if key == b"\x03":  # Ctrl+C
                        return 0
                    if key:
                        os.write(serial_fd, b"\r" if key == b"\n" else key)
    except KeyboardInterrupt:
        return 0
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_stdin)
        os.close(serial_fd)


if __name__ == "__main__":
    raise SystemExit(main())
