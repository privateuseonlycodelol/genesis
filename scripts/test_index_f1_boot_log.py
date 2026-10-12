#!/usr/bin/env python3
"""Literal offline fixtures; these do not establish router behavior."""
import unittest

from index_f1_boot_log import display_line, index_log


class IndexTests(unittest.TestCase):
    def test_lf_numbering_does_not_count_cr_as_lines(self):
        result = index_log(b"first\r\n\rU-Boot\r\r\nlast")
        self.assertEqual((result["lf_count"], result["lf_lines"], result["cr_count"]), (2, 3, 4))
        self.assertEqual(result["selected_lines"], [{"line": 2, "text": "U-Boot"}])
        self.assertFalse(result["final_lf"])

    def test_empty_and_final_newline(self):
        self.assertEqual(index_log(b"")["lf_lines"], 0)
        self.assertEqual(index_log(b"x\n")["lf_lines"], 1)
        self.assertEqual(index_log(b"\n")["lf_lines"], 1)
        self.assertEqual(index_log(b"\n")["tail"], [{"line": 1, "text": ""}])

    def test_known_sha256(self):
        self.assertEqual(index_log(b"abc")["sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_invalid_bytes_and_controls(self):
        result = index_log(b"\xff\r\n\x1b[31mOSCK Loaded!\x1b[0m\x00\n")
        self.assertEqual(result["invalid_utf8_lines"], [1])
        self.assertEqual(result["esc_count"], 2)
        self.assertEqual(result["selected_lines"][0]["text"], "OSCK Loaded![CTRL]")

    def test_redactions_and_concatenated_error(self):
        self.assertEqual(display_line(b"abcdef0123456789abcdef0123456789fERROR:Unable"),
                         "[REDACTED_HEX]ERROR:Unable")
        self.assertEqual(display_line(b"00:11:22:33:44:55"), "[REDACTED_MAC]")
        self.assertEqual(display_line(b"00 11 22 33 44 55 "), "[REDACTED_SPACED_MAC]")
        self.assertEqual(display_line(b"serial_num: TEST123"), "serial_num: [REDACTED_SERIAL]")
        self.assertEqual(display_line(b"5925268C-46BE-4C6D-8A91-BFD718D0AB61"), "[REDACTED_UUID]")
        self.assertEqual(display_line(b"192.0.2.123"), "[REDACTED_IPV4_SHAPE]")

    def test_literal_partition_and_negative(self):
        result = index_log(b'0x000000800000-0x000000900000 : "backup"\nnot a map\n')
        self.assertEqual(result["partitions"], [{"line": 1, "name": "backup",
                         "start": 8388608, "end_exclusive": 9437184, "size": 1048576}])
        self.assertEqual(index_log(b'0xgarbage-0x123 : "bad"')["partitions"], [])
        with self.assertRaises(ValueError):
            index_log(b'0x20-0x10 : "bad"')

    def test_messages_are_only_messages(self):
        result = index_log(b"OSCK Loaded!\nPlease press Enter to activate this console.\n")
        self.assertEqual(len(result["selected_lines"]), 2)
        self.assertNotIn("root_obtained", result)
        self.assertNotIn("key_recovered", result)

    def test_tail_line_numbers(self):
        result = index_log(b"ordinary\n" * 40)
        self.assertEqual(len(result["tail"]), 35)
        self.assertEqual((result["tail"][0]["line"], result["tail"][-1]["line"]), (6, 40))


if __name__ == "__main__":
    unittest.main()
