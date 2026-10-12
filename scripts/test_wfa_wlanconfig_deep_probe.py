#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wfa_wlanconfig_deep_probe as deep


class Tests(unittest.TestCase):
    def test_shell_m2_wire_size(self):
        nonce = bytes(16)
        blob = deep.shell_m2(nonce)
        self.assertEqual(len(blob), 5 + 5 + 20 + 20)


if __name__ == "__main__":
    unittest.main()
