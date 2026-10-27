#!/usr/bin/env python3
"""Tests for xts_plain64_squashfs_scan.py.

Run with a Python that has `cryptography` installed:
    python3 scripts/test_xts_plain64_squashfs_scan.py
"""

import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xts_plain64_squashfs_scan as scanner  # noqa: E402
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: E402

MKSQUASHFS = shutil.which("mksquashfs") or "/opt/homebrew/bin/mksquashfs"


def encrypt_plain64(key, data):
    """Encrypt whole 512-byte sectors, tweak = sector index (little-endian)."""
    out = bytearray()
    for index in range(len(data) // scanner.SECTOR):
        sector = data[index * scanner.SECTOR:(index + 1) * scanner.SECTOR]
        tweak = index.to_bytes(16, "little")
        encryptor = Cipher(algorithms.AES(key), modes.XTS(tweak)).encryptor()
        out += encryptor.update(sector) + encryptor.finalize()
    return bytes(out)


class ReadKeyTest(unittest.TestCase):
    def test_key_read_from_numbered_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "log.txt")
            key_hex = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
            with open(log, "w") as handle:
                handle.write("first line\n")
                handle.write(key_hex + "ERROR:trailing text\n")
            self.assertEqual(scanner.read_key_from_log(log, 2).hex(), key_hex)

    def test_line_without_64_hex_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "log.txt")
            with open(log, "w") as handle:
                handle.write("short 00ff\n")
            with self.assertRaises(ValueError):
                scanner.read_key_from_log(log, 1)


@unittest.skipUnless(os.path.exists(MKSQUASHFS), "mksquashfs not installed")
class ScanControlTest(unittest.TestCase):
    """Positive and negative controls built from a real squashfs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        src = os.path.join(self.tmp.name, "src")
        os.makedirs(os.path.join(src, "etc"))
        with open(os.path.join(src, "etc", "motd"), "w") as handle:
            handle.write("control\n")
        self.squashfs = os.path.join(self.tmp.name, "rootfs.squashfs")
        subprocess.run(
            [MKSQUASHFS, src, self.squashfs, "-comp", "gzip", "-all-root", "-noappend", "-no-progress"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        with open(self.squashfs, "rb") as handle:
            self.squashfs_bytes = handle.read()
        self.key = bytes(range(32))

    def tearDown(self):
        self.tmp.cleanup()

    def _embed(self, encrypted, offset, total):
        rng = random.Random(1)
        blob = bytearray(rng.getrandbits(8) for _ in range(total))
        blob[offset:offset + len(encrypted)] = encrypted
        return bytes(blob)

    def test_positive_control_finds_embedded_encrypted_squashfs(self):
        offset = 8 * scanner.SECTOR
        pad = (-len(self.squashfs_bytes)) % scanner.SECTOR
        encrypted = encrypt_plain64(self.key, self.squashfs_bytes + bytes(pad))
        image = self._embed(encrypted, offset, 64 * 1024)
        self.assertEqual(scanner.scan(image, self.key), [offset])

    def test_negative_control_wrong_key_finds_nothing(self):
        offset = 8 * scanner.SECTOR
        pad = (-len(self.squashfs_bytes)) % scanner.SECTOR
        encrypted = encrypt_plain64(self.key, self.squashfs_bytes + bytes(pad))
        image = self._embed(encrypted, offset, 64 * 1024)
        wrong = bytes(reversed(self.key))
        self.assertEqual(scanner.scan(image, wrong), [])

    def test_negative_control_no_squashfs_finds_nothing(self):
        image = self._embed(b"", 0, 64 * 1024)
        self.assertEqual(scanner.scan(image, self.key), [])


if __name__ == "__main__":
    unittest.main()
