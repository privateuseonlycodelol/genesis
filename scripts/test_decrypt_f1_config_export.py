#!/usr/bin/env python3
"""Tests for Technicolor-style config export parse/verify/decrypt."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from decrypt_f1_config_export import (  # noqa: E402
    build_envelope,
    decrypt,
    load_randb,
    parse_envelope,
    verify_hmac,
)

REFERENCE_EXPORT = (
    ROOT / "artifacts/ui/readonly-control-20261012T021317Z/response-10.private"
)
REFERENCE_SHA256 = "430de53785019e67b4391a8adf296f7d0424a37e0863aab8c6bf4fb38193bdd0"
SYNTHETIC_RANDB = bytes(range(64))


class ConfigExportTests(unittest.TestCase):
    def test_synthetic_roundtrip(self) -> None:
        header = [
            "PREAMBLE=THENC",
            "BACKUPVERSION=1.00",
            "BOARDMNEMONIC=TEST",
            "PRODUCTNAME=TST",
            "SERIALNUMBER=SN000000000",
            "MAC=00:11:22:33:44:55",
            "BUILDVERSION=0.0.0-test",
            "CIPHERKEY=GW",
            "SIGNATUREKEY=GW",
        ]
        plaintext = b"<config>\n  <item>value</item>\n</config>\n"
        iv = bytes(16)
        blob = build_envelope(header, SYNTHETIC_RANDB, plaintext, iv)
        envelope = parse_envelope(blob)
        self.assertTrue(verify_hmac(SYNTHETIC_RANDB, envelope))
        self.assertEqual(decrypt(SYNTHETIC_RANDB, envelope), plaintext)

    def test_wrong_key_fails_hmac(self) -> None:
        header = ["PREAMBLE=THENC", "CIPHERKEY=GW", "SIGNATUREKEY=GW"]
        blob = build_envelope(header, SYNTHETIC_RANDB, b"data", bytes(16))
        envelope = parse_envelope(blob)
        wrong = SYNTHETIC_RANDB[::-1]
        self.assertFalse(verify_hmac(wrong, envelope))

    def test_real_export_structure_if_present(self) -> None:
        if not REFERENCE_EXPORT.is_file():
            self.skipTest("reference export not available locally")
        data = REFERENCE_EXPORT.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), REFERENCE_SHA256)
        envelope = parse_envelope(data)
        self.assertEqual(envelope.cipher_key_label, "GW")
        self.assertEqual(envelope.signature_key_label, "GW")
        self.assertEqual(len(envelope.header_with_sep), 237)
        self.assertEqual(len(envelope.iv), 16)
        self.assertEqual(len(envelope.ciphertext) % 16, 0)
        self.assertEqual(len(envelope.signature), 20)

    def test_cli_verify_rejects_missing_randb(self) -> None:
        if not REFERENCE_EXPORT.is_file():
            self.skipTest("reference export not available locally")
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/decrypt_f1_config_export.py"),
                str(REFERENCE_EXPORT),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("randb_required", proc.stdout)


if __name__ == "__main__":
    unittest.main()
