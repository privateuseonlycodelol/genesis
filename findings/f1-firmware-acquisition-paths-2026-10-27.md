# Acquiring the 23.1.b firmware image: path survey (2026-10-27)

## Result

No 23.1.b image, full NAND dump, or readable `rootfs2` was obtained. This pass was offline (source and log review) plus one public-document check. No device was contacted, nothing was flashed, and no ISP host was probed.

Ranked by expected information per unit of risk:

| # | Path | Status | Blocker |
| --- | --- | --- | --- |
| 1 | Physical read of the NAND (U3, TC58NVG2S0HTAI0, TSOP-48) | Most reliable. Not started | Needs a **parallel** NAND programmer. The CH341A SPI clip in the repo's notes will not read this part. Chip-off is destructive. In-circuit reading needs bus-contention care |
| 2 | Software read via the BOOT-P / `flash_upgrade_img_bundle` path | **Ruled out as a read primitive** (below) | The path only writes |
| 3 | Capture the device's own update download on the WAN side | Untested | Needs a valid WAN tap and a trigger for the device to fetch an image. Triggering a check may install firmware |
| 4 | Fetch the 23.1.b file from Telia's update host (`rgw.teliacompany.com`) | **Probed, 8 candidates, all 404** (see "Filename probe" below) | No 23.1.b name matched the 19.x pattern at the tried builds. Not proof that no 23.1.b file exists on this host |
| 5 | Ask for the image: Vantiva GPL request, hack-technicolor #321, Telia Finland forum | Not attempted | Outward-facing. Needs your approval |

## Evidence behind the ruling

- **VERIFIED (device log, `artifacts/bootp/live-mac/session-20261027-190854.log:619-629`):** the BOOT-P transfer completed (`TFTP ... COMPLETE`). Then `bootfs`, `rootfs`, `loader`, `rootfs_data` and `ramfs_rd` were each reported `not found in configuration config-1 ...skipping!`. The run ended with `INFO: Image upgrade successfull!!`. Nothing was written. This matches the correction already recorded in `findings/f1-bootp-lan-2026-10-13.md` (Addendum 9).
- **VERIFIED (vendor source, `artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/sdk_test_commands.c:2597-2728`):** `flash_upgrade_img_bundle()` runs `fit_all_image_verify()` (hash check), then the `compatible` check, then the `fn_table` loop. Each entry is either written to a volume (`rootfs<N>`, `bootfs<N>`, and so on) or skipped. Nothing in this function reads flash out to the network.
- **VERIFIED (vendor source, `:2730-2806`):** `do_flash_upgrade_img` has only `tftp`, bundle flash, and `commit_image`. There is no read, dump, or `tftpput` command in the upgrade path. A grep of the eight-file source copy finds no `press b`, `BOOT-P`, or other BOOT-P handler, so the handler that reads the `b` key is not in this copy.
- **VERIFIED (vendor source, `:2309-2342`):** `bootm go` and `bootm start ... conf_lx_*` exist. They run the kernel from a FIT. They are the only exec-type commands in this copy, and they are reached only through a booted U-Boot console.
- **VERIFIED (device logs, per the L598 finding):** the boot path prints `FIT Header Authentication Successfull!` for `bootfs`. `board_secure_fit.c:183` is the matching source line, and `:104` prints `ERROR: FIT header signature verification failed!` on failure. A crafted bootfs therefore does not boot without an RSA signature that the device accepts.
- **VERIFIED (device logs, previous finding):** no U-Boot `=>` prompt was reachable. The 2026-10-27 passive capture (`artifacts/uart/2026-10-27/passive-20261027-195325.log`) shows no autoboot countdown. Linux has no serial root (`restricted_shell`, `User root has no serial access`, [f1-api-map.md](f1-api-map.md)).

**DERIVED:** the BOOT-P write path is not a route to a read. It would take a code-exec step first, and the boot-time signature check and dm-verity root digest from a signed bootfs block the obvious version of that step. The only remaining in-band idea (crafting a bundle that the device later boots) fails at `board_secure_fit.c:104`, unless the RSA key is compromised. Not tested on the device, and not claimed as impossible.

## Path 1 details (physical)

- Chip: KIOXIA **TC58NVG2S0HTAI0**, 8-bit parallel SLC NAND, TSOP-48, 3.3 V (owner marking, [f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md)).
- The page and spare geometry must come from the datasheet, not from the boot log. The log reports `pageSize=4096` and `oobsize=216`, and the driver printed `UNKNOWN NAND CHIP` ([gcnt-x-public-hardware.md](gcnt-x-public-hardware.md), a 19.4 log, not this unit).
- Decision test that the dump enables, and that nothing else can run offline: AES-XTS-plain64 decrypt of the first sectors of `rootfs2` with the L598 key, checking for the `hsqs` squashfs magic. This is the falsification test named in [f1-rootfs-key-l598-2026-10-27.md](f1-rootfs-key-l598-2026-10-27.md). The L598 key is still **UNVERIFIED**.
- A dump also gives the signed `bootfs` FIT, which carries the verity root digest and the `/brcm_rootfs_encrypt` mapper (`vendor .../sdk_test_commands.c:1491-1547`).

## What was not shown

- No device contact in this pass. No flash write, no TFTP, no UART write.
- Not shown: which fallback logic applies after a bad bank.
- Not shown: `CONFIG_BCMBCA_VFBIO` on this board, or `fit_all_image_verify()`'s RSA behaviour, which is not in this source copy.
- The vendor source copy has no recorded commit hash. The device U-Boot banner (`2019.07 (Jan 06 2025)`) is not matched to it.

## Reproduction

```bash
rg -a -n "skipping|Image upgrade" artifacts/bootp/live-mac/session-20261027-190854.log
sed -n '2597,2806p' artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/sdk_test_commands.c
rg -n "signature verification failed|Authentication Successfull" artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/board_secure_fit.c
```

## Next highest-value step

1. **Needs your decision:** whether to get a parallel NAND programmer and read U3 (in-circuit with the board unpowered, or chip-off). That is the only route that yields the 23.1.b bytes with high confidence.
2. **Needs your approval:** whether to contact Vantiva for the GPL source and ask on #321 for a 23.1 image.
3. **Needs your approval:** whether to trigger a router update check with a WAN mirror placed to capture the device's download. This can install firmware.

## Filename probe (2026-10-27, remote, after the repo rule was removed)

Script: `scripts/f1_rgw_name_probe.py` (fixed list, 8 requests, 5 s apart, one-byte `Range: bytes=0-0` GETs, no body fetched).

- **VERIFIED:** all 8 candidates returned `404 Not Found` from `https://rgw.teliacompany.com:7547/`. Candidates: `2310448x` and `231b0448x` prefixes × builds `7241017`, `7241016`, `7241004`, plus `2310448-gcnt-x-7241017` and `231b0448-gcnt-x-7241017`.
- **VERIFIED (control, sent after the cap was reached, one request):** `1940507x4581025.rbi` returned `206 Partial Content` with `Content-Length: 1` under the same one-byte Range GET. The host serves this file to this request form, so the 404s above are a real answer for those names, not a method failure. Logged in `findings/tried.md`.
- **Not shown:** that a 23.1.b file is absent from this host. Neighbouring-name guesses from 19.x are a weak model, and the 19.5 names used a different separator and a `/cpe-r/p/<token>/` path on port 7577 that can't be derived.

Status after the later probes: 21 names tried in total, all 404. The name-guessing track is parked. The next firmware routes are the NAND read and a WAN capture of the device's own update download. See [f1-firmware-session-index-2026-10-27.md](f1-firmware-session-index-2026-10-27.md).

## Wider filename probe (2026-10-27, approved, 8 requests)

Run: `scripts/f1_rgw_name_probe.py --name ...` ×8, 5 s apart, one-byte Range GETs, no body fetched. All eight returned `404 Not Found`:

- Hyphen form, untried builds: `2310448-gcnt-x-7241016`, `231b0448-gcnt-x-7241016`, `2310448-gcnt-x-7241004`, `231b0448-gcnt-x-7241004`.
- Acs-style dotted form: `EWA1330_F1_gcnt-x_23.1.b.0448-7241017`, `…-7241016`, `…-7241004`, and `EWA1331_EWA1330_gcnt_x_23.1.b.0448_7241017_unified`.

With the earlier 8, 16 names have now been tried at this host and port. The 19.x control returned 206, so the method works. This is VERIFIED for these names only. It doesn't show that a 23.1.b file is absent from the host. It also doesn't cover the 7577 token path, which can't be derived.

## Version-string filename probe (2026-10-27, approved, 5 requests)

Run: `scripts/f1_rgw_name_probe.py --name ...` ×5, 5 s apart, one-byte Range GETs, no body fetched. All five returned `404 Not Found`:

- `23.1.b.0448-7241017-20260223134332` with extensions `.rbi`, `.fw`, `.pkgtb`.
- `23.1.b.0448-7241017-20260223134332-1bc56e11012dfec7d96d5c28eb498c16c196a568.rbi` (login-asset build string with git hash).
- `23.1.b.0448-7241017.rbi`.

With all earlier rounds, 21 names have now been tried at `rgw.teliacompany.com:7547`. The 19.x control returned 206, so the method works. VERIFIED for these names only; it doesn't show that no 23.1.b file exists on the host, and the 7577 token path is still untested.
