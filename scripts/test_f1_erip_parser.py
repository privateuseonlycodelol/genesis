#!/usr/bin/env python3
"""Unit tests for scripts/f1_erip_parser.py."""

from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from Crypto.Cipher import AES

from scripts.f1_erip_parser import (
    ATTR_ECK_ENCR,
    ATTR_EIK_SIGN,
    ATTR_LOCKED,
    ATTR_VALID,
    INDEX_RECORD_SIZE,
    RIP_ITEM_NAMES,
    decrypt_item_eck,
    dump_items_to_directory,
    parse_eripv2_image,
)


def build_synthetic_erip(items_spec: list, total_size: int = 65536) -> bytes:
    """Helper to construct a valid synthetic eRIPv2 binary image.

    items_spec is a list of tuples: (item_id, payload_bytes, attr_lo, attr_hi)
    """
    buf = bytearray(total_size)
    current_addr = 0x100  # Start data area at 256 bytes

    index_entries = []
    for item_id, payload, attr_lo, attr_hi in items_spec:
        length = len(payload)
        buf[current_addr : current_addr + length] = payload

        # Record: [item_id: uint16, addr ^ 0x20000: uint32, attr_lo: uint32, attr_hi: uint32, length: uint32]
        addr_encoded = current_addr ^ 0x20000
        record = struct.pack(">HLLLL", item_id, addr_encoded, attr_lo, attr_hi, length)
        index_entries.append(record)

        current_addr += length
        if current_addr % 16 != 0:
            current_addr += 16 - (current_addr % 16)  # 16-byte align

    # Place index records from end of buffer walking backwards
    # The last 4 bytes are reserved (CRC32/footer)
    end_data_offset = total_size - 4
    for idx, record in enumerate(index_entries, start=1):
        offset = end_data_offset - (idx * INDEX_RECORD_SIZE)
        buf[offset : offset + INDEX_RECORD_SIZE] = record

    # Write end-of-index marker (0xFFFF)
    term_offset = end_data_offset - ((len(index_entries) + 1) * INDEX_RECORD_SIZE)
    buf[term_offset : term_offset + 2] = b"\xff\xff"

    return bytes(buf)


class TestF1EripParser(unittest.TestCase):
    def test_parse_plain_items(self):
        items_spec = [
            (0x0012, b"CP22349AE12345", 0x0, 0xFFFFFFFF),  # RIP_ID_BOARD_SERIAL_NBR
            (0x0040, b"GCNT-X", 0x0, 0xFFFFFFFF),           # RIP_ID_BOARD_NAME
            (0x0032, b"\x00\x11\x22\x33\x44\x55", 0x0, 0xFFFFFFFF),  # RIP_ID_LAN_ADDR
        ]
        image = build_synthetic_erip(items_spec)
        items = parse_eripv2_image(image)

        self.assertEqual(len(items), 3)
        item_dict = {i.item_id: i for i in items}

        self.assertIn(0x0012, item_dict)
        self.assertEqual(item_dict[0x0012].name, "RIP_ID_BOARD_SERIAL_NBR")
        self.assertEqual(item_dict[0x0012].raw_data, b"CP22349AE12345")
        self.assertEqual(item_dict[0x0012].decrypted_data, b"CP22349AE12345")
        self.assertTrue(item_dict[0x0012].decrypted_ok)

        self.assertIn(0x0040, item_dict)
        self.assertEqual(item_dict[0x0040].raw_data, b"GCNT-X")

        self.assertIn(0x0032, item_dict)
        self.assertEqual(item_dict[0x0032].raw_data, b"\x00\x11\x22\x33\x44\x55")

    def test_parse_and_decrypt_encrypted_item(self):
        eck_key = b"0123456789abcdef"  # 16-byte AES-128 key
        secret_content = b"TOP_SECRET_RIP_DATA_FOR_TELIA_F1"

        # Apply PKCS#7 padding
        pad_len = 16 - (len(secret_content) % 16)
        padded = secret_content + bytes([pad_len] * pad_len)

        # Encrypt with AES-CBC
        iv = b"fedcba9876543210"
        cipher = AES.new(eck_key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(padded)
        encrypted_payload = iv + ciphertext

        # Attribute active-low: clear ATTR_ECK_ENCR bit
        attr_hi = 0xFFFFFFFF & ~ATTR_ECK_ENCR

        items_spec = [
            (0x0108, encrypted_payload, 0x0, attr_hi),  # RIP_ID_RANDOM_KEY_B
        ]
        image = build_synthetic_erip(items_spec)

        # Without ECK key, item remains encrypted
        items_locked = parse_eripv2_image(image, eck_key=None)
        self.assertEqual(len(items_locked), 1)
        self.assertTrue(items_locked[0].is_encrypted)
        self.assertFalse(items_locked[0].decrypted_ok)

        # With ECK key, item is decrypted
        items_unlocked = parse_eripv2_image(image, eck_key=eck_key)
        self.assertEqual(len(items_unlocked), 1)
        self.assertTrue(items_unlocked[0].is_encrypted)
        self.assertTrue(items_unlocked[0].decrypted_ok)
        self.assertEqual(items_unlocked[0].decrypted_data, secret_content)

    def test_dump_to_directory(self):
        items_spec = [
            (0x0040, b"GCNT-X", 0x0, 0xFFFFFFFF),
        ]
        image = build_synthetic_erip(items_spec)
        items = parse_eripv2_image(image)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            dump_items_to_directory(items, out_path)

            extracted_file = out_path / "0040_RIP_ID_BOARD_NAME.bin"
            self.assertTrue(extracted_file.exists())
            self.assertEqual(extracted_file.read_bytes(), b"GCNT-X")

            manifest_file = out_path / "manifest.json"
            self.assertTrue(manifest_file.exists())
            manifest = json.loads(manifest_file.read_text())
            self.assertEqual(len(manifest), 1)
            self.assertEqual(manifest[0]["name"], "RIP_ID_BOARD_NAME")

    def test_short_buffer_raises_error(self):
        with self.assertRaises(ValueError):
            parse_eripv2_image(b"too_short")


if __name__ == "__main__":
    unittest.main()
