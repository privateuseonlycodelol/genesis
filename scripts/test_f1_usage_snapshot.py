#!/usr/bin/env python3
import unittest
from datetime import datetime, timezone

from f1_usage_snapshot import (
    REMOTE,
    cpu_busy_pct,
    fail_snapshot,
    parse_df,
    parse_netdev,
    parse_snapshot,
    pick_overlay_kib,
    seed_snapshot,
)

FIXTURE = """
@@LOAD
0.12 0.18 0.23 1/50 10
@@MEM
MemTotal:        494592 kB
MemAvailable:     94208 kB
Slab:            106496 kB
@@NET
eth4: 1000 1 0 0 0 0 0 0 2000 1 0 0 0 0 0 0
br-lan: 3000 1 0 0 0 0 0 0 4000 1 0 0 0 0 0 0
lo: 9 0 0 0 0 0 0 0 9 0 0 0 0 0 0 0
@@DF
Filesystem 1K-blocks Used Available Use% Mounted on
ubi0:overlay 100000 10000 87040 11% /overlay
@@UP
101.0 2.0
@@CPU1
cpu  100 0 100 1000 0 0 0 0
@@CPU2
cpu  110 0 110 1080 0 0 0 0
@@PROCS
1 16384 airties
2 6440 cloud-comm
3 5120 wlan_mgr
4 3788 cwmpd
5 2000 datausaged
6 1900 datausage-notifier
7 1800 mosquitto
8 1900 mosquitto
9 100 nginx
10 0 [kworker]
@@TOP
CPU:  13% usr
  PID  PPID USER     STAT   VSZ %VSZ %CPU COMMAND
    9     1 root     S    100m  0.1  13.0 nginx
    1     1 root     S     16m  3.0   0.0 airties
  PID  PPID USER     STAT   VSZ %VSZ %CPU COMMAND
    9     1 root     S    100m  0.1   3.5 nginx
    1     1 root     S     16m  3.0   0.0 airties
"""


class TestF1UsageSnapshot(unittest.TestCase):
    def test_remote_is_read_only(self):
        folded = REMOTE.lower()
        for banned in ("uci ", "reboot", "passwd", "rm ", "wifi", "mtd write"):
            self.assertNotIn(banned, folded)

    def test_cpu_delta(self):
        self.assertEqual(cpu_busy_pct((1200, 1000), (1300, 1080)), 20.0)
        self.assertIsNone(cpu_busy_pct((10, 5), (10, 5)))

    def test_overlay_and_netdev(self):
        rows = parse_df("Filesystem 1K-blocks Used Available Use% Mounted on\nubi 1 2 85 1% /overlay\n")
        self.assertEqual(pick_overlay_kib(rows), 85)
        net = parse_netdev("eth4: 5 0 0 0 0 0 0 0 9 0 0 0 0 0 0 0\n")
        self.assertEqual(net["eth4"], (5, 9))

    def test_parse_live_shape(self):
        when = datetime(2026, 11, 6, 20, 50, tzinfo=timezone.utc)
        snap = parse_snapshot(FIXTURE, when)
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["kind"], "ssh")
        self.assertEqual(snap["cpuPct"], 20.0)
        self.assertEqual(snap["memTotalMib"], 483.0)
        self.assertEqual(snap["memAvailableMib"], 92.0)
        self.assertEqual(snap["slabMib"], 104.0)
        self.assertEqual(snap["overlayFreeMib"], 85.0)
        self.assertEqual(snap["traffic"][0]["name"], "WAN eth4")
        self.assertEqual(snap["traffic"][0]["inBytes"], 1000)
        names = [row["name"] for row in snap["topRam"]]
        self.assertTrue(any(name.startswith("mosquitto ") for name in names))
        self.assertNotIn("[kworker]", names)
        idle_names = [row["name"] for row in snap["idle"]]
        self.assertTrue(any(name.startswith("airties") or name == "airties" for name in idle_names))
        self.assertNotIn("wlan_mgr", idle_names)
        self.assertEqual(snap["notRunning"], ["obuspa", "miniupnp", "F-Secure", "sense"])
        nginx = next(row for row in snap["topCpu"] if row["name"] == "nginx")
        self.assertEqual(nginx["cpuPct"], 3.5)

    def test_failure_keeps_last_numbers(self):
        previous = seed_snapshot()
        failed = fail_snapshot(previous, "SSH timed out", datetime(2026, 11, 6, 20, 55, tzinfo=timezone.utc))
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["error"], "SSH timed out")
        self.assertEqual(failed["traffic"], previous["traffic"])
        self.assertEqual(failed["readAt"], previous["readAt"])


if __name__ == "__main__":
    unittest.main()
