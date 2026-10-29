#!/usr/bin/env python3
"""Unit tests for f1_modal_discovery candidate definitions and parser."""
import unittest
from scripts.f1_modal_discovery import CANDIDATES

class TestModalDiscovery(unittest.TestCase):
    def test_candidates_list(self):
        self.assertGreater(len(CANDIDATES), 20)
        self.assertIn("printersharing-modal.lp", CANDIDATES)
        self.assertIn("cwmpconf-modal.lp", CANDIDATES)
        self.assertIn("wireless-client-modal.lp", CANDIDATES)
        for c in CANDIDATES:
            self.assertTrue(c.endswith(".lp"), f"Invalid candidate: {c}")

if __name__ == "__main__":
    unittest.main()
