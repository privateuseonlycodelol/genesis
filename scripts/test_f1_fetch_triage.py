#!/usr/bin/env python3
"""Unit tests for scripts/f1_fetch_triage.py."""

from __future__ import annotations

import base64
import io
import socket
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.f1_fetch_triage import (
    extract_triage_bundle,
    fetch_remote_file_base64,
)


class MockSocket:
    def __init__(self, responses: list[bytes]):
        self.responses = list(responses)
        self.sent = bytearray()
        self.timeout = None

    def settimeout(self, t):
        self.timeout = t

    def sendall(self, data: bytes):
        self.sent.extend(data)

    def recv(self, bufsize: int) -> bytes:
        if self.responses:
            return self.responses.pop(0)
        return b""

    def close(self):
        pass


class TestF1FetchTriage(unittest.TestCase):
    def test_extract_triage_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)

            # Create synthetic tar.gz in memory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
                # Add a dummy 0108 file
                info = tarfile.TarInfo(name="triage/rip/0108")
                dummy_key = b"\xaa" * 64
                info.size = len(dummy_key)
                tar.addfile(info, io.BytesIO(dummy_key))

                # Add a dummy uname
                info_uname = tarfile.TarInfo(name="triage/uname.txt")
                dummy_uname = b"Linux TeliaF1 4.19.235 aarch64\n"
                info_uname.size = len(dummy_uname)
                tar.addfile(info_uname, io.BytesIO(dummy_uname))

            tar_bytes = tar_stream.getvalue()
            harvested = extract_triage_bundle(tar_bytes, out_dir)

            self.assertIn("tarball", harvested)
            self.assertIn("0108", harvested)
            self.assertIn("uname.txt", harvested)

            extracted_key = (out_dir / "triage" / "rip" / "0108").read_bytes()
            self.assertEqual(extracted_key, b"\xaa" * 64)

    def test_fetch_remote_file_base64(self):
        raw_payload = b"TEST-ROUTER-TRIAGE-ARCHIVE-PAYLOAD"
        b64_encoded = base64.b64encode(raw_payload).decode("ascii")

        mock_stream = (
            b"sh-4.4# "
            + b"===B64_START===\r\n"
            + b64_encoded.encode("ascii")
            + b"\r\n===B64_END===\r\nsh-4.4# "
        )

        # First item is drained as initial prompt, second item is returned after command
        mock_sock = MockSocket([b"", mock_stream])
        result = fetch_remote_file_base64(mock_sock, "/tmp/f1-triage.tar.gz")
        self.assertEqual(result, raw_payload)


if __name__ == "__main__":
    unittest.main()
