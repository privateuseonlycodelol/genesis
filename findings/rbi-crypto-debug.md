# RBI crypto debug — GCNT-X 19.x reference (offline)

**RBI:** `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`  
**SHA-256:** `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de`  
**Live unit (not touched):** SN `CP2242AD8AN`, MAC `A0:B5:3C:C6:62:82`, FW `23.1.b`

## Algorithm (Type 2 Homeware / BLI2)

| Stage | Magic | Meaning |
|-------|-------|---------|
| File container | `BLI2` + FIM/FIA (`23`/`KN`) | Static header + TLV metadata, then sealed payload |
| First payload chunk | `0xB7` | AES-256-CBC envelope: OSCK unwraps inner key, second AES-CBC decrypts bulk |
| Follow-on (typical) | `0xB8` | OSIK SHA-256 signature strip (skipped in PC tools) |
| Terminator | `0xB0` / `0xB4` | Cleartext skip or zlib inflate → flash image (`0xFF` padding, squashfs, etc.) |

Crypto chain matches **Ansuel `Decrypt_RBI_Firmware_Utility`** (`rbi_reader.java` `decryptPayload`) and **`tools/secr/blidec_enhanced.py`**: after `0xB7`, layout is `MUTE`, newline, BE `payload_size`, IV₁ (16), wrapped key (48), IV₂ (16), ciphertext.

On-router equivalent (requires gateway binaries + in-kernel OSCK):

```bash
cat file.rbi | (bli_parser && bli_unseal | dd bs=4 skip=1 seek=1 of=file.bin)
```

`bli_parser` / `bli_unseal` are **not** shipped in `hack-technicolor` (docs only); they live on the gateway filesystem when rooted.

## BLI2 header (this file)

| Field | Value |
|--------|--------|
| `magic` | `BLI2` |
| `fim` / `fia` | `23` / `KN` |
| `prodid` / `varid` | `0` / `TL` (Telia) |
| `version` (header) | `0.0.0.0` |
| `data_offset` | **363** (`0x16b`) |
| `data_size` | 32 759 002 |
| `timestamp` TLV | `0x27987416` |
| `boardname` | **GCNT-X** |
| `prodname` / `varname` | Technicolor EWA1330 / EWA1330 |
| `tagpparserversion` | 200 |
| `flashaddress` | **0x117c0000** |

### Seal boundary (hex)

TLVs end at 363; payload begins with `b7 4d555445 0a` + BE size `0x01f3dcda` (32 758 992).

```
0000015b: 413133333020033230308104117c0000
0000016b: b74d5554450a01f3dcd09d50b329960e
0000017b: 9b36866678955644375473aecc3addb0
```

First `0xB7` layer fields:

- IV₁: `9d50b329960e9b368666789556443754`
- Wrapped key block (48 B): `73aecc3addb038ac44ed75d194166aa5e2683868e079aa386f5cf5c294cf2f7d211858ed5e94525cdb9d526a8b2efedb`
- IV₂: `86963b82c842b86b37a97b930da15cb3`

Full inspect log: `artifacts/logs/rbi-inspect-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.txt`

## Tooling status

| Tool | Result |
|------|--------|
| `hack-technicolor` (`git pull`) | Already up to date; **37** `osck/*.osck`, **no `GCNT-X.osck`** (only **`GCNT-R.osck`** in GCNT* family) |
| `bli_parser` / `bli_unseal` | Not in repo; **cannot run offline** without router copy or separate leak |
| `Decrypt_RBI_Firmware_Utility` | Cloned; **`board.java` has `GCNT-N`, not `GCNT-X`**; **Java/Maven absent** on host (`java` not installed) |
| `secr` (`eripv2.py`, `blidec_enhanced.py`) | Present; extraction path needs **eripv2 MTD dump + ECK from `r2secr` ko** → `RIP_ID_OSCK` (`0x0121`) |
| Python trials | `scripts/attempt_rbi_decrypt.py` (PyCryptodome in `tools/venv/`) |

### Failure modes (documented)

| Failure | When |
|---------|------|
| `bad_osck` | Wrong 32-byte OSCK at first `0xB7` AES unwrap (PKCS padding invalid) — **all offline trials** |
| `osck not provided` | `blidec_enhanced.py` without `--osckey` on `0xB7` |
| `Can't recognize magic bit!` | Ansuel utility after wrong OSCK (inner stream still encrypted) |
| `bli_unseal` hang/OOM | Documented on low RAM; use USB path (#128) — **N/A offline** |
| Missing `GCNT-X` in GUI board list | Manual 64-hex OSCK entry would work **if** key were known |

## Keys tried (systematic offline)

Run: `tools/venv/bin/python3 scripts/attempt_rbi_decrypt.py` → `artifacts/logs/decrypt-attempt-19x.txt`

Categories:

1. **All community `.osck`** under `tools/hack-technicolor/osck/` (37 boards, incl. `GCNT-R`, Telia `VDNT-O_Telia`, etc.)
2. **Ansuel `board.java` embedded hex keys** (every `addOsKeys` 64-char string, incl. `GCNT-N`)
3. **Logviewer leak [#321](https://github.com/hack-technicolor/hack-technicolor/issues/321):** `4d17f88a54003ce68362bbf7b1c70d1d` as pad32, doubled to 32 B, SHA-256 — **not OSCK** (16-byte diagnostic token per issue discussion)
4. **Serial variants** for live SN `CP2242AD8AN` (case, strip `CP`, pad32, SHA-256)
5. **MAC** `a0:b5:3c:c6:62:82` (raw 6 B pad32, colon forms, SHA-256)
6. **Board/product strings** (`GCNT-X`, `EWA1330`, `BLI223KN`, serial+board combos)

**GitHub code search** for `GCNT-X.osck`: API requires auth; manual review shows **no published GCNT-X OSCK** (repo docs: “OSCK Not Known” for this board).

### Closest error

Every candidate stops at the **first `0xB7` layer** with **`bad_osck`** (AES unwrap of the 48-byte inner key fails PKCS#7). No candidate reached `plain_b0`, `inflate`, or a secondary magic (`0xB8`/`0xB4`).

**Decrypt success: false.** Last run: **57** unique 32-byte keys (`bad_osck`: 57) — see `artifacts/logs/decrypt-attempt-19x.txt`.

Cross-check: `blidec_enhanced.py --osckey GCNT-R.osck` reaches `Layer type B7` then **`ValueError: Invalid key size (0) for AES`** (bad unwrap → empty inner key). Python trial maps the same root cause to **`bad_osck`** at PKCS#7 check.

## #321 notes (offline applicability)

| Item | Applicable offline? |
|------|---------------------|
| Logviewer modal `/modals/logviewer-modal.lp` | Explains **ACS URL discovery**, not RBI keys |
| `NsecondGenTechSsh.sts` on `rgw.teliacompany.com:7577` | Operator script object; **not** OSCK |
| NAND / `eripv2` + `cwmp.conf` OSCK mention | **Yes** — correct extraction path once hardware dump exists |
| `tchroot` SSH user | On-device after root; irrelevant to PC decrypt |

## Next hypotheses (realistic)

1. **Extract `RIP_ID_OSCK` (0x0121)** from lab hardware: UART → root or `secr` (`dd if=/dev/mtd5`, `r2secr.*.ko` + `eripv2.py`) on **GCNT-X** (19.x bank safer than flashing 23.1.b unit).
2. **Rooted `bli_unseal`** on same board family — OSCK stays in kernel/secstore; no derivation from SN/MAC alone.
3. **Community share** — upload `GCNT-X.osck` to hack-technicolor (as done for `GCNT-R`).
4. **23.1.b RBI capture** (WAN mirror) — same crypto, confirms OSCK unchanged across minor FW; still needs key once.
5. Optional: install **Temurin JRE** and run Ansuel GUI with a future OSCK hex to cross-check Python.

**Do not flash** reference 19.x onto the live `23.1.b` Telia F1.
