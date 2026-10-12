# RBI crypto — attempt 3 (boot log + module path)

**Reference RBI:** `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` (19.4.0507)  
**Boot log:** public GCNT-X **19.4.0856** UART capture ([pastebin biRghtLr](https://pastebin.com/raw/biRghtLr))  
**Log:** `artifacts/logs/decrypt-attempt3.txt`

## Decrypt success

**No.** **71** unique 32-byte OSCK trials after dedup (37 community `.osck` + **61** derived names including **21** boot-log-only constants). All **`bad_osck`** at the first `0xB7` unwrap.

Boot-log derivations included `bl_oid`, firmware/bootloader git hashes, full `bl_version` / `SW Version` strings, `.r2secr` / prozone / `flashaddress` physical addresses, NAND `flashId` prefix, and `RIP_ID_OSCK` HMAC salts. None are the RBI OSCK.

## What changed in tooling

| Artifact | Purpose |
|----------|---------|
| `scripts/attempt_rbi_decrypt.py` | `boot_log_derived_candidates()` |
| `scripts/test_boot_log_osck_trials.py` | regression on candidate shape/count |
| `scripts/select_r2secr_ko.py` | map `uname -a` / kernel banner → `tools/secr/r2secr*.ko` |
| `scripts/build_r2secr_module.sh` | macOS cross-compile `r2secr.o` + package `r2secr.arm64.4.1.52.ko` — [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md) |
| `scripts/acquire_f1_config_key.sh` | default KO corrected from **armv7 `4.1.52_p2v8`** to **`r2secr.arm64.4.1.52.ko`** for GCNT-X aarch64 |

## RBI download sweep (this pass)

| URL | Result |
|-----|--------|
| `:7547/1940507x4581025.rbi` | **200** — same bytes as local reference (32 759 365) |
| `:7547/1940856*`, `1951062-gcnt-x-*` | **404** |
| `:7577/.../19.5.1062_unified.rbi` | **403** (18 B) |

No second sealed image for header diff.

## Honest unblock chain

1. **RBI plaintext** still needs **`RIP_ID_OSCK` (`0x0121`)** for GCNT-X. Boot log proves the kernel loads it (`OSCK Loaded!`) but does not print bytes.
2. **On-router dump** (root + USB): copy **`tools/secr/r2secr.arm64.4.1.52.ko`** → `insmod` → `dmesg` hex for **`0x0121` (OSCK)** / **`0x011f` (ECK)** → `eripv2.py` on `dd` of **eripv2** MTD. Built on Mac 2026-10-12 ([r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md)); if **23.1.b** `uname -r` differs, rerun `scripts/build_r2secr_module.sh` on Linux with device `KDIR`.
3. **UART on your 23.1.b unit** (read-only): capture `Linux version …` and `/proc/mtd` to confirm whether 23.1.b still uses aarch64 4.1.5x and the same **eripv2** name before any root attempt.

## Best next experiment

Root or lab 19.x hardware → `insmod` + `dmesg` DumpHex for **`nextFreeItem->id : 121`** (OSCK) → save as `GCNT-X.osck` → rerun `tools/venv/bin/python3 scripts/attempt_rbi_decrypt.py` → `binwalk -e` → squashfs RE (`cwmpd`, `transformer`, `bli_unseal`).

See also: [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md), [rbi-crypto-attempt2.md](rbi-crypto-attempt2.md).
