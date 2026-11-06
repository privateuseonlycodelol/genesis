#!/usr/bin/env python3
"""Unit tests for validate_f1_fit_bundle.py.

Positive and negative cases built with build_f1_fit_skeleton.py; every negative
case mutates one contract element that maps to a specific U-Boot code path.
"""

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
    build_standard_fit_skeleton,
)
from validate_f1_fit_bundle import (
    Report,
    validate_bundle,
    validate_bootfs_payload,
)

KERNEL = b"PLACEHOLDER-AARCH64-KERNEL-NOT-REAL\n"
DTB = b"\xd0\x0d\xfe\xed-DTB-PLACEHOLDER"
SQUASHFS = b"hsqs" + b"placeholder-squashfs-payload" * 4


def valid_inner_bootfs() -> bytes:
    return build_inner_bootfs_fit(kernel_data=KERNEL, dtb_data=DTB, board="GCNT-X")


def valid_bundle() -> bytes:
    return build_standard_fit_skeleton(
        bootfs_data=valid_inner_bootfs(), rootfs_data=SQUASHFS
    )


class TestValidateF1FitBundle(unittest.TestCase):
    def test_valid_dual_component_bundle_passes(self):
        report = validate_bundle(valid_bundle())
        self.assertEqual(report.errors, [])
        # Contract coverage: both members resolve, hashes verify
        self.assertTrue(
            any("bootfs" in i and "/images/bootfs" in i for i in report.info)
        )
        self.assertTrue(
            any("rootfs" in i and "/images/rootfs" in i for i in report.info)
        )
        # Secure gate flagged as warning for the unsigned placeholder bootfs
        self.assertTrue(any("SECURE-BOOT GATE" in w for w in report.warnings))

    def test_absent_members_reported_as_skipped(self):
        blob = build_standard_fit_skeleton(payload_data=KERNEL)
        report = validate_bundle(blob)
        self.assertEqual(report.errors, [])
        skipped = [i for i in report.info if "skipping!" in i]
        self.assertEqual(len(skipped), 5)  # bootfs, rootfs, loader, rootfs_data, ramfs_rd

    def test_not_an_fdt(self):
        report = validate_bundle(b"NOPE" + b"\x00" * 64)
        self.assertFalse(report.ok)
        self.assertTrue(any("not an FDT" in e for e in report.errors))

    def test_truncated_header(self):
        report = validate_bundle(b"\xd0\x0d\xfe\xed")
        self.assertFalse(report.ok)

    def test_missing_configurations_node(self):
        w = FdtWriter()
        w.begin_node("")
        w.property_string("description", "no configurations")
        w.end_node()
        report = validate_bundle(w.build())
        self.assertFalse(report.ok)
        self.assertTrue(any("/configurations" in e for e in report.errors))

    def test_missing_compatible_on_config(self):
        # Rebuild a bundle whose config-1 lacks 'compatible' by patching the
        # property value away is hard (lengths differ), so construct via writer
        # through build_standard_fit_skeleton then patch to a zero-length value.
        blob = valid_bundle()
        old = b"GCNT-X\x00\x00"  # config-1:compatible value (padded)
        idx = blob.find(b"configurations\x00")
        # find the second occurrence of the compat value after /configurations
        marker = blob.find(old, blob.find(b"config-1\x00"))
        assert marker != -1
        # zero out the value and its length field is unchanged; an empty string
        # property (len 4 with just NUL) reads as "" -> still present. To model
        # absence we must instead verify the error path directly with a writer.
        w = FdtWriter()
        w.begin_node("")
        w.property_u32("#address-cells", 1)
        w.begin_node("images")
        w.end_node()
        w.begin_node("configurations")
        w.property_string("default", "config-1")
        w.begin_node("config-1")
        w.property_string("kernel", "kernel-1")
        w.end_node()
        w.end_node()
        w.end_node()
        report = validate_bundle(w.build())
        self.assertFalse(report.ok)
        self.assertTrue(any("compatible" in e for e in report.errors))
        del blob, idx, marker  # unused path

    def test_wrong_hash_aborts_upgrade(self):
        blob = valid_bundle()
        reader = FdtReader(blob)
        _, props = reader.walk()
        digest = props["/images/rootfs/hash-1:value"]
        bad = bytes(32)  # same length, all zeros
        idx = blob.find(digest)
        self.assertNotEqual(idx, -1)
        blob = blob[:idx] + bad + blob[idx + 32 :]
        report = validate_bundle(blob)
        self.assertFalse(report.ok)
        self.assertTrue(
            any("hash-1 value does not match" in e for e in report.errors)
        )

    def test_missing_hash_node_fails_whole_upgrade(self):
        # Build outer bundle with bootfs only; then check an image without hash-1.
        w = FdtWriter()
        w.begin_node("")
        w.property_u32("#address-cells", 1)
        w.begin_node("images")
        w.begin_node("bootfs")
        w.property("data", b"\xd0\x0d\xfe\xedNOHASH")
        w.property_string("type", "firmware")
        w.end_node()
        w.end_node()
        w.begin_node("configurations")
        w.property_string("default", "config-1")
        w.begin_node("config-1")
        w.property_string("bootfs", "bootfs")
        w.property_string("compatible", "GCNT-X")
        w.end_node()
        w.end_node()
        w.end_node()
        report = validate_bundle(w.build())
        self.assertFalse(report.ok)
        self.assertTrue(
            any("missing hash-1" in e for e in report.errors)
        )

    def test_config_reference_to_missing_image(self):
        w = FdtWriter()
        w.begin_node("")
        w.property_u32("#address-cells", 1)
        w.begin_node("images")
        w.begin_node("bootfs")
        w.property("data", b"\xd0\x0d\xfe\xedPAYLOAD")
        w.end_node()
        w.begin_node("hash-1")
        w.property_string("algo", "sha256")
        w.property("value", hashlib.sha256(b"\xd0\x0d\xfe\xedPAYLOAD").digest())
        w.end_node()
        w.end_node()
        w.end_node()
        w.begin_node("configurations")
        w.property_string("default", "config-1")
        w.begin_node("config-1")
        w.property_string("bootfs", "nope")
        w.property_string("compatible", "GCNT-X")
        w.end_node()
        w.end_node()
        w.end_node()
        report = validate_bundle(w.build())
        self.assertFalse(report.ok)
        self.assertTrue(
            any("does not resolve to /images/nope" in e for e in report.errors)
        )

    def test_non_gcntx_compatible_warns(self):
        w = FdtWriter()
        w.begin_node("")
        w.property_u32("#address-cells", 1)
        w.begin_node("images")
        w.end_node()
        w.begin_node("configurations")
        w.property_string("default", "config-1")
        w.begin_node("config-1")
        w.property_string("compatible", "OTHER-BOARD")
        w.end_node()
        w.end_node()
        w.end_node()
        report = validate_bundle(w.build())
        self.assertEqual(
            [e for e in report.errors if "compatible" in e], []
        )
        self.assertTrue(any("GCNT-X" in w for w in report.warnings))

    def test_totalsize_mismatch_detected(self):
        blob = valid_bundle() + b"\x00" * 4
        report = validate_bundle(blob)
        self.assertFalse(report.ok)
        self.assertTrue(any("totalsize" in e for e in report.errors))

    def test_rootfs_bad_magic_warns(self):
        blob = build_standard_fit_skeleton(rootfs_data=b"XXXX" + b"junk" * 8)
        report = validate_bundle(blob)
        self.assertEqual(report.errors, [])
        self.assertTrue(
            any("recognized magic" in w for w in report.warnings)
        )

    def test_unsigned_inner_bootfs_flags_secure_gate(self):
        report = Report()
        validate_bootfs_payload(valid_inner_bootfs(), report)
        self.assertTrue(any("SECURE-BOOT GATE" in w for w in report.warnings))
        self.assertTrue(
            any("/brcm_rootfs_encrypt" in i and "omits" in i for i in report.info)
        )

    def test_signed_tag_present_no_gate_warning(self):
        inner = valid_inner_bootfs()
        tagged = inner + struct.pack("!I", 0x46495453) + b"\x00" * 260
        report = Report()
        validate_bootfs_payload(tagged, report)
        self.assertFalse(any("SECURE-BOOT GATE" in w for w in report.warnings))
        self.assertTrue(
            any("appended BCM FIT-header signature tag" in i for i in report.info)
        )

    def test_encrypted_bootfs_reports_mapper_path(self):
        # Inner FIT with a /brcm_rootfs_encrypt node: mapper path, no raw fallback
        kernel_fit = valid_inner_bootfs()
        # append an extra node is invasive; instead build via writer directly
        w = FdtWriter()
        w.begin_node("")
        w.property_string("description", "inner with encrypt")
        w.property_u32("#address-cells", 1)
        w.begin_node("images")
        w.begin_node("kernel-1")
        w.property("data", KERNEL)
        w.property_string("type", "kernel")
        w.end_node()
        w.end_node()
        w.begin_node("configurations")
        w.property_string("default", "conf_linux")
        w.begin_node("conf_linux")
        w.property_string("kernel", "kernel-1")
        w.end_node()
        w.end_node()
        w.begin_node("brcm_rootfs_encrypt")
        w.property_string("device", "/dev/ubiblock0_4")
        w.end_node()
        w.end_node()
        report = Report()
        validate_bootfs_payload(w.build(), report)
        self.assertTrue(
            any(
                "/brcm_rootfs_encrypt" in i and "declares" in i for i in report.info
            )
        )
        del kernel_fit

    def test_gled_vendor_bootfs_is_not_the_unsigned_gate(self):
        w = FdtWriter()
        w.begin_node("")
        w.property_string("description", "vendor-shaped")
        w.begin_node("brcm_rootfs_encrypt")
        w.property_string("device", "/dev/ubiblock0_4")
        w.end_node()
        w.end_node()
        report = Report()
        validate_bootfs_payload(w.build() + b"GLED" + b"\x00" * 8, report)
        self.assertFalse(any("SECURE-BOOT GATE" in x for x in report.warnings))
        self.assertTrue(any("GLED" in i for i in report.info))

    def test_non_fdt_bootfs_payload_warns(self):
        report = Report()
        validate_bootfs_payload(b"RAWVENDORBLOB", report)
        self.assertTrue(any("not an FDT" in w for w in report.warnings))

    def test_rootfs_data_valid_ubifs_magic(self):
        ubifs_data = b"\x31\x18\x10\x06" + b"SAMPLE-UBIFS-NODE-DATA"
        blob = build_standard_fit_skeleton(rootfs_data_component=ubifs_data)
        report = validate_bundle(blob)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("valid overlay volume format" in i for i in report.info))

    def test_rootfs_data_invalid_magic_warns(self):
        bad_data = b"NOTU" + b"SAMPLE-NON-UBIFS-DATA"
        blob = build_standard_fit_skeleton(rootfs_data_component=bad_data)
        report = validate_bundle(blob)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("rootfs_data does not start with UBIFS node magic" in w for w in report.warnings))

    def test_generated_overlay_injection_bundle_file_validates(self):
        bundle_path = Path(__file__).resolve().parent.parent / "artifacts" / "firmware" / "overlay-injection-bundle.itb"
        if not bundle_path.is_file():
            self.skipTest("overlay-injection-bundle.itb not generated yet")
        report = validate_bundle(bundle_path.read_bytes())
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])
        self.assertTrue(any("valid overlay volume format" in i for i in report.info))


if __name__ == "__main__":
    unittest.main()
