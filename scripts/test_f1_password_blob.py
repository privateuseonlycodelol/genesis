#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from f1_password_blob import generate_password_blob, run_reference_blob_tests


class PasswordBlobTests(unittest.TestCase):
    def test_run_reference_tests_skips_with_env(self):
        with patch.dict(os.environ, {"F1_SKIP_PASSWORD_BLOB_TESTS": "1"}, clear=False):
            run_reference_blob_tests()

    @patch("f1_password_blob.subprocess.run")
    def test_generate_calls_shim(self, mock_run):
        mock_run.side_effect = [
            mock.Mock(
                returncode=0,
                stdout='{"salt":"ab","verifier":"cd","cryptedpassword":"$6$x"}',
                stderr="",
            ),
        ]
        with patch.dict(os.environ, {"F1_SKIP_PASSWORD_BLOB_TESTS": "1"}, clear=False):
            blob = generate_password_blob("User", "secret")
        self.assertEqual(blob["salt"], "ab")
        mock_run.assert_called_once()
        self.assertIn("f1_password_blob.mjs", mock_run.call_args.args[0][1])


if __name__ == "__main__":
    unittest.main()
