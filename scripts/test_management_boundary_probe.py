#!/usr/bin/env python3
"""Offline controls for response classification and immediate probe stopping."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import management_boundary_probe as probe


class BoundaryTests(unittest.TestCase):
    def test_login_html_cannot_be_metadata(self):
        result = probe.classify(b'<html><button id="sign-me-in">Login</button></html>')
        self.assertTrue(result["login_marker"])
        self.assertFalse(result["json_object"])
        self.assertNotIn("current_role", result)

    def test_independent_literal_success_fixtures(self):
        self.assertEqual(probe.classify(b'{"current_role":"admin"}')["current_role"], "admin")
        self.assertTrue(probe.classify(b'{"success":"true","banksize":"134217728"}')["bank_metadata"])

    def test_negative_and_malformed_json(self):
        for body in (b'[]', b'{broken', b'\xff', b'null'):
            self.assertFalse(probe.classify(body)["json_object"])
        for body in (b'{"success":false,"banksize":"134217728"}',
                     b'{"success":"true","banksize":"0"}'):
            self.assertFalse(probe.classify(body)["bank_metadata"])

    def test_transport_failure_and_503_stop_without_followup(self):
        for code, status in ((7, b'000'), (0, b'503')):
            with tempfile.TemporaryDirectory() as directory:
                previous_umask = probe.os.umask(0o077)
                try:
                    with patch.object(probe, 'ROOT', Path(directory)), \
                         patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, status, b'')) as run, \
                         patch.object(probe.time, 'sleep') as sleep, \
                         contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(probe.main(), 1)
                        self.assertEqual(run.call_count, 1)
                        sleep.assert_not_called()
                finally:
                    probe.os.umask(previous_umask)


if __name__ == '__main__':
    unittest.main()
