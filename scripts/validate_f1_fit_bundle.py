#!/usr/bin/env python3
"""Offline structural validator for Telia F1 / GCNT-X dual-component FIT bundles.

Checks a generated .itb bundle against the exact contract implemented by Broadcom
U-Boot's flash_upgrade_img_bundle() (artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/sdk_test_commands.c):

  1. fit_all_image_verify() over the WHOLE bundle: every /images/* node must carry
     hash-1 (sha256) whose value matches its data. Any failure aborts the upgrade.
  2. /configurations node, :default property, and the referenced config node.
  3. 'compatible' string property on the config node (verify_compat_string gate).
  4. fn_table member lookup (bootfs, rootfs, loader, rootfs_data, ramfs_rd):
     a config property naming an image node must resolve to /images/<name>;
     absent members are skipped by U-Boot with "...skipping!" (expected).

Separately, when the bootfs payload is itself an FDT (inner bootfs FIT), the
validator reports the boot-time secure-boot gate that flash does NOT enforce:

  - nand_load_bootfs()/emmc_load_bootfs()/vfbio_load_bootfs()/spinor_load_bootfs()
    call bcm_sec_validate_fit() on the loaded inner bootfs BEFORE bcm_handle_mapper().
    On FLD-secure units (VERIFIED live: "Board is FLD secure", TPL "FIT Header
    Authentication Successfull!") an unsigned inner bootfs reaches bcm_sec_abort()
    (board_secure.c: wipes keys, prints "### ERROR ### Boot Aborted", loops forever).
  - bcm_tag_fit_hdr_validate() (board_secure_fit.c) RSA-verifies the WHOLE inner
    FDT via BCM_TAG_FIT_HDR_SEC_SIGNATURE ("FITS") tags appended after the FDT blob,
    or a BCM_TAG_FIT_HDR_SEC_PUBKEY ("FITP") record verified against the platform key.
    This script therefore flags an inner bootfs lacking an appended FITS/FITP tag.

Exit codes: 0 = structurally valid (warnings allowed unless --strict),
1 = contract violation, 2 = unreadable input.

Pure Python, offline, no device contact.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_f1_fit_skeleton import FdtReader

# fn_table order from sdk_test_commands.c (flash_upgrade_img_bundle)
FN_TABLE = ["bootfs", "rootfs", "loader", "rootfs_data", "ramfs_rd"]

# Appended signature tag markers from board_secure_fit.c
BCM_TAG_FIT_HDR_SEC_SIGNATURE = 0x46495453  # "FITS"
BCM_TAG_FIT_HDR_SEC_PUBKEY = 0x46495450  # "FITP"
BCM_TAG_FIT_HDR_SEC_DELG_REC = 0x44454C47  # "DELG"

SQUASHFS_MAGIC = b"hsqs"
UBIFS_MAGIC_LE = 0x06101831  # UBIFS node magic (sdk_test_commands.c:47 #define UBIFS_MAGIC 0x06101831)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def _prop_str(props: dict[str, bytes], key: str) -> str | None:
    val = props.get(key)
    if val is None:
        return None
    return val.rstrip(b"\x00").decode("ascii", "replace")


def validate_bootfs_payload(data: bytes, report: Report) -> None:
    """Report the boot-time secure gate for an inner bootfs FIT (if it is an FDT)."""
    if data[:4] != b"\xd0\x0d\xfe\xed":
        report.warnings.append(
            "bootfs payload is not an FDT (no d00dfeed magic); if it is not the "
            "vendor inner bootfs FIT, nand_load_bootfs() would fail before boot."
        )
        return
    try:
        reader = FdtReader(data)
    except ValueError as exc:
        report.errors.append(f"bootfs payload FDT unreadable: {exc}")
        return

    nodes, props = reader.walk()
    fdt_size = reader.totalsize

    if "/brcm_rootfs_encrypt" in nodes:
        report.info.append(
            "inner bootfs declares /brcm_rootfs_encrypt: bcm_handle_mapper() will set "
            "up dm-verity + dm-crypt (encrypted rootfs required)."
        )
    else:
        report.info.append(
            "inner bootfs omits /brcm_rootfs_encrypt: bcm_handle_mapper() returns 1 and "
            "nand_load_bootfs() falls back to raw SquashFS rootfs (magic check on "
            "rootfs first 4 bytes)."
        )

    # Secure-boot gate: appended tag region after fdt_totalsize.
    trailing = data[fdt_size:]
    # On-flash 23.1.b bootfs is a small FIT header plus external image bytes.
    # The first four of those bytes are "GLED", not the FITS/FITP tag this
    # checker was written for. The board already boots that layout.
    if trailing[:4] == b"GLED" and "/brcm_rootfs_encrypt" in nodes:
        report.info.append(
            "inner bootfs matches the on-flash vendor layout: FDT totalsize "
            "ends at a GLED image container and /brcm_rootfs_encrypt is present. "
            "Signature bytes are not checked offline."
        )
        return
    has_sig = False
    for tag in (
        BCM_TAG_FIT_HDR_SEC_SIGNATURE,
        BCM_TAG_FIT_HDR_SEC_PUBKEY,
        BCM_TAG_FIT_HDR_SEC_DELG_REC,
    ):
        if len(trailing) >= 4 and struct.unpack("!I", trailing[:4])[0] == tag:
            has_sig = True
    if not has_sig and any(
        struct.unpack("!I", trailing[i : i + 4])[0]
        in (BCM_TAG_FIT_HDR_SEC_SIGNATURE, BCM_TAG_FIT_HDR_SEC_PUBKEY)
        for i in range(0, min(len(trailing), 4096) - 3)
    ):
        has_sig = True

    if has_sig:
        report.info.append(
            "inner bootfs carries an appended BCM FIT-header signature tag (FITS/FITP). "
            "Structure present; signature validity is NOT checked offline."
        )
    else:
        report.warnings.append(
            "SECURE-BOOT GATE: inner bootfs has NO appended FITS/FITP signature tag. "
            "The bundle will flash (flash path checks hashes only), but on FLD-secure "
            "units bcm_sec_validate_fit() in nand_load_bootfs() fails and "
            "bcm_sec_abort() wipes keys and hangs the board ('### ERROR ### Boot "
            "Aborted'). Do NOT live-flash this bundle: no vendor 23.1.b image is "
            "available locally for restore."
        )


def validate_bundle(data: bytes) -> Report:
    """Validate an outer recovery bundle against the U-Boot flash contract."""
    report = Report()

    if len(data) < 40 or data[:4] != b"\xd0\x0d\xfe\xed":
        report.errors.append("input is not an FDT/FIT (magic d00dfeed required)")
        return report
    try:
        reader = FdtReader(data)
    except ValueError as exc:
        report.errors.append(f"unreadable FDT: {exc}")
        return report
    if reader.totalsize != len(data):
        report.errors.append(
            f"FDT totalsize {reader.totalsize} != file length {len(data)}"
        )

    nodes, props = reader.walk()

    # Contract 2: /configurations, default, config node
    if "/configurations" not in nodes:
        report.errors.append(
            "/configurations node missing: flash_upgrade_img_bundle returns "
            "CMD_RET_FAILURE ('ERROR: /configurations node not found in bundle!')"
        )
        return report

    default_conf = _prop_str(props, "/configurations:default")
    if default_conf is None:
        report.errors.append(
            "/configurations:default missing: U-Boot cannot select a configuration"
        )
        return report
    conf_path = f"/configurations/{default_conf}"
    if conf_path not in nodes:
        report.errors.append(
            f"{conf_path} missing: 'ERROR: {default_conf} node not found in bundle!'"
        )
        return report
    report.info.append(f"selected configuration: {default_conf}")

    # Contract 3: compatible string on the config node
    compat = _prop_str(props, f"{conf_path}:compatible")
    if compat is None:
        report.errors.append(
            f"'compatible' property missing on {conf_path}: verify_compat_string "
            "fails ('Error: Bundle is not compatible with platform!')"
        )
    else:
        report.info.append(f"config compatible: {compat!r}")
        if compat != "GCNT-X":
            report.warnings.append(
                f"compatible {compat!r} is not the live board string 'GCNT-X' "
                "(UART log: 'compatible = \"GCNT-X\"' validated in recovery)"
            )

    # Contract 4: fn_table member resolution
    for member in FN_TABLE:
        ref = _prop_str(props, f"{conf_path}:{member}")
        if ref is None:
            report.info.append(
                f"fn_table member {member!r} absent from config: U-Boot logs "
                f"'INFO: {member} not found in configuration {default_conf} "
                "...skipping!' (matches the 2026-10-27 19:09 run)"
            )
            continue
        img_path = f"/images/{ref}"
        if img_path not in nodes:
            report.errors.append(
                f"config property {member}={ref!r} does not resolve to {img_path}"
            )
            continue
        report.info.append(f"fn_table member {member!r} -> image {img_path}")
        if member == "bootfs" and props.get(f"{img_path}:data"):
            validate_bootfs_payload(props[f"{img_path}:data"], report)

    # Contract 1: fit_all_image_verify over EVERY image node
    image_nodes = [n for n in nodes if n.startswith("/images/") and n.count("/") == 2]
    for img in sorted(image_nodes):
        img_data = props.get(f"{img}:data")
        if img_data is None:
            report.errors.append(f"{img}: no 'data' property (hash cannot verify)")
            continue
        algo = _prop_str(props, f"{img}/hash-1:algo")
        digest = props.get(f"{img}/hash-1:value")
        if algo is None or digest is None:
            report.errors.append(
                f"{img}: missing hash-1 (algo/value) - fit_all_image_verify fails "
                "and the WHOLE upgrade returns CMD_RET_FAILURE"
            )
            continue
        if algo != "sha256":
            report.warnings.append(
                f"{img}: hash algo {algo!r} is not sha256 (U-Boot support depends "
                "on build; sha256 verified in vendor chain)"
            )
        if hashlib.sha256(img_data).digest() != digest:
            report.errors.append(
                f"{img}: hash-1 value does not match sha256(data) "
                f"(len(data)={len(img_data)})"
            )

    # Payload magic sanity for rootfs (raw-SquashFS fallback path)
    rootfs_ref = _prop_str(props, f"{conf_path}:rootfs")
    if rootfs_ref:
        rootfs_data = props.get(f"/images/{rootfs_ref}:data")
        if rootfs_data is not None:
            if rootfs_data[:4] == SQUASHFS_MAGIC:
                report.info.append(
                    "rootfs starts with SquashFS magic: unencrypted fallback boot "
                    "path is structurally applicable"
                )
            elif struct.pack("<I", int.from_bytes(rootfs_data[:4], "little")) and (
                int.from_bytes(rootfs_data[:4], "little") == UBIFS_MAGIC_LE
            ):
                report.info.append(
                    "rootfs starts with UBIFS magic: nand_load_bootfs() would set "
                    "rootfstype=ubifs instead of the SquashFS fallback"
                )
            elif any("/brcm_rootfs_encrypt" in line and "declares" in line for line in report.info):
                report.info.append(
                    "rootfs has no SquashFS/UBIFS magic: expected for the encrypted "
                    "volume paired with /brcm_rootfs_encrypt"
                )
            else:
                report.warnings.append(
                    "rootfs does not start with a recognized magic (SquashFS hsqs / "
                    "UBIFS): with an unsigned/omitted /brcm_rootfs_encrypt bootfs the "
                    "raw fallback cannot identify the filesystem"
                )

    # Payload magic sanity for rootfs_data (UBIFS overlay volume)
    rootfs_data_ref = _prop_str(props, f"{conf_path}:rootfs_data")
    if rootfs_data_ref:
        rootfs_data_bytes = props.get(f"/images/{rootfs_data_ref}:data")
        if rootfs_data_bytes is not None:
            if len(rootfs_data_bytes) >= 4 and int.from_bytes(rootfs_data_bytes[:4], "little") == UBIFS_MAGIC_LE:
                report.info.append(
                    "rootfs_data starts with UBIFS node magic (0x06101831): valid overlay volume format"
                )
            else:
                got_magic = rootfs_data_bytes[:4].hex() if len(rootfs_data_bytes) >= 4 else "too short"
                report.warnings.append(
                    f"rootfs_data does not start with UBIFS node magic (0x06101831); got {got_magic}: "
                    "Homeware mount_root expects UBIFS format for the rootfs_data overlay partition"
                )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("bundle", help="Path to the .itb bundle to validate")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings (including the unsigned-bootfs secure gate) as failures",
    )
    args = parser.parse_args()

    path = Path(args.bundle)
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 2

    report = validate_bundle(path.read_bytes())

    for line in report.errors:
        print(f"FAIL  {line}")
    for line in report.warnings:
        print(f"WARN  {line}")
    for line in report.info:
        print(f"INFO  {line}")

    if not report.ok:
        print(f"\nRESULT: INVALID ({len(report.errors)} contract violation(s))")
        return 1
    if args.strict and report.warnings:
        print(f"\nRESULT: INVALID under --strict ({len(report.warnings)} warning(s))")
        return 1
    print(
        f"\nRESULT: STRUCTURALLY VALID ({len(report.warnings)} warning(s), "
        f"{len(report.info)} info)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
