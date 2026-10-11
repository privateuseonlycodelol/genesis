# RBI crypto — attempt 2 (GCNT-X 19.x)

**Reference RBI:** `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` (19.4.0507 build, SHA-256 `2d46e728…`)  
**Sibling target:** `EWA1331_EWA1330_gcnt_x_19.5.1062_4581010_unified.rbi` ([#321 URL](https://rgw.teliacompany.com:7577/cpe-r/p/tZLIYj9o/EWA1331_EWA1330_gcnt_x_19.5.1062_4581010_unified.rbi))  
**Log:** `artifacts/logs/decrypt-attempt-19x.txt` (attempt 1) · `artifacts/logs/decrypt-attempt2.txt` (this pass)

## Decrypt success

**No.** Extended trials: **88** unique 32-byte keys (37 community `.osck` + 51 new derivations). Histogram: **87× `bad_osck`**, **1× `bad_inner_key_len_47`** (false PKCS on `header_fim_fia_pad32`). No `plain_b0` / `inflate`.

---

## A) Sibling RBI comparison

| Step | Result |
|------|--------|
| `curl -fL` → `artifacts/firmware/sibling-19.5-unified.rbi` | **HTTP 403** on `:7577` path (same as `findings/decomp-kickoff.md`). Retried with browser User-Agent. |
| `:7547` short names (`1951062-gcnt-x-4581001.rbi`, long unified name) | **404** |
| Header diff vs 19.5 unified | **Not run** (no local sibling file). Community `bli_parser` post in [#321](https://github.com/hack-technicolor/hack-technicolor/issues/321) reports same **GCNT-X** / **EWA1330** / **flash 0x117C0000** as reference — expect TLV identity match; seal ciphertext will differ per build. |
| OSCK in sibling header | **None** — BLI2 TLVs do not carry OSCK; key is **RIP_ID_OSCK (`0x0121`)** in eRIPv2 only. |

---

## B) `secr` / decrypt tooling RE

| Source | OSCK derivation |
|--------|-----------------|
| `tools/secr/src/*/rip_ids.h` | Defines `RIP_ID_OSCK` `0x0121`; **no** serial/MAC/board derivation code in tree. |
| `tools/secr/eripv2.py`, `cfg_dec.py` | Extract **stored** keys from MTD dump + **ECK**; config uses `RIP_ID_RANDOM_KEY_B`, not OSCK. |
| `r2secr*.ko` / `ripdrv*.ko` strings | `rip_bl_crypto_confidkey` — kernel path names **confidentiality key**, not a PC-side formula. |
| `Decrypt_RBI_Firmware_Utility` | `board.java` has **GCNT-N**, not **GCNT-X**; keys are static hex per board, not computed. |

**New derivations implemented** (in `scripts/attempt_rbi_decrypt.py`): HMAC-SHA256 with `RIP_ID 0x0121` salt, **TL/TCH/Telia** manufacturer strings, RBI header fields (`prodid`/`varid` **0** / **TL**, `fim`+`fia` **23KN**, timestamp, flash address), device combo string — all **failed** at B7 unwrap.

### B7 / `blidec_enhanced.py` IV handling

Both our script and Ansuel/Kbios `blidec_enhanced.py` use **inline IVs in the B7 blob** (IV₁ → 48 B wrapped key → IV₂ → ciphertext). **No** extra nonce in BLI2 TLVs for B7.

**Footgun:** `blidec_enhanced.py` reads payload start as `struct.unpack_from(">H", globalheader, 0x2A)` (16-bit at `0x2A`). Correct Homeware offset is **32-bit big-endian at `0x28`** (see `header_parser.java` / `scripts/rbi_header.py`). On a full RBI file, `blidec` would seek to the wrong offset unless the stream is pre-stripped — use `rbi_header.py` offset or `attempt_rbi_decrypt.py`.

---

## C) Structural attacks (no key)

| Check | Reference RBI |
|-------|----------------|
| Trailing bytes after `data_off + data_size` | **0** (exact file size) |
| Second `BLI2` magic in first 1 MiB | **None** (only file start) |
| ZIP / gzip in header region (363 B) | **None** |
| Cleartext PEM/ssh in header gap `0x30…` | **None** |
| Cross-board community OSCK on GCNT-X | **All fail** (same as attempt 1) |

### B7 error oracle

For each trial key, first-layer AES unwrap was classified by PKCS padding byte (`b7_unwrap_oracle` in log). **~70 distinct `bad_pad_*` classes** plus a few **`bad_pkcs_*`** — consistent with **random wrong-key decrypt**, not a key-id side channel. One key (`header_fim_fia_pad32`) accidentally passes PKCS with **47-byte** “inner key” (invalid for AES-256); **not** a real unwrap.

---

## D) Tooling changes

| Artifact | Change |
|----------|--------|
| `scripts/attempt_rbi_decrypt.py` | Attempt-2 derivations, structural scan, B7 oracle logging, `--compare-sibling`, `--attempt1-only` |
| `scripts/report.sh` | Surfaces `decrypt-attempt2.txt` + link to this doc |
| `findings/rbi-crypto-attempt2.md` | This file |

Re-run:

```bash
tools/venv/bin/python3 scripts/attempt_rbi_decrypt.py
# optional when sibling file exists:
tools/venv/bin/python3 scripts/attempt_rbi_decrypt.py --compare-sibling artifacts/firmware/sibling-19.5-unified.rbi
```

---

## Best new lead (one sentence)

**GCNT-X OSCK is not derivable from published formulas or sibling RBI metadata; the only credible unlock remains per-device `RIP_ID_OSCK` from eRIPv2 (UART/`eripv2.py` + ECK) or a WAN capture while the CPE still receives a 403-gated `:7577` RBI/STS — offline guessing only produces random PKCS oracle noise.**

See also: `findings/rbi-crypto-debug.md` (attempt 1), Project doc [gcnt-x-19x-community-path.md](/cursor/stores/bc-1cfc75c5-aae2-44ff-a156-ad36d8520fd9/files/docs/gcnt-x-19x-community-path.md).
