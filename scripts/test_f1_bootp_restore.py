#!/usr/bin/env python3
"""Tests for the interface restore logic in f1_bootp_tftp_mac.py (no network changes)."""
import unittest

from f1_bootp_tftp_mac import parse_getinfo, restore_commands

MANUAL_OUT = """Manual Configuration
IP address: 192.168.1.100
Subnet mask: 255.255.255.0
Router: 192.168.1.100
"""

DHCP_OUT = """DHCP Configuration
IP address: 192.168.1.150
Subnet mask: 255.255.255.0
Router: 192.168.1.1
DHCP Client ID: nils
"""


class ParseGetinfoTests(unittest.TestCase):
    def test_manual_config(self):
        self.assertEqual(
            parse_getinfo(MANUAL_OUT),
            {"mode": "Manual", "ip": "192.168.1.100", "mask": "255.255.255.0", "router": "192.168.1.100"},
        )

    def test_dhcp_config(self):
        info = parse_getinfo(DHCP_OUT)
        self.assertEqual(info["mode"], "DHCP")
        self.assertEqual(info["ip"], "192.168.1.150")


class RestoreCommandTests(unittest.TestCase):
    def test_dhcp_prior_restores_dhcp(self):
        prior = parse_getinfo(DHCP_OUT)
        self.assertEqual(
            restore_commands("USB 10/100/1000 LAN", prior, "192.168.1.2"),
            [["networksetup", "-setdhcp", "USB 10/100/1000 LAN"], ["arp", "-d", "192.168.1.2"]],
        )

    def test_manual_prior_restores_manual_values(self):
        prior = parse_getinfo(MANUAL_OUT)
        self.assertEqual(
            restore_commands("svc", prior, "192.168.1.2")[0],
            ["networksetup", "-setmanual", "svc", "192.168.1.100", "255.255.255.0", "192.168.1.100"],
        )

    def test_unknown_prior_only_clears_arp(self):
        self.assertEqual(restore_commands("svc", None, "192.168.1.2"), [["arp", "-d", "192.168.1.2"]])

    def test_no_service_only_clears_arp(self):
        self.assertEqual(restore_commands(None, parse_getinfo(DHCP_OUT), "192.168.1.2"), [["arp", "-d", "192.168.1.2"]])

    def test_incomplete_manual_prior_skips_service_restore(self):
        prior = {"mode": "Manual", "ip": "192.168.1.100"}
        self.assertEqual(restore_commands("svc", prior, "192.168.1.2"), [["arp", "-d", "192.168.1.2"]])


if __name__ == "__main__":
    unittest.main()
