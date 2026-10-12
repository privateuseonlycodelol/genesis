# F1 config export — Tier 1 offline decrypt pass (2026-10-12)

Scope: three saved authenticated `export_config` blobs only. No live router traffic, no key material copied into Git, no plaintext or header values printed in this note.

## Evidence found

| Claim | Status | Basis |
| --- | --- | --- |
| Container matches Technicolor `THENC` family | **VERIFIED** | All three exports: `PREAMBLE=THENC`, `BACKUPVERSION=1.00`, `BOARDMNEMONIC=GCNT-X`, labels `CIPHERKEY=GW` and `SIGNATUREKEY=GW` (two-character **slot labels**, not hex keys) |
| Layout | **VERIFIED** | Header ends at offset 235, body at 237: 16-byte IV, AES ciphertext, final 20-byte trailer; ciphertext block-aligned |
| Signed region | **VERIFIED** | HMAC-SHA1 over `header + "\n\n" + IV + ciphertext` (file minus last 20 bytes), same as public [technicolor-config-decrypt](https://github.com/antnks/technicolor-config-decrypt) PoC |
| Cipher | **DERIVED** | AES-256-CBC, PKCS#7; AES key = first 32 bytes of 64-byte `RIP_ID_RANDOM_KEY_B`; HMAC key = full 64 bytes (`/proc/rip/0108`, `tools/secr/cfg_dec.py`) |
| Decrypted plaintext on this unit | **BLOCKED** | No `RIP_ID_RANDOM_KEY_B` / `mtd5` / `proc_rip_0108` artifact in the workspace; **55+** offline HMAC trials (header/metadata, 37 OSCK files) — **zero** matches; see [`f1-hardware-key-blocker-2026-10-12.md`](f1-hardware-key-blocker-2026-10-12.md) |
| Export deltas | **VERIFIED** | Headers byte-identical across `response-10` vs `response-13`; first difference at offset 237 (IV). Ciphertext length +32 bytes between those two exports (+80 vs latest `response-07`), consistent with time-varying config size under CBC |

Artifacts (private, gitignored):

- `artifacts/ui/readonly-control-20261012T021317Z/response-10.private` — SHA-256 `430de53785019e67b4391a8adf296f7d0424a37e0863aab8c6bf4fb38193bdd0`
- `artifacts/ui/readonly-control-20261012T021317Z/response-13.private` — SHA-256 `90d9833b519ddad18b183321196b8f0584ece549154ccb17081417a6434fe390`
- `artifacts/ui/readonly-control-20261012T051406Z/response-07.private` — SHA-256 `61dee5c7b4511afb0b2dababea162be3cd6a0e2a50b561fda056ccdeeb7fed3f`

## Work performed

Added `scripts/decrypt_f1_config_export.py` (parse, HMAC verify, decrypt; never prints keys or plaintext) and `scripts/test_decrypt_f1_config_export.py` (synthetic round-trip + structure checks on the real export).

```sh
tools/venv/bin/python scripts/test_decrypt_f1_config_export.py
tools/venv/bin/python scripts/decrypt_f1_config_export.py \
  artifacts/ui/readonly-control-20261012T021317Z/response-10.private --inspect-only
```

Related GUI source (`artifacts/source-review/gateway-modal.lp`) only copies a transient `config_export.*` file from transformer RPC; it does **not** define the binary envelope. Producer logic remains in shipped 23.1.b userspace (not available decrypted locally).

## What changed

Tier 1 narrowed the problem: the export is **not** a novel format and **not** decryptable from header fields alone. `GW` names the gateway RIP key slot; decryption is keyed to per-device `0x0108` material, the same class as legacy Technicolor backup — **orthogonal to OSCK / RBI**.

Until that 64-byte blob exists, offline analysis stops at structure and cross-export size deltas. Community RBI work does not substitute for `RANDOM_KEY_B`.

## Next attack on the problem

Highest-value unblock (still software-only once material exists):

1. Obtain `RIP_ID_RANDOM_KEY_B` via authorized `eripv2.py` on an `mtd5` dump, or `dd` of `/proc/rip/0108` with temporary root/USB — then run:

   ```sh
   tools/venv/bin/python scripts/decrypt_f1_config_export.py \
     artifacts/ui/readonly-control-20261012T021317Z/response-10.private \
     --randb /path/to/RIP_ID_RANDOM_KEY_B_0x0108.bin \
     --output /tmp/config.plain.private
   ```

2. If HMAC passes, classify plaintext (expected XML/UCI-style per public PoC) and mine for firmware URLs, credentials, and transform paths — without re-exporting secrets into `findings/`.

Secondary: locate **23.1.b** backup encrypt implementation in a decrypted rootfs (needs OSCK or leak) to confirm no `GW`→key derivation change on GCNT-X.
