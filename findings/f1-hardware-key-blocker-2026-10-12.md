# Config hardware key (`RIP_ID_RANDOM_KEY_B`) — decompile attempt (2026-10-12)

## Bottom line

**BLOCKED:** the config encryption key for this Telia F1 cannot be recovered by decompiling the export, the sealed 19.x RBI, community OSCK files, or the `r2secr` kernel module alone. The 64-byte material is **per-device**, lives in the **eripv2** flash partition (encrypted under **ECK**), and is only released on-box via **`/proc/rip/0108` after root** (or offline via `eripv2.py` + ECK + MTD dump).

`CIPHERKEY=GW` in `config.bin` is a **label** for that RIP slot, not the key bytes.

## Follow-up surface sweep (2026-10-12, still no key)

**VERIFIED:** `scripts/f1_config_key_probe.py` ran **119** authenticated GETs (rip/debug/api/ajax guesses, 30+ `action=` names on three modals, path traversal) — **`interesting_count=0`**. Only non-login JSON hits remained the known pair: `gateway.lp?action=scheduleReboot` (184 B) and `system-config-modal.lp?action=getbanksize` (44 B). Every other “rip/backup/debug” action on `system-config-modal.lp` returned the same **3944-byte** HTML shell as a control name.

**VERIFIED:** **42** additional HMAC trials using full export header field values (MAC, serial, build, concatenations, header SHA-256/512) — **0** matches.

**VERIFIED:** Telia `rgw` fetch of `19.5.1062` unified RBI returned **HTTP 403 Forbidden** (18-byte body), not a firmware blob.

**VERIFIED (2026-10-12 follow-up):** CUPS `file:///proc/rip/0108` as `printer-uri` → HTTP **400** / 347 bytes in under 0.2 s — **no** file read. See [f1-gateway-url-action-2026-10-12.md](f1-gateway-url-action-2026-10-12.md).

**VERIFIED:** `POST gateway.lp` `action=URL` with twelve SSRF-style `urlVal` strings → identical 17,267-byte dashboard HTML; **no** SSRF demonstrated. Same finding.

**VERIFIED:** After the key-probe burst, **new** logins via `curl` returned nginx **503** (190-byte stub) on `/` and `/login.lp` — confirmed on the owner Mac terminal as well as automation. Wait for **200** before more live work (see `findings/f1-ui-leads-23.1b.md`). Heavy parallel curls re-trigger **503** even when a lone `login.lp` check returns **200**.

Private artifacts: `artifacts/ui/key-probe-20261012T060025Z/summary.json`.

## What was executed (this pass)

| Attack | Result |
| --- | --- |
| HTTP `GET /proc/rip`, `/proc/rip/0108`, `/proc/efu` on `192.168.2.1` | **404** (nginx) — not exposed to LAN web |
| SSH **22** / **2222** | **closed** |
| Mesh / LXC `192.168.1.2`, `192.168.2.2` | **unreachable** from lab Mac |
| HMAC verify export with **37** `hack-technicolor/osck/*.osck` variants + logviewer token derivations | **0** matches |
| Header/metadata weak keys (MAC, serial, build, `GW*32`, etc.) | **0** HMAC matches (prior pass + confirmed) |
| `strings` / prior RBI decrypt matrix for GCNT-X OSCK | **57** trials, all **`bad_osck`** — no decrypted rootfs to disassemble backup code in 23.1.b |

## What “decompile” actually targets

Technicolor Homeware stores secrets in **eRIP v2** (see `tools/secr/eripv2.py`):

1. **`RIP_ID_ECK` (0x011f)** — 16-byte **ECK**, recoverable once with **`r2secr.*.ko`** + `dmesg` on a **rooted** kernel (module dumps kernel pointer to ECK; it is not in the RBI).
2. **`RIP_ID_RANDOM_KEY_B` (0x0108)** — **64 bytes** in MTD **eripv2** image, AES-wrapped with ECK (+ EIK signature on many items). `eripv2.py` walks the partition and writes `RIP_ID_RANDOM_KEY_B_0x0108-*` when ECK is correct.
3. **Config export** uses bytes `[0:32]` as AES-256-CBC key and `[0:64]` as HMAC-SHA1 key (`scripts/decrypt_f1_config_export.py`).

There is **no** public algorithm that derives `0x0108` from `GCNT-X` board name, `THENC` header, or ISP firmware — community threads confirm **two routers of the same model have different `RANDOM_KEY_B`**.

Reverse-engineering `r2secr.arm.*.ko` (ARM EABI relocatable, not stripped) explains **how to read ECK from RAM after root**, not **what your unit’s 0108 bytes are**.

## Only verified unblock paths (owned hardware)

1. **Root shell** (UART-led boot analysis, future exploit, or lab 19.x hardware — **not** established on this **23.1.b** unit):
   ```sh
   dd if=/proc/rip/0108 of=proc_rip_0108   # 64 bytes
   ```
   Then on the Mac:
   ```sh
   tools/venv/bin/python scripts/decrypt_f1_config_export.py \
     artifacts/ui/readonly-control-20261012T021317Z/response-10.private \
     --randb proc_rip_0108 --output /tmp/config.plain.private
   ```

2. **MTD eripv2 dump + ECK** (same root prerequisite for `dd` / `insmod`):
   - Checklist wrapper: `scripts/acquire_f1_config_key.sh` (edit `KO` + `MTD_DEV` for your kernel map).
   - Parser: `tools/venv/bin/python tools/secr/eripv2.py --eripv2 eripv2.mtd.bin --eckey '<from dmesg>'`

3. **NAND / chip-off** of eripv2 region — still needs ECK or broken crypto; last resort per `findings/gcnt-x-root-path.md`.

## What does not advance this key

- More export downloads (IV changes; key does not).
- RBI OSCK brute force without a **new** `GCNT-X.osck` leak.
- Treating logviewer `4d17f88a…` as OSCK or config key (tested; unrelated diagnostic token).

## Next discriminating experiment

**UART boot log on the open case** (read-only, no flash): confirm **Linux version** → `scripts/select_r2secr_ko.py` (public **19.4.0856** log is **aarch64 4.1.52**, not armv7 `p2v8`; local module **`tools/secr/r2secr.arm64.4.1.52.ko`** — [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md)). Print **`/proc/mtd`** for **eripv2** on **23.1.b**. That does not yield the key by itself but selects the right acquisition commands the moment root exists. See [rbi-crypto-attempt3.md](rbi-crypto-attempt3.md).
