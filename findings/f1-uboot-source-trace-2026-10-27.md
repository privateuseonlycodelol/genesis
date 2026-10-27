# Vendor U-Boot source trace: bank commit, mapper, and boot gating (2026-10-27)

## Scope and status

Offline only. No device contact, no TFTP, no UART write, no flash. Source: the 8 vendor U-Boot files in `artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/` (gitignored). `shasum -a 256 -c SHA256SUMS` → all 8 **OK** (VERIFIED).

**Provenance caveat (VERIFIED mismatch):** the device prints `U-Boot 2019.07 (Jan 06 2025 - 22:32:33 +0000), Build: 20250106223231-c5207534ab`. The bundle loop on the device includes `rootfs_data` and `ramfs_rd`, and debug lines `flash_upgrade_img_bundle 3244>`. In this copy, `fn_table` has only `bootfs`, `rootfs`, and `loader` (non-VFBIO), and `rootfs_data`/`ramfs_rd` appear nowhere in the `*.c` files. Line 3244 is not in `flash_upgrade_img_bundle`. **Every statement below about the source describes this copy, not the device build** until the build is matched.

## Q1. Bank fallback and metadata state machine

- **VERIFIED (device log, 19:09 run, `artifacts/bootp/live-mac/session-20261027-190854.log` lines 619–637):** five members logged `not found ... skipping!`, then `Image upgrade successfull!!`, then `Getting committed 2 valid 1,2 seq 0,1`, `Remove/Creating` of `metadata1`/`metadata2`, `Setting committed 1 valid 1,2 seq 2,1`, `resetting ...`. No partition write appears.
- **DERIVED (source):** `do_flash_upgrade_img` → `flash_upgrade_img_bundle()` returns `err = 0` when every member is skipped (the `for` loop only `continue`s on a missing member). Then `commit_image(img_index)` runs (`sdk_test_commands.c`, `do_flash_upgrade_img` near line 2790). `commit_image` → `set_img_status(IMG_STAT_VALID, IMG_STAT_COMMIT)`, which sets `committed = img_index` and **marks `valid[img_index-1]` as valid regardless of what was written**.
- **DERIVED:** target bank = `get_img_index_for_upgrade()`: if `/chosen/active_image` is set, the inactive bank; otherwise `committed==1 → 2`, `committed==2 → 1`. So repeated bundle runs with **no members** toggle `committed` deterministically and write no partitions. The paste's "non-destructive toggle" is consistent with this, but it also marks the target VALID without checking it.
- **DERIVED:** no tentative flag or watchdog rollback is set in these 8 files. The only fallback code is `do_check_fallback` (`sdk_test_commands.c` ~2921), compiled only with `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT`, and no caller of `check_fallback` is in these files. Whether the device enables it is **UNKNOWN**. Until shown otherwise, a bank commit is treated as **permanent** (no automatic rollback).
- **Precondition:** if env `reformatOnUpgrade` is set, the bundle path calls `board_init_flash_parts(1)` (`sdk_test_commands.c` ~2685), which reformats partitions. The 19:09 log has no `reformat` line (VERIFIED by grep), so that run did not hit it. Env state on the device is not recorded.

## Q2. Mapper and bootargs inputs

- **VERIFIED (source):** `bcm_handle_mapper()` (`sdk_test_commands.c` ~1491) reads only the bootfs FIT node `/brcm_rootfs_encrypt` (`dev`, `type`, `mapper`). `%DEVICE%` comes from the caller. `%IMAGE_KEY%` is substituted from `gd->fdt_blob:/trust/key_image_aes`, i.e. the DTB built during boot, not from UBI or env. The result is written to env `rootfs_opts` via `env_set`. Caller `flash_opts` strings are hard-coded (`ubi.mtd=image ubi.block=0,N rootfstype=squashfs`).
- **VERIFIED (device log, boot section ~lines 373–419):** `FIT Header Authentication Successfull!`, then `Creating /trust/key_image_aes`, `Adding exported decoded key node key_image_aes`. The key is derived during boot from the encoded key chain.
- **VERIFIED (source), the important gate:** in `nand_load_bootfs()` (`sdk_test_commands.c` ~1433–1485), `fit_auth = bcm_sec_validate_fit(...)` **only gates `bcm_board_boot_fdt_fixup_from_fit()`**. The function returns `ret` from `ubi read bootfsN`, not `fit_auth`. `load_linux_img()` (~2235–2320) then runs `bootm start/loados/prep` unconditionally. So **a failed bootfs header check does not stop the boot path in this source.** Whether `bootm` verifies the kernel image itself depends on U-Boot library config that is not in this copy: **UNKNOWN**.
- **VERIFIED (source):** `bcm_sec_validate_fit()` (`board_secure_fit.c` ~152) returns **0** when there is no active public key and the device is in `SEC_STATE_UNSEC` (`rc = 0; goto _die`). So "0" is not proof of an RSA check in that state. On the device the key path ran (`FIT Header Authentication Successfull!` is printed only after `bcm_tag_fit_hdr_validate` passes).
- **DERIVED (hypothesis, not tested):** if the signed bootfs lacks `/brcm_rootfs_encrypt`, `bcm_handle_mapper()` returns 1, and `nand_load_bootfs()` falls back to reading the `rootfs%d` volume magic. A SquashFS magic gives `root=/dev/ubiblock0_N` **with no verity or crypt**. That path is chosen by the bootfs contents, and the rootfs volume's own content only has to carry the squashfs magic. Whether this path is reachable depends on the bootfs authentication actually gating the boot, which the source above suggests may not hold. **HYPOTHESIS.**
- **UNKNOWN:** whether any unsigned env variable reaches the kernel command line. The bootargs assembly that consumes `rootfs_opts` is in a board config not in this copy.

## Q3. Does the bundle path write UBI or env without signature checks?

- **VERIFIED (device log, lines 603–615):** the bundle is a FIT with `compatible = "GCNT-X"`, no signature node. The only integrity line is `## Checking hash(es) for FIT Image at 01000000 ... Hash(es) for Image 0 (kernel-1): sha256+`. The bundle was accepted. So **the bundle path accepts a hash-only, unsigned FIT** (VERIFIED for this build).
- **VERIFIED (device log):** the commit rewrites `metadata1` and `metadata2` (`Remove UBI volume`, `Creating static volume`). These are UBI volumes outside any signed image, written with no signature check. The boot-order flags live there.
- **DERIVED (absence of a warning, not a positive print):** the compat check ran and passed. No `WARNING: Skipping all compatibility checks due to forced updates` line appears, and no `not compatible` error appears.
- **Partition writes:** `flash_rootfs_nand()` (~1171) writes raw bytes to the `rootfs<N>` UBI volume with no encryption or verity step (DERIVED from source, consistent with the packaging finding).

## Q4. Read primitives from the BOOT-P state

- **VERIFIED (device log):** the BOOT-P exchange is server-to-device only (`BOOTREQUEST ... Replying`, then TFTP RRQ from the device, DATA blocks to it). No upload path is seen.
- **VERIFIED (source, these files):** no `tftpput`, `md`, `mm`, or flash-dump subcommand is registered in the `sdk`/`bca_test` tables. Generic U-Boot memory and flash read commands come from U-Boot core config, which is not in this copy.
- **UNKNOWN:** `httpd_start` (registered under `sdk` and `bca_test`, `sdk_test_commands.c` ~2998) starts an embedded web server. Its handlers live in `httpd/` (not in this copy). Starting it needs a U-Boot prompt, which BOOT-P did not give (see [f1-fit-rootfs-packaging-2026-10-27.md](f1-fit-rootfs-packaging-2026-10-27.md), "Passive UART check"). No read path is demonstrated.

## What was not shown

- Not matched: the device build against this source tree. Until it is matched (for example by the banner, or by a matching `flash_upgrade_img_bundle` line-3244 debug source), every source claim is about the copy.
- Not tested: any bootfs with `/brcm_rootfs_encrypt` removed; whether `bootm` verifies the kernel; the device's `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT` setting; whether `reformatOnUpgrade` or any unsigned env reaches the bootargs.
- Not run: no live device command. No write, no flash, no TFTP in this pass.

## Reproduction

```bash
cd artifacts/firmware/vendor-uboot-bcmbca-5.04behnd && shasum -a 256 -c SHA256SUMS
rg -n "flash_upgrade_img_bundle|commit_image|set_img_status|get_img_index_for_upgrade|do_check_fallback" sdk_test_commands.c
rg -n "fit_auth" sdk_test_commands.c
rg -n "rc = 0" board_secure_fit.c
```

## Next offline steps

1. Match the device build: find a copy of the source at the banner's build or the `c5207534ab` commit, and check that `fn_table` contains `rootfs_data`/`ramfs_rd`. Without this, nothing above is about the device.
2. Trace `bootm` FIT and kernel verification (`CONFIG_FIT_SIGNATURE`, `required` key) in the U-Boot library, to settle whether a failed bootfs header check reaches `bootm go`.
3. Find where `check_fallback` is called (board `bootcmd` or a board config) to settle whether a bank commit can roll back.

## Continuation (2026-10-27): caller, bootm verification, build match

Method: the vendor tree was read through `gh api` and `gh search code` against `RMerl/asuswrt-merlin.ng` (main, commit `ca72a61f8bc5ef920e29d63d53d9864262208f0c`). Fetched copies are scratch files under `/private/tmp/claude-501/uboot-trace/`, not in the repo. Code search is GitHub's index, not an exhaustive grep. A negative search result is evidence only within that index.

**Caller of `check_fallback`:** VERIFIED (index): `check_fallback` appears only in `sdk_test_commands.c` (definition and dispatch table). No caller was found. The board `bootcmd` was not located, so the caller is UNKNOWN.

**Fallback config state:** VERIFIED (fetched defconfigs): `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT=y` in `bcm963178`, `bcm94912`, `bcm963138`, `bcm963158`. It is absent from `bcm96855`, `bcm96856`, and `bcm96858`, which all set `CONFIG_FIT_SIGNATURE=y`. Kconfig: `depends on BCM_BOOTSTATE && !SMC_BASED`, `default n`. The device's config is not known.

**bootm verification (upstream code in the same tree):**
- VERIFIED: `fit_image_verify_with_data()` (`common/image-fit.c` ~1217–1262) fails on a hash mismatch. A signature is checked as a hard failure only when a `required` key is present (`fit_image_verify_required_sigs`). Other signatures print `-` and do not fail.
- VERIFIED: `bootm_start()` sets `images.verify = env_get_yesno("verify")` (`common/bootm.c` line 74). `env_get_yesno()` (`env/common.c` line 36) returns -1 when the variable is unset, which is truthy. So hash verification is on unless env `verify` is set to a false value.
- DERIVED: env `verify` can be changed only from a U-Boot command prompt. No env writer was found in the eight local files, and BOOT-P does not reach a prompt.
- DERIVED consequence: a hash check does not prove authenticity. A FIT rewritten together with consistent hash nodes passes. The only signature gate in this path is the vendor `bcm_sec_validate_fit()`, which (per the earlier section) does not stop boot. So a tampered bootfs with consistent hashes is a HYPOTHESIS that still needs a test.

**Build and chip match:**
- VERIFIED (device log): `CPU : BCM68360_B1` (lines 514, 583).
- VERIFIED (index): the banner build string `c5207534ab` has no hit in the repo index.
- VERIFIED (tree): no `bcm68360` mach directory and no `bcm68360` defconfig in the 5.04behnd.4916 U-Boot tree. `BCM68360` appears there only as a board and driver name for a reference board (`bcm68560gref.c`).
- REPORTED (upstream U-Boot commit text found via web search): BCM68360 is a variant within the BCM6856 family. Nearest in-tree neighbour: `bcm96856_defconfig`, which has FIT signatures on and no bootstate fallback. Neighbour only, not a match.
- Result: the device-to-tree mapping is UNKNOWN. No public GPL source for GCNT-X or the Telia F1 was found (web search, not exhaustive).

**Revised answers:**
- Fallback on the device: UNKNOWN. In the 6855/6856/6858 neighbours it is off, so a bank commit is permanent there.
- bootm: hash checking is on by default and does not add authenticity.
- The copy stays a family neighbour, not the device's build.

**Still not shown:** device-matched U-Boot binary, bootfs contents, a live fallback test, and any tampered-bootfs boot. The device's own U-Boot image can be read from a flash dump, which requires a live-device action, so it is not done here.
