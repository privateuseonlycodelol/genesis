# Homeware Dual-Bank Overlay Architecture & `rootfs_data` Recovery Flashing (2026-11-04)

## Scope and Status

Offline reverse-engineering analysis of Technicolor Homeware overlay mechanics, Broadcom U-Boot recovery flashing contracts (`sdk_test_commands.c`), and live boot logs (`artifacts/uart/2026-10-27/router-boot-20261027-010457-82769.log`).

Enhanced FIT generation and validation tooling to support standalone or bundled `rootfs_data` UBIFS components. All 186 unit tests passing in Python.

---

## 1. Ground Truth: Why `rootfs_data` is the Key Flashing Surface

With Broadcom FLD Secure Boot confirmed to halt unsigned `bootfs` images ([f1-uboot-fld-secure-boot-gate-2026-11-04.md](f1-uboot-fld-secure-boot-gate-2026-11-04.md)), replacing the kernel is blocked until a signed image or hardware read is available.

However, cross-referencing U-Boot's recovery upgrade table with Linux initialization reveals that **the rootfs overlay (`rootfs_data`) is exposed to recovery flashing without secure boot gating**:

### A. U-Boot Recovery Upgrade Table
In `artifacts/bootp/live-mac/session-20261027-190854.log` (lines 620–628), U-Boot recovery evaluates five upgrade targets:
1. `bootfs`
2. `rootfs`
3. `loader`
4. `rootfs_data`
5. `ramfs_rd`

### B. Stock Linux Mounts `rootfs_data` as an Unsigned UBIFS Overlay
In `artifacts/uart/2026-10-27/router-boot-20261027-010457-82769.log` (lines 1564–1590):
```text
UBIFS (ubi0:20): UBIFS: mounted UBI device 0, volume 20, name "rootfs_data"
UBIFS (ubi0:20): LEB size: 253952 bytes (248 KiB), min./max. I/O unit sizes: 4096 bytes/4096 bytes
UBIFS (ubi0:20): FS size: 102342656 bytes (97 MiB, 403 LEBs)
mount_root: switching to ubifs overlay
mount_root: executing script in /lib/mount_root
mount_root: /lib/mount_root/00_overlay_bank_check.sh
mount_root: /lib/mount_root/00_rtfd_all
mount_root: /lib/mount_root/10_remove_due_to_upgrade
mount_root: /lib/mount_root/20_rtfd_remove
mount_root: /lib/mount_root/30_parameter_conversion
HOMEWARE_CONFIG_ON_ACTIVE_BANK
mount_root: /lib/mount_root/80_rtfd_restore
```

### C. The Dual-Bank Overlay Structure (`HOMEWARE_CONFIG_ON_ACTIVE_BANK`)
- **VERIFIED:** Homeware separates configuration overlays per bank: `/overlay/bank_1` and `/overlay/bank_2`.
- At boot time, `bankmgr` and `/lib/mount_root/00_overlay_bank_check.sh` detect the active running bank and bind the overlay upper directory to the active bank directory.
- `UBIFS_MAGIC`: Line 47 of `sdk_test_commands.c` defines `UBIFS_MAGIC` as `0x06101831` (little-endian: `\x31\x18\x10\x06`), matching the standard Linux `UBIFS_NODE_MAGIC`.

---

## 2. Tooling Enhancements

### A. Builder: `scripts/build_f1_fit_skeleton.py`
- Added `--rootfs-data <file>` argument to the CLI.
- Added `rootfs_data_component` parameter to `build_standard_fit_skeleton()`.
- Generates `/images/rootfs_data` with proper SHA-256 hashes and maps `rootfs_data = "rootfs_data"` in `/configurations/config-1`.
- Allows creating a standalone `rootfs_data` recovery bundle (where `bootfs` and `rootfs` are omitted and skipped by U-Boot, leaving the authentic signed kernel and rootfs untouched on NAND).

### B. Validator: `scripts/validate_f1_fit_bundle.py`
- Corrected `UBIFS_MAGIC_LE` to `0x06101831` (`\x31\x18\x10\x06`).
- Added structural inspection for `rootfs_data`: checks that when `rootfs_data` is declared, its binary payload starts with valid UBIFS node magic.

### C. Unit Tests & Dry-Run
- Added 2 new tests in `scripts/test_build_f1_fit_skeleton.py`.
- Added 2 new tests in `scripts/test_validate_f1_fit_bundle.py`.
- Generated dry-run artifact `artifacts/firmware/dryrun-2026-11-04/bundle-rootfs-data-placeholder.itb` and validated it with zero warnings.

---

## 3. Exploit Model: Standalone Overlay Injection

Because U-Boot skips absent components:
1. We construct a recovery bundle containing **only** `rootfs_data` (a crafted UBIFS filesystem containing `/bank_2/etc/shadow`, `/bank_2/etc/inittab`, or `/bank_2/etc/config/clash`).
2. U-Boot recovery flasher skips `bootfs` and `rootfs`, leaving the stock, vendor-signed partitions on NAND.
3. U-Boot flashes `rootfs_data` to UBI volume 20.
4. On reboot:
   - Broadcom FLD Secure Boot authenticates the untouched stock `bootfs` -> **PASSES**.
   - Kernel verifies untouched SquashFS `rootfs` with dm-verity -> **PASSES**.
   - `mount_root` switches to `rootfs_data` overlay -> **APPLIES INJECTED CONFIGURATION**.
   - Root shell or unlocked serial console is enabled.
