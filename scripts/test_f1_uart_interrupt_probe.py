#!/usr/bin/env python3
"""Unit tests for the pure logic in f1_uart_interrupt_probe.py (no device needed)."""
import unittest

from f1_uart_interrupt_probe import KEY_CYCLE, is_allowed, parse_keys, should_stop


class SendAllowlistTests(unittest.TestCase):
    def test_every_cycle_key_allowed(self):
        for key in KEY_CYCLE:
            self.assertTrue(is_allowed(key), key)

    def test_a_key_allowed(self):
        self.assertTrue(is_allowed(b"a"))

    def test_boot_p_trigger_refused(self):
        self.assertFalse(is_allowed(b"b"))
        self.assertFalse(is_allowed(b"B"))

    def test_b_never_in_cycle(self):
        self.assertNotIn(b"b", KEY_CYCLE)
        self.assertNotIn(b"B", KEY_CYCLE)

    def test_unlisted_bytes_refused(self):
        for byte in (b"x", b"1", b"\x04", b"id", b""):
            self.assertFalse(is_allowed(byte), byte)


class ParseKeysTests(unittest.TestCase):
    def test_single_a(self):
        self.assertEqual(parse_keys("a"), (b"a",))

    def test_mixed_keys(self):
        self.assertEqual(parse_keys("a\t"), (b"a", b"\t"))

    def test_b_refused_anywhere(self):
        for text in ("b", "ab", "Bx"):
            with self.assertRaises(ValueError, msg=text):
                parse_keys(text)

    def test_unlisted_key_refused(self):
        with self.assertRaises(ValueError):
            parse_keys("x")


class StopPromptTests(unittest.TestCase):
    def test_uboot_prompt_stops(self):
        self.assertTrue(should_stop(b"...\r\n=> "))
        self.assertTrue(should_stop(b"U-Boot> "))

    def test_login_prompt_stops(self):
        self.assertTrue(should_stop(b"router login: "))

    def test_linux_console_stops(self):
        self.assertTrue(should_stop(b"Please press Enter to activate this console."))

    def test_mount_root_stops(self):
        self.assertTrue(should_stop(b"mount_root: executing script in /lib/mount_root"))

    def test_boot_banner_does_not_stop(self):
        self.assertFalse(should_stop(b"U-Boot 2019.07 (Jan 06 2025)"))
        self.assertFalse(should_stop(b"*** Press b to enter BOOT-P ***"))


if __name__ == "__main__":
    unittest.main()
