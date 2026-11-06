#!/usr/bin/env python3
"""Build and package a complete rootfs_data overlay injection FIT bundle for Telia F1 / GCNT-X.

End-to-end offline pipeline:
  1. Stages overlay hierarchy (ash on console in inittab, blank root shadow,
     rc.local telnetd fallback, clash/dropbear configs) via generate_f1_overlay.py.
  2. Compiles rootfs_data.ubifs using the macOS-native tools/bin/mkfs.ubifs binary
     with exact GCNT-X NAND flash parameters (min-io=4096, leb-size=253952, max-lebs=403).
  3. Packages rootfs_data into a valid Flattened Image Tree (FIT / ITB) bundle via
     build_f1_fit_skeleton.py, safely omitting unsigned bootfs/rootfs to bypass FLD secure boot.
  4. Validates structural and cryptographic integrity via validate_f1_fit_bundle.py.
  5. Computes SHA-256 hashes and verifies 0 errors and 0 warnings before output.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_f1_fit_skeleton import build_standard_fit_skeleton
from generate_f1_overlay import generate_overlay_staging
from validate_f1_fit_bundle import validate_bundle

DEFAULT_STAGING_DIR = REPO_ROOT / "artifacts" / "firmware" / "overlay_staging"
DEFAULT_MKFS_UBIFS = REPO_ROOT / "tools" / "bin" / "mkfs.ubifs"
DEFAULT_OUT_UBIFS = REPO_ROOT / "artifacts" / "firmware" / "rootfs_data.ubifs"
DEFAULT_OUT_FIT = REPO_ROOT / "artifacts" / "firmware" / "overlay-injection-bundle.itb"

# Broadcom BCM68360 NAND flash geometry for GCNT-X UBI volume 20 (rootfs_data)
# Verified from live boot logs (router-boot-20261027-010457-82769.log:1565-1568)
GCNT_X_MIN_IO_SIZE = 4096
GCNT_X_LEB_SIZE = 253952  # 248 KiB
GCNT_X_MAX_LEB_CNT = 403  # 97 MiB
GCNT_X_JOURNAL_SIZE = 1015808  # 1 MiB (4 LEBs) - ensures journal fits in dynamic UBI volume
GCNT_X_COMPRESSION = "zlib"


def build_overlay_bundle(
    staging_dir: Path = DEFAULT_STAGING_DIR,
    mkfs_ubifs_bin: Path = DEFAULT_MKFS_UBIFS,
    out_ubifs: Path = DEFAULT_OUT_UBIFS,
    out_fit: Path = DEFAULT_OUT_FIT,
    root_password: str = "",
    description: str = "F1 Bank 2 rootfs_data overlay injection bundle",
    skip_staging: bool = False,
) -> tuple[Path, Path, str, str]:
    """Run full overlay staging, UBIFS generation, FIT packaging, and validation.

    Returns (out_ubifs, out_fit, sha256_ubifs, sha256_fit).
    """
    # Step 1: Stage overlay tree
    if not skip_staging:
        staging_dir.mkdir(parents=True, exist_ok=True)
        generate_overlay_staging(
            staging_dir, password=root_password if root_password else None
        )
        # Create a 10 MiB padding file so U-Boot creates an adequately-sized dynamic UBI volume (>50 LEBs)
        pad_path = staging_dir / "pad.dat"
        if not pad_path.exists() or pad_path.stat().st_size != 10 * 1024 * 1024:
            pad_path.write_bytes(os.urandom(10 * 1024 * 1024))

    # Step 2: Validate mkfs.ubifs binary
    if not mkfs_ubifs_bin.is_file():
        raise FileNotFoundError(
            f"mkfs.ubifs binary not found at {mkfs_ubifs_bin}. "
            f"Run tools/patches/build_mkfs_ubifs_macos.sh or compile mtd-utils."
        )

    # Step 3: Run mkfs.ubifs
    out_ubifs.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(mkfs_ubifs_bin),
        "-r",
        str(staging_dir),
        "-m",
        str(GCNT_X_MIN_IO_SIZE),
        "-e",
        str(GCNT_X_LEB_SIZE),
        "-c",
        str(GCNT_X_MAX_LEB_CNT),
        "-j",
        str(GCNT_X_JOURNAL_SIZE),
        "-x",
        GCNT_X_COMPRESSION,
        "-F",  # free-space fixup on first mount
        "-U",  # squash uids to root (0:0)
        "-o",
        str(out_ubifs),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"mkfs.ubifs failed with exit code {res.returncode}:\n{res.stderr}\n{res.stdout}"
        )

    ubifs_bytes = out_ubifs.read_bytes()
    if len(ubifs_bytes) < 4 or ubifs_bytes[:4] != b"\x31\x18\x10\x06":
        raise ValueError(
            f"Generated UBIFS image at {out_ubifs} lacks valid UBIFS magic (0x06101831)"
        )

    sha256_ubifs = hashlib.sha256(ubifs_bytes).hexdigest()

    # Step 4: Package into standard FIT bundle
    out_fit.parent.mkdir(parents=True, exist_ok=True)
    fit_blob = build_standard_fit_skeleton(
        rootfs_data_component=ubifs_bytes,
        description=description,
        board="GCNT-X",
    )
    out_fit.write_bytes(fit_blob)
    sha256_fit = hashlib.sha256(fit_blob).hexdigest()

    # Step 5: Validate the FIT bundle
    report = validate_bundle(fit_blob)
    if report.errors:
        raise ValueError(
            f"Generated FIT bundle failed structural validation:\n"
            + "\n".join(f"  ERROR: {e}" for e in report.errors)
        )
    if report.warnings:
        raise ValueError(
            f"Generated FIT bundle has unexpected validation warnings:\n"
            + "\n".join(f"  WARNING: {w}" for w in report.warnings)
        )

    return out_ubifs, out_fit, sha256_ubifs, sha256_fit


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and package rootfs_data overlay injection FIT bundle for Telia F1"
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
        help="Path to overlay staging directory",
    )
    parser.add_argument(
        "--mkfs-ubifs",
        type=Path,
        default=DEFAULT_MKFS_UBIFS,
        help="Path to mkfs.ubifs executable",
    )
    parser.add_argument(
        "--out-ubifs",
        type=Path,
        default=DEFAULT_OUT_UBIFS,
        help="Output path for UBIFS filesystem image",
    )
    parser.add_argument(
        "--out-fit",
        type=Path,
        default=DEFAULT_OUT_FIT,
        help="Output path for FIT bundle",
    )
    parser.add_argument(
        "--root-password",
        type=str,
        default="",
        help="Root password (default: empty string for passwordless root)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="F1 Bank 2 rootfs_data overlay injection bundle",
        help="FIT image description",
    )
    parser.add_argument(
        "--skip-staging",
        action="store_true",
        help="Skip re-generating staging directory contents",
    )

    args = parser.parse_args()

    try:
        ubifs_path, fit_path, sha_ubifs, sha_fit = build_overlay_bundle(
            staging_dir=args.staging_dir,
            mkfs_ubifs_bin=args.mkfs_ubifs,
            out_ubifs=args.out_ubifs,
            out_fit=args.out_fit,
            root_password=args.root_password,
            description=args.description,
            skip_staging=args.skip_staging,
        )
        print("[+] SUCCESS: Overlay injection pipeline complete.")
        print(f"    UBIFS Image: {ubifs_path} ({ubifs_path.stat().st_size:,} bytes)")
        print(f"    UBIFS SHA256: {sha_ubifs}")
        print(f"    FIT Bundle:  {fit_path} ({fit_path.stat().st_size:,} bytes)")
        print(f"    FIT SHA256:  {sha_fit}")
        print("    Validation:  0 errors, 0 warnings (100% verified)")
        return 0
    except Exception as e:
        print(f"[-] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
