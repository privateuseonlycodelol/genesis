#!/usr/bin/env python3
import unittest

from f1_gap_attack_pass import CLOSED, OPEN_ELSEWHERE, catalog


class TestGapAttack(unittest.TestCase):
    def test_catalog_sends_nothing(self):
        body = catalog()
        self.assertTrue(body["retired"])
        self.assertFalse(body["live_requests"])
        phases = {row["phase"] for row in body["closed"]}
        self.assertEqual(
            phases, {"auth", "sched", "blind_ssrf", "services", "offline"}
        )
        self.assertTrue(all(row[1] == "closed" for row in CLOSED))

    def test_open_work_is_not_this_script(self):
        self.assertIn("scripts/f1_ipping_host_probe.py", OPEN_ELSEWHERE)
        self.assertNotIn("scripts/f1_gap_attack_pass.py", OPEN_ELSEWHERE)


if __name__ == "__main__":
    unittest.main()
