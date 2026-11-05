#!/usr/bin/env python3
"""Automated post-exploit triage fetcher and key extraction tool for Telia F1 / GCNT-X.

Connects to the rooted router over LAN (telnet on port 23), downloads the automated
triage bundle (/tmp/f1-triage.tar.gz), extracts hardware keys from /proc/rip/ (such as
Item 0x0108: RIP_ID_RANDOM_KEY_B), and decrypts stored configuration exports offline.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import socket
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

DEFAULT_ROUTER_IP = "192.168.1.1"
DEFAULT_TELNET_PORT = 23
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "triage"


def fetch_remote_file_base64(
    sock: socket.socket, remote_path: str, timeout: float = 30.0
) -> bytes:
    """Retrieve a remote file over an active shell session using base64 encoding."""
    # Drain any initial banners / prompts
    sock.settimeout(2.0)
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
    except socket.timeout:
        pass

    # Send base64 dump command with start and end sentinels
    sentinel_start = "===B64_START==="
    sentinel_end = "===B64_END==="
    cmd = (
        f"echo {sentinel_start} && base64 {remote_path} 2>/dev/null && echo {sentinel_end}\n"
    )
    sock.sendall(cmd.encode("ascii"))

    sock.settimeout(timeout)
    buf = bytearray()
    started = False
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            text = buf.decode("latin-1")
            if sentinel_end in text:
                break
        except socket.timeout:
            break

    full_text = buf.decode("latin-1")
    if sentinel_start not in full_text or sentinel_end not in full_text:
        raise RuntimeError(
            f"Failed to receive complete base64 payload for {remote_path}"
        )

    b64_data = full_text.split(sentinel_start)[1].split(sentinel_end)[0].strip()
    # Remove any whitespace or CR/LF introduced by terminal
    b64_clean = re.sub(r"\s+", "", b64_data)
    return base64.b64decode(b64_clean)


def extract_triage_bundle(
    tar_bytes: bytes, output_dir: Path
) -> dict[str, Path]:
    """Extract triage tarball and return dict of harvested artifact paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tar_path = output_dir / "f1-triage.tar.gz"
    tar_path.write_bytes(tar_bytes)

    with tarfile.open(fileobj=tarfile.io.BytesIO(tar_bytes), mode="r:gz") as tar:
        tar.extractall(path=output_dir)

    harvested: dict[str, Path] = {"tarball": tar_path}
    for root, _, files in os.walk(output_dir):
        for f in files:
            p = Path(root) / f
            harvested[p.name] = p

    return harvested


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch automated triage bundle and extract keys from Telia F1"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=DEFAULT_ROUTER_IP,
        help="Router IP address (default: 192.168.1.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_TELNET_PORT,
        help="Telnet port (default: 23)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Local directory to store triage artifacts",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Connection and download timeout in seconds",
    )

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_dir = args.out_dir / f"session-{timestamp}"

    print(f"[*] Connecting to router telnet at {args.ip}:{args.port}...")
    try:
        s = socket.create_connection((args.ip, args.port), timeout=10.0)
    except Exception as e:
        print(f"[-] Connection failed: {e}", file=sys.stderr)
        return 1

    try:
        print("[*] Waiting for /tmp/f1-triage.tar.gz to be ready...")
        time.sleep(3.0)  # Give triage script a moment to write tarball
        tar_bytes = fetch_remote_file_base64(
            s, "/tmp/f1-triage.tar.gz", timeout=args.timeout
        )
        print(f"[+] Downloaded {len(tar_bytes):,} bytes of triage archive.")

        harvested = extract_triage_bundle(tar_bytes, target_dir)
        print(f"[+] Extracted artifacts to {target_dir}")

        # Check for Item 0x0108 (RIP_ID_RANDOM_KEY_B)
        key_b_file = target_dir / "triage" / "rip" / "0108"
        if key_b_file.is_file():
            key_data = key_b_file.read_bytes()
            print(f"[+] FOUND Item 0x0108 (RANDOM_KEY_B): {len(key_data)} bytes")
            print(f"    Hex: {key_data.hex()}")

        # Check for Item 0x011a (CLIENT_CERTIFICATE)
        cert_file = target_dir / "triage" / "rip" / "011a"
        if cert_file.is_file():
            print(f"[+] FOUND Item 0x011a (CLIENT_CERTIFICATE): {cert_file.stat().st_size} bytes")

        # Check for Item 0x0120 (OSIK)
        osik_file = target_dir / "triage" / "rip" / "0120"
        if osik_file.is_file():
            print(f"[+] FOUND Item 0x0120 (OSIK): {osik_file.stat().st_size} bytes")

        return 0
    except Exception as e:
        print(f"[-] Error during triage fetch: {e}", file=sys.stderr)
        return 1
    finally:
        s.close()


if __name__ == "__main__":
    sys.exit(main())
