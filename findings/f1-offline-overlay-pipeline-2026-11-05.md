# Offline Rootfs Overlay Injection Pipeline & macOS Toolchain (2026-11-05)

## Scope and status

Offline reverse-engineering, toolchain development, and artifact packaging pass.
No physical router intervention, no live network traffic, no flash writes performed.
All work executed locally on macOS host; **192 unit tests passing** across the repository test suite.

---

## 1. Executive Summary

In previous sessions, we established two critical facts:
1. **Unsigned `bootfs` is DEAD on this hardware:** The live Telia F1 unit operates in Broadcom FLD Secure Boot mode (`board_secure.c`). Attempting to flash an unsigned or self-compiled kernel triggers an unrecoverable `bcm_sec_abort()` infinite loop (`findings/f1-uboot-fld-secure-boot-gate-2026-11-04.md`).
2. **Selective Component Flashing:** Broadcom U-Boot's `flash_upgrade_img_bundle()` loops over `fn_table`: `bootfs`, `rootfs`, `loader`, `rootfs_data`, `ramfs_rd`. If `bootfs` and `rootfs` are omitted from `/configurations/config-1`, U-Boot logs `... not found in configuration config-1 ...skipping!`, leaving the vendor-signed authentic kernel and rootfs untouched on NAND, while writing only the present `rootfs_data` component to UBI volume 20 (`findings/f1-rootfs-data-overlay-flashing-2026-11-04.md`).

In this session, we completed the **entire offline exploit pipeline natively on macOS without external VM or Docker dependencies**:
- Ported `mkfs.ubifs` from Linux `mtd-utils` to macOS Darwin via a lightweight C compatibility layer.
- Staged the full dual-bank Homeware overlay hierarchy (`/bank_1`, `/bank_2`, `/`) targeting serial console, root shadow, telnet fallback, and network access.
- Compiled the binary `rootfs_data.ubifs` matching exact Broadcom BCM68360 NAND geometry.
- Packaged the standalone recovery FIT bundle `artifacts/firmware/overlay-injection-bundle.itb`.
- Validated structural integrity, FDT schema, SHA-256 hashes, and verified 0 errors and 0 warnings.
- Automated the entire workflow into a single turnkey command: `scripts/build_f1_overlay_bundle.py`.

---

## 2. macOS Native `mkfs.ubifs` Toolchain

### A. The Challenge
`mtd-utils` has historically been tightly coupled to Linux kernel UAPI headers (`<linux/types.h>`, `<linux/fs.h>`, `<sys/sysmacros.h>`, `<byteswap.h>`), making native compilation on macOS Darwin notoriously difficult and forcing researchers into Docker containers or Linux VMs.

### B. The Darwin Compatibility Patch (`tools/patches/mtd-utils-macos.patch`)
We engineered a clean compatibility shim addressing all Linux-specific constructs:
1. **Types & Byteorder:** Mapped `__u8`..`__u64`, `__s8`..`__s64`, `__le16`..`__le64`, and `loff_t` to standard POSIX `<stdint.h>`, `<sys/types.h>`, and Darwin `<libkern/OSByteOrder.h>`. Utilized compiler builtin macros (`__BYTE_ORDER__`, `__ORDER_LITTLE_ENDIAN__`) for robust endianness resolution.
2. **Device Macros:** Guarded `<sys/sysmacros.h>` and mapped `major()`/`minor()` to `<sys/types.h>`.
3. **File Attributes:** Provided fallback definitions for Linux-specific ioctls (`FS_IOC_GETFLAGS`) and file attribute flags (`FS_COMPR_FL`, `FS_IMMUTABLE_FL`, `FS_POLICY_FLAGS_PAD_*`), gracefully falling back on Darwin host filesystems.
4. **Header Interactions:** Resolved a clang preprocessor collision where defining `fallthrough` conflicted with Apple's `<os/base.h>` inside `<execinfo.h>`.
5. **Bitwise Builtins:** Guarded conflicting non-static `fls(int)` declaration against Darwin's `<strings.h>`.
6. **Errno:** Defined missing Linux `EUCLEAN` (117).

### C. Build Automation (`tools/patches/build_mkfs_ubifs_macos.sh`)
Automated the clone, patch, and build into a single script:
```bash
./tools/patches/build_mkfs_ubifs_macos.sh
```
Installs the native standalone binary to `tools/bin/mkfs.ubifs` (ignored in `.gitignore`).

---

## 3. NAND Geometry & Overlay Generation

### A. Ground-Truth Hardware Parameters
Extracted from live router UART boot logs (`artifacts/uart/2026-10-27/router-boot-20261027-010457-82769.log:1565-1568`):
- **Minimum I/O size (`-m`):** `4096` bytes
- **Logical Erase Block (`-e`):** `253952` bytes (248 KiB)
- **Max LEB Count (`-c`):** `403` (~97 MiB)
- **Journal Size (`-j`):** `5079040` bytes (20 LEBs)
- **Compression (`-x`):** `zlib`
- **Superblock / Node Magic:** `0x06101831` (little-endian: `\x31\x18\x10\x06`)

### B. Overlay Staging Tree (`scripts/generate_f1_overlay.py`)
Populated into `artifacts/firmware/overlay_staging/` across `bank_1/`, `bank_2/`, and root:
- `etc/inittab`: Spawns unauthenticated login shell on console: `::askconsole:/bin/ash --login` (bypassing Homeware `restricted_shell` and `clash-access-control`).
- `etc/passwd`: Standard root user: `root:x:0:0:root:/root:/bin/ash`.
- `etc/shadow`: Empty root password (`root::18000:0:99999:7:::`), allowing immediate root access without credentials.
- `etc/rc.local`: Starts background telnet daemon on LAN port 23: `busybox telnetd -l /bin/ash -p 23 &`.
- `etc/config/clash`: Sets `config access 'serial'` enabled for root.
- `etc/config/dropbear`: Enables SSH password authentication on LAN.

---

## 4. End-to-End Pipeline & Artifacts

### A. Turnkey Script (`scripts/build_f1_overlay_bundle.py`)
Single command to run the entire pipeline:
```bash
./tools/venv/bin/python3 scripts/build_f1_overlay_bundle.py
```

### B. Generated Offline Artifacts
- **UBIFS Overlay Image:**
  - Path: `artifacts/firmware/rootfs_data.ubifs`
  - Size: 3,301,376 bytes
  - SHA-256: `91f84d2b1010b99da3f1f4c63d08d1bb10328f0ee48854b9e81193e94e9891e9`
  - Magic: `\x31\x18\x10\x06` (verified)
- **FIT Injection Bundle:**
  - Path: `artifacts/firmware/overlay-injection-bundle.itb`
  - Size: 3,302,553 bytes
  - SHA-256: `9b69b5ebe1b628e0ed3730c9f37f981c51cea4689cbcb5ccd4ed87d7fbd42893`
  - Format: Flattened Device Tree v17 (magic `0xd00dfeed`)

### C. Bundle Validation (`scripts/validate_f1_fit_bundle.py`)
```text
INFO  selected configuration: config-1
INFO  config compatible: 'GCNT-X'
INFO  fn_table member 'bootfs' absent from config: U-Boot logs 'INFO: bootfs not found in configuration config-1 ...skipping!'
INFO  fn_table member 'rootfs' absent from config: U-Boot logs 'INFO: rootfs not found in configuration config-1 ...skipping!'
INFO  fn_table member 'loader' absent from config: U-Boot logs 'INFO: loader not found in configuration config-1 ...skipping!'
INFO  fn_table member 'rootfs_data' -> image /images/rootfs_data
INFO  fn_table member 'ramfs_rd' absent from config: U-Boot logs 'INFO: ramfs_rd not found in configuration config-1 ...skipping!'
INFO  rootfs_data starts with UBIFS node magic (0x06101831): valid overlay volume format

RESULT: STRUCTURALLY VALID (0 warning(s), 8 info)
```

---

## 5. Exploit Execution Contract (When Router Access is Ready)

When authorized live router testing begins:
1. Connect Mac Ethernet to F1 LAN port 1 and UART USB-TTL adapter to router debug header (`ttyS0`, 115200 8N1).
2. Execute the single-process recovery server:
   ```bash
   sudo ./tools/venv/bin/python3 scripts/f1_bootp_tftp_mac.py \
     --iface en4 \
     --uart /dev/cu.usbserial-0001 \
     --file artifacts/firmware/overlay-injection-bundle.itb
   ```
3. Power-cycle router.
4. Expected device behavior:
   - Automated press of `b` at U-Boot BOOT-P countdown.
   - U-Boot sends BOOTREQUEST, receives BOOTREPLY, fetches `overlay-injection-bundle.itb` via TFTP.
   - `flash_upgrade_img_bundle()` verifies hashes, skips `bootfs` and `rootfs`, and flashes `rootfs_data` to UBI vol 20.
   - Router reboots into stock signed Bank 2 kernel.
   - Kernel mounts injected UBIFS overlay on `/overlay/bank_2`.
   - Serial console drops directly into passwordless root shell (`/bin/ash`).
   - Telnet daemon listens on LAN port 23.

---

## 6. What Was NOT Shown (Negative Boundaries)

- **NOT shown:** Live router flashing was **not** performed in this session. All validation is structural and offline.
- **NOT shown:** We have not bypassed Broadcom FLD secure boot on the kernel itself; our exploit specifically evades the secure-boot gate by preserving the authentic signed kernel and flashing only the unsigned overlay partition.
