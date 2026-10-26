#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))


class ImpactGuardTests(unittest.TestCase):
    def test_refuses_live_without_ack(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "f1_password_encoding_impact.py"),
                "--password-file",
                str(ROOT / "artifacts" / "secrets" / "f1-admin.password"),
                "--new-password",
                "Aa0!TestPass9",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        if not (ROOT / "artifacts" / "secrets" / "f1-admin.password").is_file():
            self.skipTest("no password file")
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data.get("error"), "refused")

    @patch("f1_password_encoding_impact.run_reference_blob_tests")
    @patch("f1_password_encoding_impact.generate_password_blob")
    def test_dry_run_does_not_touch_device(self, mock_blob, _mock_tests):
        import f1_password_encoding_impact as impact

        mock_blob.return_value = {
            "salt": "abcd1234",
            "verifier": "v" * 512,
            "cryptedpassword": "$6$abcd",
        }
        with patch.object(
            sys,
            "argv",
            [
                "f1_password_encoding_impact.py",
                "--password-file",
                "/nonexistent",
                "--new-password",
                "x",
                "--dry-run",
            ],
        ):
            with patch.object(impact, "read_password_file", return_value="dummy"):
                self.assertEqual(impact.main(), 0)
        mock_blob.assert_called_once()


if __name__ == "__main__":
    unittest.main()
