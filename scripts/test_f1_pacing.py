#!/usr/bin/env python3
import unittest

from f1_pacing import DEFAULT_REQUEST_GAP_S, LOGIN_POLL_INTERVAL_S


class TestF1Pacing(unittest.TestCase):
    def test_defaults_conservative(self):
        self.assertGreaterEqual(DEFAULT_REQUEST_GAP_S, 3.0)
        self.assertGreaterEqual(LOGIN_POLL_INTERVAL_S, 60.0)


if __name__ == "__main__":
    unittest.main()
