#!/usr/bin/env python3
"""Tests for the restart request body in f1_restart_router.py (no network)."""
import unittest
import urllib.parse

from f1_restart_router import FORBIDDEN_ACTIONS, RESTART_ACTION, build_restart_body


class RestartBodyTests(unittest.TestCase):
    def test_body_is_system_reboot(self):
        fields = urllib.parse.parse_qs(build_restart_body("tok123").decode())
        self.assertEqual(fields["action"], ["system_reboot"])
        self.assertEqual(fields["CSRFtoken"], ["tok123"])

    def test_restart_action_not_forbidden(self):
        self.assertNotIn(RESTART_ACTION, FORBIDDEN_ACTIONS)

    def test_soft_reset_and_factory_reset_refused_as_actions(self):
        self.assertIn("system_softReset", FORBIDDEN_ACTIONS)
        self.assertIn("system_factory_reset", FORBIDDEN_ACTIONS)


if __name__ == "__main__":
    unittest.main()
