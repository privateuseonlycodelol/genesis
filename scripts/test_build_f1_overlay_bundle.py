#!/usr/bin/env python3
"""Unit tests for build_f1_overlay_bundle.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_f1_overlay_bundle import (
    DEFAULT_MKFS_UBIFS,
    build_overlay_bundle,
)
from validate_f1_fit_bundle import validate_bundle


class TestBuildF1OverlayBundle(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_overlay_bundle_creates_valid_artifacts(self):
        if not DEFAULT_MKFS_UBIFS.is_file():
            self.skipTest("tools/bin/mkfs.ubifs binary not present")

        staging = self.temp_path / "staging"
        out_ubifs = self.temp_path / "test.ubifs"
        out_fit = self.temp_path / "test.itb"

        res_ubifs, res_fit, sha_ubifs, sha_fit = build_overlay_bundle(
            staging_dir=staging,
            mkfs_ubifs_bin=DEFAULT_MKFS_UBIFS,
            out_ubifs=out_ubifs,
            out_fit=out_fit,
            root_password="",
            description="Test injection bundle",
            skip_staging=False,
        )

        self.assertEqual(res_ubifs, out_ubifs)
        self.assertEqual(res_fit, out_fit)
        self.assertTrue(out_ubifs.is_file())
        self.assertTrue(out_fit.is_file())

        # Check UBIFS node magic
        ubifs_bytes = out_ubifs.read_bytes()
        self.assertEqual(ubifs_bytes[:4], b"\x31\x18\x10\x06")

        # Check FIT FDT magic
        fit_bytes = out_fit.read_bytes()
        self.assertEqual(fit_bytes[:4], b"\xd0\x0d\xfe\xed")

        # Validate bundle contract
        report = validate_bundle(fit_bytes)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])
        self.assertTrue(
            any("valid overlay volume format" in i for i in report.info)
        )

    def test_missing_mkfs_binary_raises_file_not_found(self):
        staging = self.temp_path / "staging"
        out_ubifs = self.temp_path / "test.ubifs"
        out_fit = self.temp_path / "test.itb"

        with self.assertRaises(FileNotFoundError):
            build_overlay_bundle(
                staging_dir=staging,
                mkfs_ubifs_bin=self.temp_path / "nonexistent_mkfs",
                out_ubifs=out_ubifs,
                out_fit=out_fit,
            )


if __name__ == "__main__":
    unittest.main()
