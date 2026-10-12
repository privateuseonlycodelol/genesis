# RBI parser/decryptor validation pass

**Scope:** offline validation of the repository's BLI2 header parser and B7 payload helper, plus a bounded read-only search of public primary-source repositories. No candidate-key search, firmware download, device access, or firmware modification was performed.

## Evidence

**VERIFIED — real fixture identity and independent header read.** The ignored input `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` has SHA-256 `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de`. `rbi_header.parse_header` and a separate `struct`/TLV reader in [test_rbi_validation.py](../scripts/test_rbi_validation.py) agree on BLI2 / 23 / KN, product ID `0`, variant ID `TL`, `data_offset=363`, `data_size=32,759,002`, and the GCNT-X, EWA1330, timestamp, and flash-address TLVs. The size ends exactly at EOF. The real payload begins `B7 MUTE LF`; its B7 size is 32,758,992, equal to the remaining bytes after the ten-byte B7 prefix.

**VERIFIED — before/after malformed-header checks.** The initial probe showed that the old parser accepted a 308-byte synthetic buffer whose declared `data_offset` was 48, accepted magic `NOPE` and a `data_size` extending beyond EOF, and returned `abc` from a board-name TLV that advertised eight bytes but contained only three. A tag without a length raised `IndexError`. After the changes below, all six malformed cases raise `ValueError`; these inputs are invalid-header controls, not real RBI fixtures.

**VERIFIED — synthetic crypto control only.** A deterministic two-layer B7 payload was encrypted with dummy keys using PyCryptodome 3.24.0. The independent `cryptography` 50.0.2 backend decrypted both AES-CBC layers, checked PKCS#7 padding, and recovered the predefined inner key and plaintext. `attempt_rbi_decrypt.process_payload` returned the same plaintext with status `plain_b0`. This validates that code path against generated data only. It does not establish the GCNT-X OSCK, the real RBI's successful decryption, or the vendor's exact deployed behavior.

**VERIFIED — synthetic B7 negative cases.** With the controlled positive fixture, a wrong dummy key and a truncated wrapped-key ciphertext both produce `bad_osck`. The helper does not distinguish a wrong key from that truncation. It also still returns the known plaintext when the B7 length field is changed to `1` and a trailing byte is added after the second-layer ciphertext: the length field is not checked, and the helper drops the trailing partial block. These are local-helper observations only. B7 behavior was deliberately left unchanged because no real matching firmware/key control is available.

**DERIVED — local known-good fixture/key pair is unavailable.** A local inventory found one RBI/BLI container: the GCNT-X reference above. The community OSCK directory has 37 keys and none named for GCNT-X; `board.java` contains GCNT-N but no GCNT-X entry. No local matching real firmware/key pair was found. Wrong-board keys were not retried. This inventory does not establish that no pair is available elsewhere.

**VERIFIED — public primary-source check found no matching BLI2/B7 control.** The bounded GitHub searches used `site:github.com BLI2 RBI B7 fixture OSCK decrypt test`, `site:github.com "0xB7" "BLI2" RBI firmware decrypt`, and `site:github.com "integritycheck" "BLI223WP0"`, then inspected the locally available [Ansuel RBI decryptor repository](https://github.com/Ansuel/Decrypt_RBI_Firmware_Utility) plus the primary [mswhirl BLI223 decryptor repository](https://github.com/mswhirl/bli223dcryptex). The utility source has a B7 AES-CBC path and board-specific static keys, but its board list has GCNT-N and no GCNT-X, and the checked-out repository contains no sample RBI/BLI fixtures or test vectors. The BLI223 repository's README publishes output for `mst_tg582ndb_r10.2.5.2_bm.bin` with header type `BLI223WP0`, a `MUTE` marker and an AES key, and reports a matching legacy-header integrity digest. Its README-described sample is an older BLI223/TG582n case, not an independently known-good BLI2/B7 fixture/key pair. I did not download the large sample image, retrieve firmware from ISP endpoints, or try the unrelated published key against GCNT-X. The search was bounded and does not prove that no public matching pair exists.

## Reference implementation cross-checks

The local Java utility source independently describes a 32-bit `data_offset` at `0x28`, reads it as four bytes, and starts dynamic TLVs after the `0x134` fixed-plus-gap header. Its source was inspected but could not be run: the host's `java` command reports that no Java Runtime is installed.

For this reference fixture, `blidec_enhanced.py`'s 16-bit read at `0x2a` yields the same offset (`363`) as the 32-bit field at `0x28`, because the stored field is `00 00 01 6b`. The 16-bit read remains a width limitation for offsets above `0xffff`; this fixture does not demonstrate that failure.

The legacy Python and Java decryptors were source-audited only. Neither was run against a real key/firmware pair. The legacy Python tool also strips wrapped-key padding by its final byte without checking the full PKCS#7 pattern; the current project helper correctly checks the unwrap padding and requires a 32-byte inner key, while it tolerates invalid second-layer padding. That tolerance was not exercised against a real RBI and remains a question for format compatibility.

## Work and reproducibility

Parser changes in `scripts/rbi_header.py` now require the `BLI2` magic, a `data_offset` at or beyond `0x134`, a data region within EOF, and complete TLV tag/length/value bytes. Those malformed cases raise consistent `ValueError`s. The real reference fixture still passes its hash, metadata, TLV, B7-size, and exact-file-boundary regression checks. No B7 crypto or framing semantics were changed.

Command run after the changes:

```sh
tools/venv/bin/python scripts/test_rbi_validation.py
```

It exited 0 and printed the real-fixture checks, malformed-header rejections, independent synthetic crypto control, synthetic B7 negative cases, and the unchanged framing-gap observation. The script reports installed crypto-library versions dynamically. Full output is preserved in ignored `artifacts/logs/software-pass-crypto-validation.txt`. It does not call `run_trials` or enumerate OSCK candidates, and it does not decrypt the real RBI.

Local fixture/key inventory command:

```sh
python3 - <<'PY'
from pathlib import Path
for parent in [Path('artifacts/firmware'), Path('tools')]:
    files = [p for p in parent.rglob('*') if p.is_file() and p.suffix.lower() in {'.rbi', '.bli'}]
    print(parent, len(files), [str(p) for p in files])
oscks = sorted(Path('tools/hack-technicolor/osck').glob('*.osck'))
print('community OSCK files', len(oscks), 'GCNT-X names', [p.name for p in oscks if 'GCNT-X' in p.name.upper()])
board_java = Path('tools/Decrypt_RBI_Firmware_Utility/src/main/board.java').read_text(errors='replace')
print('board.java GCNT-X', 'GCNT-X' in board_java, 'GCNT-N', 'GCNT-N' in board_java)
PY
```

Observed: one container (the reference RBI), 37 community OSCK files with no GCNT-X filename, and `board.java` has GCNT-N but not GCNT-X. Raw RBI and key artifacts remain under ignored paths; no key bytes or firmware data were copied into this report.

## What remains open

- No independently known-good **real** BLI2/OSCK pair is available in the local tree, so the real firmware decrypt path remains unvalidated.
- The Java reference could not be executed on this host.
- The B7 helper's size-field and partial-block handling remains unvalidated against a real matching firmware/key pair; these local malformed-input results do not show that the vendor parser accepts the same input.
- Highest-value next validation is a real matching RBI/OSCK fixture from an authorized, offline source. It would verify real payload-size semantics and the complete B7-to-inner-layer path without key guessing.

## Parser changes completed

`scripts/rbi_header.py` now requires BLI2 magic, rejects offsets below `0x134` or past EOF, rejects payload sizes extending past EOF, and rejects incomplete TLV headers or values with `ValueError`. The real fixture regression and malformed-header controls pass. B7 size validation and partial-block rejection remain intentionally unchanged pending a real positive control.
