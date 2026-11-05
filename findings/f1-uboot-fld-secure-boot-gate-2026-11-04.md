# Broadcom U-Boot FLD Secure Boot Gate & FIT Bundle Validation (2026-11-04)

## Scope and Status

Offline reverse-engineering analysis of Broadcom U-Boot secure boot source code (`artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/board_secure.c`, `board_secure_fit.c`, `sdk_test_commands.c`) cross-referenced against live UART boot captures (`artifacts/uart/2026-10-27/router-boot-20261027-010457-82769.log`) and live recovery session logs (`artifacts/bootp/live-mac/session-20261027-190854.log`).

No live flash writes performed. Tooling implemented in pure Python with 16 dedicated unit tests and 182 total repo tests passing.

---

## 1. Ground Truth: The Secure Boot Gate on `bootfs`

In earlier passes ([f1-uboot-fit-flashing-schema-2026-10-30.md](f1-uboot-fit-flashing-schema-2026-10-30.md)), it was observed that Broadcom U-Boot recovery flasher (`flash_upgrade_img_bundle`) accepts dual-component FIT bundles without cryptographic vendor signatures and writes raw `bootfs` and `rootfs` volumes to UBI. It was also noted that omitting `/brcm_rootfs_encrypt` bypasses dm-verity and dm-crypt in `bcm_handle_mapper()`.

However, tracing the execution path from U-Boot to Linux reveals a critical **boot-time authentication barrier**:

### A. Unconditional Boot-Time FIT Authentication
- **VERIFIED (source):** In `sdk_test_commands.c:1447-1451` (`nand_load_bootfs`):
  ```c
  sprintf(cmd, "ubi read %x bootfs%d", bootfs_load_addr, img_index);
  ret = run_command(cmd, 0);
  if (!ret) {
      fit_auth = bcm_sec_validate_fit((void*)(uintptr_t)bootfs_load_addr, 0x10000);
  }
  ```
  All boot paths (NAND, eMMC, SPI-NOR, VFBIO) unconditionally invoke `bcm_sec_validate_fit()` on the inner `bootfs` before executing `bcm_handle_mapper()` or `bootm`.

### B. What `bcm_sec_validate_fit()` Enforces
- **VERIFIED (source, `board_secure_fit.c:152-207`):**
  - Evaluates `bcm_sec_state()`.
  - Searches for appended signature tags (`BCM_TAG_FIT_HDR_SEC_SIGNATURE` / `0x46495453` "FITS" or `BCM_TAG_FIT_HDR_SEC_PUBKEY` / `0x46495450` "FITP") placed after `fdt_totalsize()`.
  - Executes `bcm_sec_rsa_verify(fit, size, sig, key_len, key, &im)` covering the entire inner FDT blob.
  - If verification fails:
    ```c
    _die:
        if (rc) {
            printf("FAILED to authenticate FIT header!!! \n");
            if (st & SEC_STATE_SECURE) {
                bcm_sec_abort();
            } 
        }
    ```

### C. Implementation of `bcm_sec_abort()`
- **VERIFIED (source, `board_secure.c:635-652`):**
  ```c
  void bcm_sec_abort(void)
  {
      /* Lock SOTP, wipe keys in SRAM and locally in .data */
      bcm_sec_deinit();
  #if defined(CONFIG_BCMBCA_OTP)
      bcm_otp_deinit();
  #endif
      WATCHDOG_RESET();
      puts("### ERROR ### Boot Aborted. Please RESET the board ###\n");
      while (1) ;
  }
  ```
  `bcm_sec_abort()` locks SOTP, scrubs all keys, prints an error banner, and enters an infinite loop.

### D. Security State of the Owned Unit
- **VERIFIED (live boot log `router-boot-20261027-010457-82769.log` lines 39–587):**
  - Line 39: `Board is FLD secure`
  - Line 40: `$SPL: 50404p1@...-SECURE $`
  - Line 338: `$TPL: 50404p1@...-SECURE $`
  - Line 385: `FIT Header Authentication Successfull!`
  - Line 587: `Secure Mode : FLD`
- **Result:** The owned router's SOTP eFuses are blown to **FLD (Field Secure)** production mode. `st & SEC_STATE_SECURE` is active.

### E. Consequence for Live Flashing
- **DERIVED:** While BOOTP recovery flashing will happily write an unsigned `bootfs` into NAND UBI, the subsequent boot sequence will fail authentication in U-Boot, enter `bcm_sec_abort()`, and hang the device.
- **DO NOT** attempt to live-flash a custom unsigned kernel FIT onto this board. Without an authentic vendor 23.1.b restore image, a failed bootfs flash risks rendering the active bank unbootable.

---

## 2. Structural Validator Implementation

To prevent unsafe flashing attempts and ensure any future bundles strictly conform to Broadcom's upgrade parser contracts, `scripts/validate_f1_fit_bundle.py` was created.

### Contract Checks Implemented:
1. **Whole-Bundle Hash Verification:** Replicates U-Boot `fit_all_image_verify()` — ensures every member under `/images/*` carries a valid SHA-256 hash in `hash-1`. (A hash failure causes U-Boot to abort the entire bundle upgrade).
2. **Configuration & Compatibility:** Verifies `/configurations`, `:default`, and `compatible = "GCNT-X"` against `verify_compat_string()`.
3. **`fn_table` Resolution:** Validates that members defined in configuration nodes (`bootfs`, `rootfs`, `loader`, `rootfs_data`, `ramfs_rd`) properly point to `/images/<name>`.
4. **Secure Boot Gate Warning:** Inspects the inner `bootfs` payload. If the payload is an FDT lacking an appended `FITS`/`FITP` signature tag, it emits a critical warning flagging that the image will hang an FLD-secure unit at boot time.
5. **Filesystem Magic Detection:** Checks whether `rootfs` starts with SquashFS magic (`hsqs`) or UBIFS magic (`\x24\x05\x19\x05`) to confirm compatibility with U-Boot's unencrypted fallback logic.

### Testing & Validation:
- Tool: `scripts/validate_f1_fit_bundle.py`
- Test suite: `scripts/test_validate_f1_fit_bundle.py` (16 tests, 100% pass)
- Dry-run validation run:
  ```bash
  ./tools/venv/bin/python3 scripts/validate_f1_fit_bundle.py artifacts/firmware/dryrun-2026-11-04/bundle-dual-placeholder.itb
  ```
  Result: Successfully flagged the structural contract as valid while correctly emitting the FLD secure-boot gate warning.

---

## 3. What Was Not Shown

- That `rootfs` or `rootfs_data` are subject to U-Boot RSA authentication (the code trace indicates only `bootfs` undergoes `bcm_sec_validate_fit()`).
- That `mount_root` in stock Linux automatically preserves or wipes `rootfs_data` across an upgrade.

---

## 4. Strategic Implications for Next Steps

With custom unsigned kernels (`bootfs`) definitively blocked by FLD Secure Boot, arbitrary code execution must follow one of three viable routes:

1. **OverlayFS Injection via `rootfs_data` (BOOTP Flashing Vector):**
   - Keep the authentic, vendor-signed `bootfs` and `rootfs` intact on the board.
   - Use BOOTP recovery to deliver only `rootfs_data` formatted as a UBIFS volume containing an `/overlay/upper` hierarchy with modified credentials or initialization scripts.
2. **Physical NAND Read (TSOP-48 Vector):**
   - Desolder or clip the KIOXIA TC58NVG2S0HTAI0 NAND chip to dump `bootfs`, `rootfs`, and `eripv2`.
   - Resolves all offline key blockers (`RIP_ID_RANDOM_KEY_B` for config decrypt) and provides the authentic signed `bootfs` binary for analysis.
3. **GPL Source Code Acquisition (Vendor Vector):**
   - Dispatch the drafted request (`findings/f1-gpl-source-request-2026-10-29.md`) to obtain official Broadcom BCM68360 / Linux 4.19.235 patches and configuration.
