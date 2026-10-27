# Firmware and NAND work: session index (2026-10-27)

Index for the 2026-10-27 firmware session. Each item links to its detailed finding. Status tags follow [AGENTS.md](../AGENTS.md): VERIFIED, DERIVED, REPORTED, HYPOTHESIS, UNKNOWN / BLOCKED.

**Bottom line:** no 23.1.b firmware image, full NAND dump, or readable `rootfs2` has been obtained. The L598 key is still untested against real 23.1.b bytes. The next step that can settle it is a physical read of the NAND, which has not started.

## 1. Acquisition paths for the 23.1.b image

Detail: [f1-firmware-acquisition-paths-2026-10-27.md](f1-firmware-acquisition-paths-2026-10-27.md)

| Path | Status | Evidence |
| --- | --- | --- |
| BOOT-P / TFTP recovery | **Ruled out as a read path** | VERIFIED: the 19:09 run skipped all five bundle members and wrote nothing (`artifacts/bootp/live-mac/session-20261027-190854.log:619-629`). The vendor source's `flash_upgrade_img_bundle()` and `do_flash_upgrade_img` only write flash |
| Crafted bootfs to boot later | **Blocked** | VERIFIED: the boot path checks the FIT header signature (`board_secure_fit.c:104`) |
| Telia update host, filename guessing | **21 names tried, all 404** | VERIFIED. The 19.x control `1940507x4581025.rbi` returned 206, so the method works. See section 1a |
| WAN capture of the device's own update download | Not attempted | Needs a valid tap and a trigger. A check may install firmware, so it needs approval |
| Ask Vantiva, hack-technicolor #321, Telia forum | Not attempted | Outward-facing; needs approval |
| Physical NAND read | **Planned, not started** | See section 3 |

### 1a. Filename probe against `rgw.teliacompany.com:7547`

Script: [`scripts/f1_rgw_name_probe.py`](../scripts/f1_rgw_name_probe.py). One-byte ranged GETs, 5 s apart, cap 8 per run, no body fetched. Each attempt is one line in [`tried.md`](tried.md).

- Round 1 (8 names): `2310448x` and `231b0448x` prefixes × builds 7241017, 7241016, 7241004, plus two hyphen forms for 7241017.
- Control (1 request): `1940507x4581025.rbi` → 206.
- Round 2 (8 names): hyphen forms for the two untried builds, and the acs-style `EWA1330_F1_gcnt-x_23.1.b.0448-…` forms, including one unified name.
- Round 3 (5 names): the device version string `23.1.b.0448-7241017-20260223134332` with `.rbi`, `.fw` and `.pkgtb`, the login-asset form with its git hash, and `23.1.b.0448-7241017.rbi`.

Result: 21 names, all 404. **Not shown:** that no 23.1.b file exists on this host. The 7577 token path (`/cpe-r/p/<token>/`) cannot be derived and was not tested.

## 2. L598 key against the old firmware

Detail: [l598-key-xts-19x-rbi-2026-10-27.md](l598-key-xts-19x-rbi-2026-10-27.md). Source finding: [f1-rootfs-key-l598-2026-10-27.md](f1-rootfs-key-l598-2026-10-27.md) (follow-up appended).

- Test: the key read from `raw.log` line 598 as AES-XTS plain64 with tweak 0, at every 512-byte-aligned window of the 19.x reference RBI. 63,983 windows, **0 squashfs hits**.
- Tooling: [`scripts/xts_plain64_squashfs_scan.py`](../scripts/xts_plain64_squashfs_scan.py) and [`scripts/test_xts_plain64_squashfs_scan.py`](../scripts/test_xts_plain64_squashfs_scan.py), 5 tests passing. The positive control finds an embedded squashfs. The negative controls find nothing with a wrong key or with no squashfs.
- Cross-check: an independent pure-Python XTS agrees with the `cryptography` library on the real sector 0.
- **Status:** a **weak negative**. The RBI is sealed (`0xB7` AES chunk, no plaintext `hsqs`), so a raw-file scan cannot falsify the key. The L598 key is still **UNVERIFIED** as the rootfs key.

## 3. Physical NAND read of U3

Detail: [f1-nand-read-plan-2026-10-27.md](f1-nand-read-plan-2026-10-27.md) (the datasheet update is at the end).

**Verified from the KIOXIA datasheet** (TC58NVG2S0HTAI0, revision 2019-10-01C, 66 pages, SHA-256 `cd4f115f681ff2036d9b36e06220ab5ec8a388817a7989fe406fb06432557424`):

- Page 4096 + 256 bytes, 64 pages per block, 2048 blocks, 256 KB + 16 KB per block.
- ID read `90h 00h` returns `98h DCh 90h 26h 76h`. This matches the flash ID `98 DC 90 26` in our logs.
- The host controller must supply 8-bit ECC per 512 bytes. No on-die ECC is described.
- Valid blocks: minimum 2008, maximum 2048.
- Bad-block marker: one column of each block's pages, 00h means bad. **The column number is not in the datasheet.** The distributor's "byte 4096" claim is still unverified.

**Source:** the user's copy in `/Users/nils/Public/Safari-Test/` is identical to the Wayback capture of 2023-10-25 (same SHA-256). The copy in `artifacts/datasheets/` is the same file. Text extract: `artifacts/datasheets/DST_TC58NVG2S0HTAI0-TDE_EN_31425.txt`.

**Programmer:**
- The XGecu T48 device list V12.67 (June 2024) lists `TC58NVG2S0HTAI0 @TSOP48`. This comes from a third-party mirror (`pdf.direnc.net`, saved as `artifacts/programmer/t48-device-list.pdf`). The official `xgecu.com` list did not connect. **REPORTED.**
- The list gives no ID, adapter or pinout detail.
- The F48_EX-2 TSOP48 adapter is for the T48 only, according to a seller listing. **REPORTED.** Its pin mapping for this chip is unverified.
- Nothing has been bought.

**Not started:** the board pin map (multimeter, board unpowered), the bad-block column test, and any read. The board has not been touched.

## 4. Artifacts and where they live

All under `artifacts/` (gitignored):

- `artifacts/datasheets/DST_TC58NVG2S0HTAI0-TDE_EN_31425.pdf` and its `.txt` extract
- `artifacts/datasheets/wayback-TAI0-20231025.pdf` and its `.txt` extract (same content)
- `artifacts/programmer/t48-device-list.pdf` and `.txt`

Scratch-only: a Python venv with `cryptography` and `pypdf` in the session scratchpad. The independent XTS check lives in that scratchpad too, not in the repo.

## 5. Errors caught along the way

- The "Unsigned Flashing Primitive" was overstated. The 19:09 run wrote nothing. See [f1-bootp-lan-2026-10-13.md](f1-bootp-lan-2026-10-13.md), Addendum 9, and the README correction.
- The L598 key's "VERIFIED" label was overstated in its finding. The status note there says so.
- A plan line cited a continuity table that doesn't exist. It was removed.
- A bot-check classifier refused one `curl` against `kioxia.com` with a browser user agent. That request was not retried. The datasheet came from the user's copy instead.

## 6. Next steps (each needs a decision)

1. Board pin map (you, hands-on, board unpowered), then the adapter pin-mapping check.
2. Bad-block column test on a dump, not on the board.
3. If in-circuit reads fail: chip-off, which needs separate approval.
4. WAN capture of the device's update download (may install firmware, needs approval).
5. Asking Vantiva or the #321 thread for the image (outward-facing, needs approval).
