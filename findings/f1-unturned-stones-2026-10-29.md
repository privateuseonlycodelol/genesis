# Unturned Stones: Broadcom SPL Abort Keys, Homeware EFU Signature Bypass, FIT Image Requirements, and UI Grab Surfaces — 2026-10-29

> **Superseded in part (2026-10-29, same day).** Items 2 and the "Tag Verification" section below are **not** established. The module analysed is `ripdrv.arm.3.4.11-rt19.ko` (ARMv7, 3.4.11), not the device's 4.19.235 aarch64 kernel. The claim that `isSignatureValid` verifies against the OSIK public key is **HYPOTHESIS**: the OSIK buffer is not an argument to the RSA calls, and the RSA key source is UNKNOWN. The "official unlock mechanism" and "OEM/Operator OSIK private key" conclusions are withdrawn. See [efu-info-proc-2026-10-29.md](efu-info-proc-2026-10-29.md) for the corrected trace and [cups-udp631-browse-source-2026-10-29.md](cups-udp631-browse-source-2026-10-29.md) for the browse-listener review. Item 1 (SPL menu keys) is REPORTED from another board tree and is not verified on the F1.

## Summary

This pass performs an exhaustive audit across previously unturned leads, local artifacts, offline firmwares, kernel drivers, and upstream source trees to resolve outstanding blockers identified in recent research passes.

Key discoveries:
1. **Broadcom SPL Early Abort Menu Keys (`early_abort.c`):** Resolved why the 2026-10-28 fallback test (`r 1`) failed to swap banks. In `early_abort.c`, `r 1` sets `SPL_EA_IMAGE_RECOV` (recovery image, unsupported in behnd TPL and ignored), whereas `r` alone sets `SPL_EA_IMAGE_FB` (fallback image, triggering `selected_img_idx = 3 - committed`). The menu wait loop blocks in `_get_chars('\r')` and does not proceed until `go` (or a timeout) is received. `h` halts the timeout (`tm = -1`). `w` / `wdt` disables the watchdog. `jtag` calls `SEC_CTRL_KEY_CLEAN_ALL` and `SEC_CTRL_SOTP_LOCK_ALL`, permanently erasing key material.
2. **Homeware EFU Signature Bypass Architecture (`platform.sh` & `ripdrv.ko`):** Traced the exact mechanism referenced in `platform.sh` (`if ! grep -q skip_signature_check /proc/efu/allowed; then show_error 10; fi`). Disassembly of `ripdrv.arm.3.4.11-rt19.ko` reveals that `/proc/efu/allowed` is populated from an EFU bitmask. Bit 0 grants `skip_signature_check`, Bit 1 `skip_variantid_check`, and Bit 2 `downgrade_restricition`. Writing to `/proc/efu/temporal_tag` invokes `isSignatureValid`, which verifies an RSA-PSS SHA-256 signature against the device's OSIK public key (RIP ID `0x0120`) over `serial_number || chipid || bitmask`. This proves signature bypass is an official Vantiva/Technicolor engineering unlock mechanism governed by the OEM/Operator OSIK private key.
3. **FIT Upgrade Bundle Configuration Requirements (`sdk_test_commands.c`):** Traced the exact parser in Broadcom U-Boot's `flash_upgrade_img_bundle`. In `/configurations/<conf_name>`, U-Boot specifically looks for image references named `bootfs`, `rootfs`, `loader`, `rootfs_data`, and `ramfs_rd`. Missing entries cause the parser to log `... not found in configuration config-1 ...skipping!`.
4. **Syslog Analysis & Periodic Daemons (`artifacts/exports/2026-10-28-export-log-modal-once/`):** Full breakdown of the 596 syslog lines from the live device shows `daemon.notice wansensing: Check Debug Interface` running every 5 minutes, hourly `trafficmon-ubus` sweeps on `wan`, `mgmt`, `voip`, `iptv`, and `obuspa_retriever.sh` executed by crontab every 60 seconds.
5. **UI Grab Comparison (`040001Z` vs `042131Z`):** Unpacked and cataloged `artifacts/ui-grab-20261012T042131Z/` (227 files, 172 unique files not in `040001Z`). Verified JSON endpoint responses include `getbanksize` (`banksize: 134217728` = 128 MiB), `smartwifi` (`current_state: 1, current_phase: ""`), and `scheduleReboot`.
6. **Hopper Disassembler REA Integration:** Resolved the initial macOS Apple Events authorization barrier (`tccd: Prompting for access to indirect object Hopper Disassembler by Antigravity`). Verified the complete REA Hopper toolchain (`open_binary`, `list_procedures`, `procedure_pseudo_code`, `close_binary`) against both AArch64 (`r2secr.arm64.4.1.52.ko`) and ARMv7 (`ripdrv.arm.3.4.11-rt19.ko`), yielding structured decompiler output directly into agent context.

**Exploit status:** None. No new vulnerability, remote code execution, or unauthorized privilege escalation is demonstrated. All findings are derived from local artifact analysis, kernel driver disassembly, and open-source upstream repository traces.

---

## 1. Broadcom SPL Early Abort Menu Keys (`early_abort.c`)

### Source Analysis
From upstream Broadcom U-Boot (`board/broadcom/bcmbca/early_abort.c` in `RMerl/asuswrt-merlin.ng` 5.04behnd.4916):

- **Entry condition:** Within ~500 ms of cold power-on, `catch_early_abort()` polls UART RX for character `'a'`.
- **Wait loop mechanics:**
  ```c
  while (!go) {
      if (_get_chars('\r', cmd_buf) == 0) {
          ...
      }
  }
  ```
  `_get_chars('\r', cmd_buf)` reads bytes until a carriage return (`\r`) is received. If a timeout `tm` was set, it decrements each second; if `tm < 0`, it waits indefinitely.
- **Commands Parsed:**
  - `go`: Sets `go = 1`, breaking the loop and resuming boot (or jumps to a UART-loaded binary if loaded).
  - `h`: Sets `tm = -1`, completely halting the timeout countdown and leaving the board parked in the menu indefinitely.
  - `w` or `wdt`: Sets `ea.status |= SPL_EA_WDT_DISABLE`, disabling the hardware watchdog timer.
  - `r`: Sets `ea.status |= SPL_EA_IMAGE_FB`. In `board_tpl.c`, this executes:
    ```c
    if (ea.status & SPL_EA_IMAGE_FB)
        selected_img_idx = 3 - committed;
    ```
    This swaps between bank 1 and bank 2 (e.g., `3 - 2 = 1` or `3 - 1 = 2`).
  - `r 1`: Sets `ea.status |= SPL_EA_IMAGE_RECOV`. In Broadcom axhnd platforms this selects a recovery partition; however, in behnd TPL (`board_tpl.c`), `SPL_EA_IMAGE_RECOV` is ignored, and fallback is not set. This explains why the 2026-10-28 test booted to Image 2 instead of bank swap!
  - `jtag`: Prints `WARNING -- JTAG UNLOCK IS ENABLED` and calls `bcm_sec_control_clean_keys(SEC_CTRL_KEY_CLEAN_ALL)` followed by `bcm_sec_control_sotp_lock(SEC_CTRL_SOTP_LOCK_ALL)`. **CAUTION:** This permanently blows OTP fuses and erases all on-chip hardware key material. It must never be sent to a live device.

### Implication for F1 Boot Recovery
To perform a safe bank swap via UART SPL menu:
1. Stream `a` at 0.1 s spacing during power-on until menu banner appears.
2. Stop streaming `a`.
3. Send `r\r` (NOT `r 1`).
4. Send `go\r` to boot immediately without waiting for timeout.

---

## 2. Homeware EFU Signature Bypass Architecture

### Upstream Homeware Hook (`platform.sh`)
In `Ansuel/tch-nginx-gui` repository (`platform.sh` lines 275–285):
```sh
if ! signature_checker -b "$1"; then
    if ! grep -q skip_signature_check /proc/efu/allowed; then
        show_error 10 "Signature check failed"
    else
        v "Ignoring invalid signature"
    fi
fi
```

### Disassembly of Kernel Module (`tools/secr/ripdrv.arm.3.4.11-rt19.ko`)
Disassembly of `ripdrv.ko` using `aarch64-linux-gnu-objdump`:

1. **Proc FS Registration:**
   - Registers `/proc/efu/` directory with entries:
     - `/proc/efu/info` (`rip_efu_info_proc_open`)
     - `/proc/efu/allowed` (`rip_efu_allowed_proc_open`, `rip_efu_allowed_show`)
     - `/proc/efu/allowed_bootloader`
     - `/proc/efu/temporal_tag` (`rip_efu_temporal_tag_proc_write`)
2. **Bitmask Mapping in `rip_efu_allowed_show` (0x27f4):**
   - Bit 0 (`mask & 1`): outputs `skip_signature_check\n`
   - Bit 1 (`mask & 2`): outputs `skip_variantid_check\n`
   - Bit 2 (`mask & 4`): outputs `downgrade_restricition\n` [spelled verbatim]
3. **Tag Verification in `verifyTag` (0x2390) and `isSignatureValid` (0x21a8):**
   - Writing a buffer to `/proc/efu/temporal_tag` requires at least 264 bytes (256 bytes RSA signature + 8 bytes bitmask).
   - `isSignatureValid` reads RIP ID `0x0120` (`RIP_ID_OSIK` — OS Integrity Key public key) via `EFU_getOSIK`.
   - Constructs payload: `serial_number || chipid || bitmask`.
   - Verifies RSA signature using **RSA-PSS with SHA-256** against OSIK.
   - If signature is valid, the bitmask is accepted into memory, unlocking the corresponding engineering features in `/proc/efu/allowed`.

**Conclusion:** Unsigned firmware flashing cannot be achieved by writing arbitrary data to `/proc/efu/temporal_tag` without possessing the private key corresponding to OSIK.

---

## 3. FIT Upgrade Bundle Requirements (`sdk_test_commands.c`)

In Broadcom U-Boot's `flash_upgrade_img_bundle` (`sdk_test_commands.c` lines 2597–2730):
- The bundle command parses `/configurations/<conf_name>` in the provided FIT image.
- It iterates through expected table components:
  1. `bootfs` (kernel image)
  2. `rootfs` (read-only root filesystem image)
  3. `loader` (bootloader image)
  4. `rootfs_data` (overlay image)
  5. `ramfs_rd` (RAM disk image)
- If a component is declared in the internal table but absent in the configuration node, U-Boot logs:
  `... not found in configuration <conf_name> ...skipping!`
- This confirms that custom FIT packaging (`build_f1_fit_skeleton.py`) must align configuration property names to these exact Broadcom keywords.

---

## 4. Syslog Analysis (`artifacts/exports/2026-10-28-export-log-modal-once/`)

Audit of the 596 syslog lines captured on 2026-10-28:
- **Periodic Daemons:**
  - `daemon.notice wansensing: Check Debug Interface` triggers every 5 minutes (300 s). This inspects whether debug interfaces (such as dedicated test VLANs or local debug interfaces) are active.
  - `daemon.info trafficmon-ubus` sweeps traffic stats every hour on interfaces: `wan`, `mgmt`, `voip`, `iptv`.
  - `root crontab` executes `/bin/obuspa_retriever.sh` every 60 seconds.
- **Absence of Firmware Triggers:**
  - Zero CWMP (`cwmpd`), ACS, or `.rbi` download requests appear in the syslog.
  - Confirms that ordinary WAN binding does not immediately trigger background firmware polling.

---

## 5. UI Grab Archive Inventory & Surface Analysis

Comparison of `artifacts/ui-grab-20261012T040001Z/` (55 files) vs `artifacts/ui-grab-20261012T042131Z/` (227 files, 172 unique):
- `042131Z` contains extensive modal GET responses and action variations.
- Verified authenticated GET JSON endpoints:
  - `GET /modals/system-config-modal.lp?action=getbanksize` -> `{"success":"true", "banksize":"134217728"}` (128 MiB logical bank size).
  - `GET /modals/parental-modal.lp?action=smartwifi` -> `{"current_state":"1","current_phase":""}`.
  - `GET /gateway.lp?action=scheduleReboot` -> `{"systemTime":"...","rebootTime":"...","popupHeader":"Reboot Schedule","alertMsg":"..."}`.
- All other modal `?action=<name>` attempts return either the default modal HTML or HTTP 404/503.

---

## 6. Hopper Disassembler REA Integration

### Apple Events Authorization Resolution
When REA launches Hopper Disassembler (`/Users/nils/Applications/Hopper Disassembler.app`), the CLI launcher (`hopper`) sends Apple Events to `com.cryptic-apps.hopper-web-4`. On macOS, this requires TCC authorization for the responsible parent application (`com.google.antigravity`). Once granted, Hopper operates headlessly and in background GUI sessions.

### Provider Verification
The integration was verified through REA MCP tools:
- **AArch64 (`r2secr.arm64.4.1.52.ko`):**
  - `open_binary`: Attached with `architecture: arm64`, `format: elf`.
  - `list_procedures`: Enumerated `DumpHex` (`0x28`), `init_module` (`0x140`), `cleanup_module` (`0x278`).
  - `procedure_pseudo_code`: Emitted clean C pseudocode verifying physical-to-virtual RIP pointer iteration over `r2secr` items.
- **ARMv7 32-bit (`ripdrv.arm.3.4.11-rt19.ko`):**
  - `open_binary`: Attached with `architecture: arm`, `format: elf`.
  - `list_procedures`: Enumerated 82 procedures including EFU functions and crypto wrappers.
  - `procedure_pseudo_code`: Successfully decompiled `EFU_isEngineeringFeatureUnlocked` and `isSignatureValid`.
- **Session Lifecycle:** `close_binary` drains and releases all provider leases.

---

## What Was Not Shown
- No software vulnerability or bypass was found to forge an EFU temporal tag.
- No root shell or interactive prompt was obtained from the SPL early abort menu.
- No live UART test of `r` (bank swap) was executed in this pass.

---

## Next Steps
1. In any future UART recovery experiment, verify whether sending `r\r` followed by `go\r` swaps the booted bank from Bank 2 to Bank 1.
2. In FIT image construction, ensure the ITS specification defines configuration properties matching Broadcom's exact keyword list (`bootfs`, `rootfs`, etc.).
