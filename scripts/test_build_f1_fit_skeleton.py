#!/usr/bin/env python3
"""Unit tests for build_f1_fit_skeleton.py."""

import hashlib
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_f1_fit_skeleton import (
    FdtReader,
    FdtWriter,
    build_inner_bootfs_fit,
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

    def test_standard_fit_with_rootfs_roundtrip(self):
        rootfs = b"hsqs" + bytes(range(256)) * 4
        blob = build_standard_fit_skeleton(rootfs_data=rootfs)

        nodes, props = FdtReader(blob).walk()
        self.assertIn("/images/rootfs", nodes)
        self.assertIn("/images/rootfs/hash-1", nodes)
        self.assertEqual(props["/images/rootfs:data"], rootfs)
        self.assertEqual(props["/images/rootfs:type"], b"filesystem\x00")
        self.assertEqual(props["/images/rootfs:compression"], b"none\x00")
        self.assertEqual(props["/images/rootfs/hash-1:algo"], b"sha256\x00")
        self.assertEqual(props["/images/rootfs/hash-1:value"], hashlib.sha256(rootfs).digest())
        # config-1 must name the member with the exact U-Boot lookup key
        self.assertEqual(props["/configurations/config-1:rootfs"], b"rootfs\x00")
        # kernel-1 stays, and no bootfs member is added
        self.assertIn("/images/kernel-1", nodes)
        self.assertNotIn("/images/bootfs", nodes)
        self.assertNotIn("/configurations/config-1:bootfs", props)

    def test_standard_fit_without_rootfs_has_no_rootfs_member(self):
        blob = build_standard_fit_skeleton()
        nodes, props = FdtReader(blob).walk()
        self.assertNotIn("/images/rootfs", nodes)
        self.assertNotIn("/configurations/config-1:rootfs", props)

    def test_rootfs_payload_is_not_truncated_by_padding(self):
        # 5 bytes forces 3 bytes of FDT padding; the reader must return the exact length
        rootfs = b"hsqs!"
        blob = build_standard_fit_skeleton(rootfs_data=rootfs)
        _, props = FdtReader(blob).walk()
        self.assertEqual(props["/images/rootfs:data"], rootfs)

    def test_standard_fit_with_bootfs_roundtrip(self):
        bootfs = b"\xd0\x0d\xfe\xed" + bytes(range(128))
        blob = build_standard_fit_skeleton(bootfs_data=bootfs)

        nodes, props = FdtReader(blob).walk()
        self.assertIn("/images/bootfs", nodes)
        self.assertIn("/images/bootfs/hash-1", nodes)
        self.assertEqual(props["/images/bootfs:data"], bootfs)
        self.assertEqual(props["/images/bootfs:type"], b"firmware\x00")
        self.assertEqual(props["/images/bootfs:compression"], b"none\x00")
        self.assertEqual(props["/images/bootfs/hash-1:algo"], b"sha256\x00")
        self.assertEqual(props["/images/bootfs/hash-1:value"], hashlib.sha256(bootfs).digest())
        # config-1 must have bootfs = "bootfs" for Broadcom U-Boot lookup
        self.assertEqual(props["/configurations/config-1:bootfs"], b"bootfs\x00")
        self.assertNotIn("/configurations/config-1:rootfs", props)

    def test_standard_fit_dual_component_roundtrip(self):
        bootfs = b"\xd0\x0d\xfe\xed" + b"BOOTFS-PAYLOAD"
        rootfs = b"hsqs" + b"ROOTFS-SQUASHFS-PAYLOAD"
        blob = build_standard_fit_skeleton(bootfs_data=bootfs, rootfs_data=rootfs)

        nodes, props = FdtReader(blob).walk()
        self.assertIn("/images/bootfs", nodes)
        self.assertIn("/images/rootfs", nodes)
        self.assertEqual(props["/images/bootfs:data"], bootfs)
        self.assertEqual(props["/images/rootfs:data"], rootfs)
        # Both components must be present in config-1
        self.assertEqual(props["/configurations/config-1:bootfs"], b"bootfs\x00")
        self.assertEqual(props["/configurations/config-1:rootfs"], b"rootfs\x00")

    def test_inner_bootfs_fit_roundtrip(self):
        kernel = b"AARCH64-KERNEL-IMAGE-BYTES\x00\x01\x02\x03"
        dtb = b"\xd0\x0d\xfe\xed-DTB-BYTES"
        blob = build_inner_bootfs_fit(kernel_data=kernel, dtb_data=dtb, board="GCNT-X")

        nodes, props = FdtReader(blob).walk()
        self.assertIn("/images/kernel-1", nodes)
        self.assertIn("/images/fdt-1", nodes)
        self.assertIn("/configurations/conf_linux", nodes)
        self.assertIn("/configurations/conf_lx_GCNT-X", nodes)

        self.assertEqual(props["/images/kernel-1:data"], kernel)
        self.assertEqual(props["/images/fdt-1:data"], dtb)
        self.assertEqual(props["/configurations:default"], b"conf_linux\x00")
        self.assertEqual(props["/configurations/conf_linux:kernel"], b"kernel-1\x00")
        self.assertEqual(props["/configurations/conf_linux:fdt"], b"fdt-1\x00")
        self.assertEqual(props["/configurations/conf_lx_GCNT-X:kernel"], b"kernel-1\x00")
        self.assertEqual(props["/configurations/conf_lx_GCNT-X:fdt"], b"fdt-1\x00")
        # Ensure /brcm_rootfs_encrypt is OMITTED so U-Boot skips dm-verity and dm-crypt
        self.assertNotIn("/brcm_rootfs_encrypt", nodes)


if __name__ == "__main__":
    unittest.main()
