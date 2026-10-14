#!/usr/bin/env python3
import os
import stat
import tempfile
import unittest
from pathlib import Path

from f1_secrets import read_password_file, validate_router_base


class TestValidateRouterBase(unittest.TestCase):
    def test_private_lan_ok(self):
        self.assertEqual(validate_router_base("http://192.168.2.1"), "http://192.168.2.1")

    def test_public_host_blocked(self):
        with self.assertRaises(ValueError):
            validate_router_base("http://example.com")

    def test_remote_override_env(self):
        os.environ["F1_ALLOW_REMOTE_BASE"] = "1"
        try:
            self.assertEqual(
                validate_router_base("http://example.com"),
                "http://example.com",
            )
        finally:
            os.environ.pop("F1_ALLOW_REMOTE_BASE", None)


class TestReadPasswordFile(unittest.TestCase):
    def test_requires_restrictive_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / "pw"
            secret.write_text("secret\n", encoding="utf-8")
            os.chmod(secret, stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(read_password_file(secret), "secret")

    def test_rejects_world_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / "pw"
            secret.write_text("secret\n", encoding="utf-8")
            os.chmod(secret, 0o644)
            with self.assertRaises(PermissionError):
                read_password_file(secret)


if __name__ == "__main__":
    unittest.main()
