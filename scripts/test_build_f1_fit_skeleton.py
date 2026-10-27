#!/usr/bin/env python3
"""Unit tests for build_f1_fit_skeleton.py."""

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_f1_fit_skeleton import (
    FdtReader,
    FdtWriter,
    build_minimal_fit_skeleton,
    build_standard_fit_skeleton,
)


class TestBuildF1FitSkeleton(unittest.TestCase):
    def test_minimal_fit_skeleton_header(self):
        blob = build_minimal_fit_skeleton()
        self.assertGreaterEqual(len(blob), 40)
        # Check magic
        magic = struct.unpack("!I", blob[:4])[0]
        self.assertEqual(magic, 0xD00DFEED)

        # Parse with FdtReader
        reader = FdtReader(blob)
        self.assertEqual(reader.magic, 0xD00DFEED)
        self.assertEqual(reader.totalsize, len(blob))
        self.assertEqual(reader.version, 17)

        nodes, props = reader.walk()
        self.assertIn("/", nodes)
        self.assertIn("/images", nodes)
        self.assertIn("/:description", props)
        self.assertIn("/:#address-cells", props)

    def test_standard_fit_skeleton_roundtrip(self):
        payload = b"TEST-KERNEL-PAYLOAD\n"
        blob = build_standard_fit_skeleton(payload_data=payload)

        reader = FdtReader(blob)
        nodes, props = reader.walk()

        # Check nodes hierarchy
        self.assertIn("/", nodes)
        self.assertIn("/images", nodes)
        self.assertIn("/images/kernel-1", nodes)
        self.assertIn("/images/kernel-1/hash-1", nodes)
        self.assertIn("/configurations", nodes)
        self.assertIn("/configurations/config-1", nodes)

        # Check properties
        self.assertEqual(props["/images/kernel-1:data"], payload)
        self.assertEqual(props["/images/kernel-1:type"], b"kernel\x00")
        self.assertEqual(props["/images/kernel-1:arch"], b"arm64\x00")
        self.assertEqual(props["/images/kernel-1:os"], b"linux\x00")
        self.assertEqual(props["/images/kernel-1:compression"], b"none\x00")

        # Check hash
        import hashlib

        expected_hash = hashlib.sha256(payload).digest()
        self.assertEqual(props["/images/kernel-1/hash-1:value"], expected_hash)
        self.assertEqual(props["/images/kernel-1/hash-1:algo"], b"sha256\x00")

        # Check configurations
        self.assertEqual(props["/configurations:default"], b"config-1\x00")
        self.assertEqual(props["/configurations/config-1:kernel"], b"kernel-1\x00")

    def test_fdt_writer_alignment(self):
        w = FdtWriter()
        w.begin_node("")
        w.property("test1", b"123")  # 3 bytes, requires 1 byte pad
        w.property("test2", b"12345")  # 5 bytes, requires 3 bytes pad
        w.end_node()
        blob = w.build()

        reader = FdtReader(blob)
        nodes, props = reader.walk()
        self.assertEqual(props["/:test1"], b"123")
        self.assertEqual(props["/:test2"], b"12345")

    def test_fdt_reader_invalid_magic(self):
        bad_blob = b"\x00\x00\x00\x00" + b"\x00" * 40
        with self.assertRaises(ValueError):
            FdtReader(bad_blob)

    def test_fdt_reader_too_short(self):
        with self.assertRaises(ValueError):
            FdtReader(b"\xd0\x0d\xfe\xed")


if __name__ == "__main__":
    unittest.main()
