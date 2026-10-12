# GCNT-X reference RBI (19.x) — offline notes

**Scope:** Mac-only analysis of `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`. **Do not flash** on the live Telia F1 running **23.1.b**.

| Field | Value |
|--------|--------|
| Logical build (filename / issue #321) | **19.4.0507-4581025** (`1940507x4581025.rbi` on `rgw.teliacompany.com:7547`) |
| Size | 32 759 365 bytes |
| SHA-256 | `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de` |
| Live unit (out of scope for flashing) | GCNT-X, **23.1.b.0448-7241017-20260223134332** |

## Tooling run (this session)

| Script | Result |
|--------|--------|
| `scripts/inspect_rbi.sh` | OK → `artifacts/logs/rbi-inspect-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.txt` |
| `scripts/binwalk_scan.sh` | OK → no signatures; entropy PNG updated |
| `scripts/verify_squashfs.sh` | No extract tree (decrypt blocked) |
| `scripts/attempt_rbi_decrypt.py` | **Failed** (no OSCK) → `artifacts/logs/decrypt-attempt-19x.txt` |
| Cloned under `tools/` | `hack-technicolor`, `Decrypt_RBI_Firmware_Utility`, `secr` (reference only) |

Homebrew: `binwalk` 3.1.0, `squashfs-tools` / `unsquashfs` present. Java/Maven **not** installed — Ansuel GUI decrypt utility not compiled; logic replicated in Python (`pycryptodome` in `tools/venv/`).

## BLI2 header (parsed)

```
magic: BLI2
fim: 23
fia: KN
prodid: 0
varid: TL
version: 0.0.0.0          # header version field; marketing build is 19.4.0507 per URL/name
data_offset: 363
data_size: 32759002
timestamp: 0x27987416
boardname: GCNT-X
prodname: Technicolor EWA1330
varname: EWA1330
tagpparserversion: 200
flashaddress: 0x117c0000
payload_first_byte: 0xb7   # B7 = AES-encrypted payload chunk (BLI2 seal)
```

Cleartext `strings` in the file are limited to the header/metadata region (`GCNT-X`, `Technicolor EWA1330`, `EWA1330`, `BLI223KN0`). No `teliasmartrgw`, `dropbear`, `tchroot`, or URL paths appear in the sealed bulk (~31 MiB high-entropy ciphertext).

## Decrypt / unseal status

| Step | Status | Detail |
|------|--------|--------|
| OSIK signature strip (`0xB8`) | Not reached | Chain starts at `0xB7` decrypt |
| OSCK AES unwrap (`0xB7`) | **Blocked** | No **GCNT-X** / EWA1330 key in community DB |
| `bli_unseal` on router | Not run | Requires rooted gateway + on-device tools |
| Ansuel `Decrypt_RBI_Firmware_Utility` | Not run | `board.java` lists **GCNT-N** only, not **GCNT-X** |
| Brute OSCK | **57 keys tried** | Community `osck/` + serial/MAC/logviewer derivations + Ansuel `board.java` keys — all `bad_osck` at first AES layer (see `findings/rbi-crypto-debug.md`) |
| Logviewer “key” from #321 | **Not OSCK** | 16-byte value; does not decrypt RBI |

**Conclusion:** Offline decrypt on this Mac is **not possible** without extracting **GCNT-X OSCK** from hardware (root shell / NAND / `secr`-style dump) or a community-published `GCNT-X.osck`.

Expected on-device pipeline (when OSCK is known), from [hack-technicolor Upgrade](https://hack-technicolor.readthedocs.io/en/stable/Upgrade/):

```bash
cat file.rbi | (bli_parser && bli_unseal | dd bs=4 skip=1 seek=1 of=file.bin)
```

Decrypted bank images should begin with four `0xFF` bytes before binwalk finds squashfs.

## Binwalk / filesystem extract

- **RBI (sealed):** binwalk reports **no** squashfs, uImage, gzip, or tar at offset 0 (expected).
- **`binwalk -e`:** nothing extracted.
- **`artifacts/extracted/19x-reference/`:** not populated (no decrypted `.bin`).
- **Squashfs:** **no** — cannot run `unsquashfs` without decrypted payload.

Logs: `artifacts/logs/binwalk-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.txt`, entropy `artifacts/logs/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.png`.

## Sibling boot log (19.4.0856, not this file)

A public serial log for **19.4.0856** on GCNT-X is already quoted in [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md). It is not a decrypt of this 19.4.0507 RBI. It does fix the layout this header is aimed at: TLV `flashaddress 0x117c0000` is `bank_1` on that boot, banks are 60 MiB, and the kernel is **aarch64 4.1.52** with `.r2secr=0x17fdf000`. The paste records `OSCK Loaded!` and does not contain key bytes. Published `r2secr.arm.4.1.38.ko` does not match that kernel.

## Strings / Ghidra prep (from what we have)

Until decrypt succeeds, RE targets are **header tooling** and **WAN-captured 23.1.b RBI**, not this blob’s userspace. The 19.4.0856 log names the userspace to expect after unseal (`squashfs` + UBIFS `rootfs_data`, `/lib/mount_root/*`, `hostapd`, `/bin/smd`).

| Target | In sealed 19.x RBI? | Notes for later extract |
|--------|---------------------|-------------------------|
| `dropbear` / SSH paths | No (encrypted) | Enable via rooted overlay per hack-technicolor upgrade guides |
| `tchroot` | No | #321: SSH user name on VLAN-facing service when rooted |
| `teliasmartrgw` / `lcm.` URLs | No | Live F1 UI/CWMP; hunt on 23.1 WAN capture |
| `rgw.teliacompany.com` | No | Source host for this RBI download |
| `core-lcm`, `transformer`, `cwmpd` | No | Ghidra on **decrypted** squashfs ELFs (AArch64) |

## Comparison to 23.1.b goals

| Topic | 19.4 reference RBI | 23.1.b on hardware |
|--------|-------------------|---------------------|
| Board / BLI2 container | Same **GCNT-X**, **BLI223KN**, var **TL** | Same board mnemonic |
| Offline decrypt | **No OSCK** | Same blocker until key extracted |
| Public RBI URL | `rgw.teliacompany.com:7547` (this file) | No stable public URL; LCM errors in `artifacts/logs/lcm-23.1*.json` |
| Downgrade / flash 19.x on 23.1.b unit | **Brick / lock risk** | Documented in #321 — treat as lab-only |
| RE value | Header layout, flash address `0x117C0000`, sealed pipeline | Need **23.1.b** RBI via WAN mirror or rooted dump for diff |

## Next offline steps (no hardware flash)

1. Obtain **GCNT-X OSCK** from a rooted 19.x bank (or share via hack-technicolor `osck/`) → rerun `scripts/attempt_rbi_decrypt.py` / Ansuel tool.
2. Capture **23.1.b** RBI on mirrored WAN (`scripts/wan-capture.sh`) — same decrypt path once OSCK confirmed for board.
3. After decrypt: `binwalk -e` → `unsquashfs` into `artifacts/extracted/19x-reference/` → Ghidra AArch64 on `/usr/bin`, `cwmpd`, LCM helpers.
