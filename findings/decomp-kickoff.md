# GCNT-X reference RBI — decomp / RE kickoff

**Scope:** Offline analysis on Mac (`~/genesis`) only. **Do not flash** anything to the live Telia F1 (23.1.b).

**Live device:** Telia F1, board **GCNT-X**, firmware **23.1.b.0448-7241017-20260223134332**.

**Config backup (separate from RBI):** authenticated `export_config` saves are **Technicolor `THENC`** envelopes; decrypt needs per-device **`RIP_ID_RANDOM_KEY_B`** — see `findings/f1-config-export-decrypt-2026-10-12.md`. Producer source for 23.1.b is still inside sealed firmware, not in the reference 19.x RBI.

## Reference blob obtained

| Field | Value |
|--------|--------|
| Local path | `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` |
| Source URL (working) | `https://rgw.teliacompany.com:7547/1940507x4581025.rbi` |
| Logical name (issue #321) | **19.4.0507-4581025** (`1940507x4581025.rbi`) |
| Size | 32 759 365 bytes (~31.2 MiB) |
| SHA-256 | `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de` |
| `file` | `data` (no generic magic beyond custom header) |

`inspect_rbi.sh` is not present in this repo; inspection used `file`, `shasum`, `xxd`, and `binwalk` (logs under `artifacts/logs/rbi-inspect.txt`, `binwalk-reference-rbi*.txt`).

## Header / magic

First bytes (ASCII):

```
BLI223KN0....TL.........
```

Interpretation (Homeware **BLI2** container, per [hack-technicolor upgrade docs](https://hack-technicolor.readthedocs.io/en/stable/Upgrade/)):

- Magic: `BLI2` (bytes `42 4c 49 32`)
- FIM / FIA / variant fields follow (`23`, `KN`, prod var `TL`, …)
- Cleartext metadata later in the header region includes:
  - `boardname: GCNT-X`
  - `Technicolor EWA1330` / `EWA1330` (visible via `strings`)

Payload after the BLI header is **encrypted/sealed** (`bli_unseal` on-device or equivalent tooling required before squashfs/etc. show up).

## Binwalk (brew)

```
Analyzed 1 file for 85 file signatures (187 magic patterns) in ~125 ms
```

**No** embedded squashfs, uImage, gzip tarballs, or other standard partitions were reported at offset 0 — expected for a sealed RBI before unseal.

Entropy plot: `artifacts/logs/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.png` (high entropy → encrypted/compressed bulk).

## Download attempts (this session)

| URL | Result |
|-----|--------|
| `http://acs.telia.lt:8888/TCH/EWA1330_F1_gcnt-x_19.4.0856-4581012.rbi` | Connection reset by peer |
| `http://acs.telia.lt:8888/TCH/EWA1330_F1_gcnt-x_19.4.0507-4581030.rbi` | Connection reset by peer |
| `http://acs.telia.lt:8888/TCH/EWA1331_EWA1330_gcnt_x_19.5.1062_*_unified.rbi` (variants) | Connection reset |
| `https://rgw.teliacompany.com/TCH/...` (plain host, no port) | SSL timeout / connection reset |
| `http://rgw.teliacompany.com/TCH/...` | Connection reset |
| `https://rgw.teliacompany.com:7577/cpe-r/p/tZLIYj9o/*.rbi` (unified + 19.4 names) | **403 Forbidden** |
| `https://rgw.teliacompany.com:7547/1940507x4581025.rbi` | **200 OK** → saved as reference |
| `https://rgw.teliacompany.com:7547/1951062-gcnt-x-4581001.rbi` | Not tried after first success (same host pattern; try if you need 19.5 unified naming) |
| `http://131.116.22.230/1951062-gcnt-x-4581003.rbi` | Not reached in final loop (router-only host per #321) |
| `http://acs.telia.se:8888/TCH/EWA1330_F1_gcnt-x_19.4.0856-4581012.rbi` | Not reached after success |

Full curl transcript: `artifacts/logs/rbi-download-attempts.txt`.

**23.1.b RBI:** No public URL found in #321; LCM probes return `Apps was not found` for `GCNT-X` / `23.1` / `23.1.b` (`artifacts/logs/lcm-23.1*.json`). Treat **WAN capture during an operator upgrade** (or a mirror someone already captured) as the realistic path to the **23.1** blob — not GPL email, not ACS mirrors from 2024.

## Why this reference still helps for 23.1.b RE

Same **board** (`GCNT-X`) and same Homeware RBI pipeline (BLI2 → sealed image → flash layout). Differences on 23.1.b (Vantiva branding, modal/LCM changes, downgrade lock) sit mainly in **userspace and signing**, not in “unknown file format.”

Use 19.4.0507 reference to:

1. Learn BLI layout and where metadata (`boardname`, `flashaddress`, timestamps) lives.
2. Practice unseal/extract workflow once you have Linux ARM tools or a rooted 19.x bank (optional; **not** required on the 23.1 live unit).
3. Build a mental map of partition names, `core-lcm`, CWMP, and transformer paths documented in #321 for diffing against a future **23.1** extract.

**2026-10-12:** Public **19.4.0856** UART log maps `flashaddress 0x117c0000` to **`bank_1`**, 60 MiB banks, **eripv2** MTD — [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md). RBI decrypt still needs **GCNT-X OSCK** ([rbi-crypto-attempt3.md](rbi-crypto-attempt3.md)); `r2secr` module [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md).

**Related live lead (2026-10-12):** CUPS on :631 behavior is mapped without rootfs ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)). A decrypted **23.1.b** image would also supply `/etc/cups/cupsd.conf` (`Listen`, `<Location>`, `<Policy>`) to reconcile IPP vs HTTP **403**.

## Next steps — Ghidra / AI (when you have 23.1)

1. **Obtain 23.1.b RBI offline**  
   - Run `./scripts/wan-capture.sh` on mirrored WAN during Telia push (capture already started: `artifacts/captures/f1-reboot.pcapng`).  
   - Filter for `rgw.teliacompany.com`, `:7547`, `:7577`, `*.rbi`, or `lcm.teliasmartrgw.com`.  
   - Save as `artifacts/firmware/CAPTURED-23.1.b-DO-NOT-FLASH.rbi` (never commit; `*.rbi` is gitignored).

2. **Unseal to flashable `.bin`** (on a lab router or documented tooling, not the 23.1 production device if downgrade-locked):  
   `cat file.rbi | (bli_parser && bli_unseal | dd bs=4 skip=1 seek=1 of=file.bin)` — see hack-technicolor upgrade page.

3. **Binwalk / extract** on `file.bin` → locate squashfs, kernel, DTB (likely **aarch64** / cortex-a53 per #321 LCM JSON).

4. **Ghidra**  
   - Import ELF binaries from extracted rootfs (`/usr/bin`, `cwmpd`, `transformer`, `core-lcm`).  
   - Processor: **AARCH64**; base addresses from readelf if PIE.  
   - Start from strings: `acs_url`, `vlan_mgmt`, `connectionrequest_allowedips`, `tchroot`, `assistance-helper`.

5. **AI-assisted RE**  
   - Feed decompiled slices of LCM/update and CWMP TLS verification (23.1.b delta vs this 19.4 reference).  
   - Cross-reference public issue #321 state: fake ACS path, VLAN 101/254, no tch-exploit on Telia builds.

6. **Config/crypto**  
   - `config.bin` needs board **OSCK** / ISP **OSIK** (not in RBI alone). NAND dump or WAN-captured keys remain separate tracks (#321).

## Safety

- Reference firmware is for **diffing and toolchain practice** only.  
- **Do not flash** reference 19.4.0507 (or any downloaded RBI) onto a **23.1.b** unit (downgrade lock / brick risk per #321).  
- Never `git add` `*.rbi` — already in `.gitignore`.
