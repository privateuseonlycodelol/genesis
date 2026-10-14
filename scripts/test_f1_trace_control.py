#!/usr/bin/env python3
import unittest

from f1_trace_control import classify_line, TRACE_HELPER


class TestClassifyLine(unittest.TestCase):
    def test_long_helper_args_are_hashed_not_logged(self):
        msg = TRACE_HELPER + " " + ("x" * 300)
        event = classify_line(msg)
        self.assertTrue(event["arguments_logged"])
        self.assertIn("sha256", event)
        self.assertNotIn("message", event)

    def test_short_helper_args_kept(self):
        msg = TRACE_HELPER + " 127.0.0.1"
        event = classify_line(msg)
        self.assertEqual(event.get("message"), msg)


if __name__ == "__main__":
    unittest.main()
