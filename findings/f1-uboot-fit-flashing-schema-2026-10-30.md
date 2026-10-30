# Broadcom U-Boot FIT Bundle Schema & Unencrypted Bootfs Architecture (2026-10-30)

## Scope and status

Offline reverse-engineering analysis of Broadcom U-Boot source code (`artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/sdk_test_commands.c`, `bcm_bootstate.c`) and live UART recovery session logs (`artifacts/bootp/live-mac/session-20261027-190854.log`).
No physical router intervention, no live flash writes. All tests verified offline with 166 passing unit tests in Python.

---

## 1. Ground Truth: Why BOOTP Flashing Skipped Components in Earlier Runs

In the 2026-10-27 live recovery session (`session-20261027-190854.log`), the BOOTP/TFTP responder successfully delivered `test-fit-standard.itb` to U-Boot recovery at `0x01000000`, but U-Boot logged:
```text
INFO: bootfs not found in configuration config-1 ...skipping!
flash_upgrade_img_bundle 3244> bootfs 
INFO: rootfs not found in configuration config-1 ...skipping!
flash_upgrade_img_bundle 3244> rootfs 
INFO: loader not found in configuration config-1 ...skipping!
flash_upgrade_img_bundle 3244> loader 
INFO: rootfs_data not found in configuration config-1 ...skipping!
flash_upgrade_img_bundle 3244> rootfs_data 
INFO: ramfs_rd not found in configuration config-1 ...skipping!
flash_upgrade_img_bundle 3244> ramfs_rd 
INFO: Image upgrade successfull!!
```

### Root Cause Analysis (`sdk_test_commands.c:2692-2718`)
- **VERIFIED (source):** U-Boot evaluates `fn_table`:
  ```c
  static flashfn_table_entry fn_table[] = {
      { "bootfs", flash_bootfs },
      { "rootfs", flash_rootfs },
      { "loader", flash_loader },
      // ...
  };
  ```
- In `flash_upgrade_img_bundle()`:
  ```c
  for (i = 0; i < max_entries && !err; i++) {
      if (get_binary_from_bundle(bundle_addr, conf_name, fn_table[i].name, &bin_name, &addr, &size)) {
          continue;
      }
      err = fn_table[i].func(addr, size, img_index);
  }
  ```
- `get_binary_from_bundle()` queries `/configurations/<conf_name>` (default `config-1`) specifically for properties named after the table entries (`bootfs`, `rootfs`, etc.).
- In earlier FIT skeleton iterations, the configuration node contained standard U-Boot `kernel = "kernel-1"` and omitted `bootfs`. As a result, U-Boot could not locate the component name and skipped the write.
- When all entries are skipped, `err` remains `0`. U-Boot prints `INFO: Image upgrade successfull!!`, advances the bank metadata in `metadata1` and `metadata2`, and resets without writing any partition bytes.

---

## 2. Partition Geometry & NAND Flash Targeting

- **VERIFIED (source, `sdk_test_commands.c:1170-1260`):**
  - For Bank 1 (`img_index == 1`):
    - `bootfs_volid = IMAGE_VOL_ID_1` = **3** (`bootfs1`)
    - `rootfs_volid = IMAGE_VOL_ID_1 + 1` = **4** (`rootfs1`)
  - For Bank 2 (`img_index == 2`):
    - `bootfs_volid = IMAGE_VOL_ID_2` = **5** (`bootfs2`)
    - `rootfs_volid = IMAGE_VOL_ID_2 + 1` = **6** (`rootfs2`)
- **Flashing mechanics:**
  - `flash_bootfs_nand()` checks if `bootfs<N>` exists; if so, removes it and creates a static UBI volume:
    `ubi create bootfs<N> <size> static <bootfs_volid>`
    `ubi write <addr> bootfs<N> <size>`
  - `flash_rootfs_nand()` checks if `rootfs<N>` exists; if so, removes it and creates a dynamic UBI volume:
    `ubi create rootfs<N> <size> dynamic <rootfs_volid>`
    `ubi write <addr> rootfs<N> <size>`
  - Neither function verifies RSA signatures or cryptographic HMACs before writing to flash. They write raw payload bytes.

---

## 3. The `dm-verity` & `dm-crypt` Decoupling Architecture

In standard firmware boot, the Linux kernel command line mounts a complex device-mapper tree:
`lroot: 0 108184 verity 1 /dev/ubiblock0_6 /dev/ubiblock0_6 512 512 108184 108185 sha256 <digest> <salt> 1 check_at_most_once`
`lroot2: 0 108184 crypt aes-xts-plain64 <key> 0 /dev/dm-0 0`

### Discovery in `bcm_handle_mapper()` (`sdk_test_commands.c:1490-1560`)
- **VERIFIED (source):** The entire device-mapper specification is read at boot time from the **`bootfs` FIT image**:
  ```c
  off = fdt_path_offset(fit, "/brcm_rootfs_encrypt");
  if (off < 0) {
      return(1);
  }
  ```
- If `/brcm_rootfs_encrypt` is **omitted** from `bootfs`:
  1. `bcm_handle_mapper()` returns `1`.
  2. `nand_load_bootfs()` falls back to reading the first 4 bytes of `rootfs<N>`:
     ```c
     ubi read %px rootfs%d 4
     ```
  3. If magic matches `SQUASHFS_MAGIC` (`0x73717368`):
     ```c
     env set -f rootfs_opts root=/dev/ubiblock0_<rootfs_volid> ubi.mtd=image ubi.block=0,<rootfs_volid> rootfstype=squashfs
     ```
  4. Broadcom U-Boot executes `bootm` pointing directly to `/dev/ubiblock0_<rootfs_volid>` **with NO dm-verity and NO dm-crypt**!
- **Architectural Implication:** You do not need to construct a valid `dm-verity` hash tree or encrypt rootfs with the L598 AES-XTS key if you control or provide `bootfs` without `/brcm_rootfs_encrypt`.

---

## 4. Tooling Enhancements (`scripts/build_f1_fit_skeleton.py`)

1. **`build_standard_fit_skeleton()`:**
   - Added `bootfs_data: bytes | None = None` support.
   - When provided, creates `/images/bootfs` (`type = "firmware"`, `arch = "arm64"`, `os = "linux"`, sha256 `hash-1`).
   - Populates `/configurations/config-1` with `bootfs = "bootfs"`, matching U-Boot's exact `fn_table` member lookup.
   - Preserves `rootfs = "rootfs"` targeting for SquashFS dynamic volumes.
2. **`build_inner_bootfs_fit()`:**
   - Pure-Python generator for inner `bootfs` FIT images containing `kernel-1`, optional `fdt-1`, `/configurations/conf_linux`, and `/configurations/conf_lx_<board>`.
   - Deliberately omits `/brcm_rootfs_encrypt` to trigger U-Boot's raw SquashFS boot fallback.
3. **CLI Arguments:**
   - `--bootfs <path>`: Packages a bootfs/kernel FIT into `/images/bootfs`.
   - `--rootfs <path>`: Packages a SquashFS image into `/images/rootfs`.
4. **Regression & Validation:**
   - 11 unit tests in `scripts/test_build_f1_fit_skeleton.py` (all passing).
   - 166 repository tests passing (`./tools/venv/bin/python3 -m unittest discover -s scripts/`).

---

## 5. What Was Not Shown

- Not tested: Sending a live dual-component (`bootfs` + `rootfs`) ITB image to the physical router over BOOTP/TFTP.
- Not obtained: The device's active AArch64 kernel binary (`Image.lz4` or `Image.gz`). While the FIT packaging and bootargs logic are verified in source, booting an inner `bootfs` requires a functional kernel and device tree for BCM68360.
