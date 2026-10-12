#!/usr/bin/env python3
"""Offline regressions for live-control sequencing; all HTTP is mocked."""
import contextlib
import io
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import f1_readonly_control as control


class SequencingTests(unittest.TestCase):
    def run_control(self, authenticated=True, bank_ok=True, export_status=200, export_html=False):
        calls = []

        class FakeClient:
            base = "http://192.168.2.1"

            def __init__(self, directory):
                self.csrf = ""
                self.rows = []

            def login(self, username, password):
                assert username == "User" and password == "dummy-password"
                assert self.csrf == "login-token"
                return 200, "ok"

            def _open(self, url, data=None, method="GET"):
                calls.append((url, data, method))
                login_marker = False
                if url.endswith("/login.lp"):
                    body = b'<meta name="CSRFtoken" content="login-token">'
                elif url.endswith("/gateway.lp"):
                    body = b'<meta name="CSRFtoken" content="authenticated-token">'
                    login_marker = not authenticated
                elif "getSessionStatus" in url:
                    body = b'{"current_role":"admin"}'
                elif "getbanksize" in url:
                    body = b'{"success":"true","banksize":"134217728"}' if bank_ok else b'<html>login</html>'
                elif method == "POST":
                    parsed = urllib.parse.parse_qs(data.decode())
                    assert parsed == {"action": ["export_config"], "CSRFtoken": ["authenticated-token"]}
                    body = b"FORMAT=dummy\nMODE=synthetic\n\n" + bytes(range(68))
                    if export_status != 200 or export_html:
                        body = b"<html>403 Forbidden</html>"
                else:
                    raise AssertionError("unexpected request")
                self.rows.append({"login_marker": login_marker})
                return (export_status if method == "POST" else 200), body

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(control, "ROOT", Path(directory)), patch.object(control, "ControlClient", FakeClient):
                with patch.object(control.getpass, "getpass", return_value="dummy-password"):
                    with patch("sys.argv", ["f1_readonly_control.py", "--export"]), contextlib.redirect_stdout(io.StringIO()):
                        result = control.main()
        return result, calls

    def test_export_uses_rotated_authenticated_token(self):
        result, calls = self.run_control()
        self.assertEqual(result, 0)
        self.assertEqual(sum(method == "POST" for _, _, method in calls), 1)
        self.assertEqual(calls[-1][2], "POST")

    def test_failed_base_control_stops_before_hidden_actions(self):
        result, calls = self.run_control(authenticated=False)
        self.assertEqual(result, 1)
        self.assertEqual(len(calls), 2)
        self.assertFalse(any(method == "POST" for _, _, method in calls))

    def test_bad_bank_metadata_stops_before_export(self):
        result, calls = self.run_control(bank_ok=False)
        self.assertEqual(result, 1)
        self.assertFalse(any(method == "POST" for _, _, method in calls))

    def test_export_forbidden_is_failure(self):
        result, calls = self.run_control(export_status=403)
        self.assertEqual(result, 1)
        self.assertEqual(calls[-1][2], "POST")

    def test_http200_html_is_not_a_successful_export(self):
        result, calls = self.run_control(export_html=True)
        self.assertEqual(result, 1)
        self.assertEqual(calls[-1][2], "POST")


if __name__ == "__main__":
    unittest.main()
