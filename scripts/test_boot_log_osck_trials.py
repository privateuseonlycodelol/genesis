#!/usr/bin/env python3
import unittest

from attempt_rbi_decrypt import boot_log_derived_candidates


class BootLogOsckTrials(unittest.TestCase):
    def test_boot_log_candidates_are_unique_32_byte_keys(self):
        seen: set[bytes] = set()
        for name, key in boot_log_derived_candidates():
            self.assertEqual(len(key), 32, name)
            self.assertNotIn(key, seen, name)
            seen.add(name)

    def test_boot_log_candidate_count(self):
        self.assertGreaterEqual(len(boot_log_derived_candidates()), 18)


if __name__ == "__main__":
    unittest.main()
