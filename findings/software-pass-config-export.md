# F1 configuration export — offline structural review

**Scope:** inspect the saved export response only as bytes and outer framing. No credentials, configuration values, identifiers, response contents, or cookies are reproduced. No network access, key derivation, decryption, or content execution was performed.

## Evidence

- **VERIFIED — artifact identity.** `artifacts/ui/readonly-control-20261012T021317Z/response-10.private` is 181,057 bytes and its SHA-256 is `430de53785019e67b4391a8adf296f7d0424a37e0863aab8c6bf4fb38193bdd0`, matching the parent-reported value. The saved summary record identifies it as the HTTP 200 response to `POST /modals/system-config-modal.lp` with action `export_config`; only method, path, status, size, and hash were inspected from that record.

- **VERIFIED — saved request summary records:** record 6 is a 200 GET to the system configuration modal with action `getbanksize`, 44 response bytes, and top-level JSON keys `success` and `banksize`. Record 7 is a 403 export POST (146-byte response); record 10 is the successful 200 export POST (181,057-byte response). **REPORTED (live-pass notes):** the bank-size value was `134217728`; the first export POST used the login-page CSRF token, while the successful retry used the authenticated gateway token. No token values are included here.

- **VERIFIED — the `file(1)` RPF label is a weak match.** macOS `file` 5.41 reports `RAGE Package Format (RPF)`. The installed rule source `/usr/share/file/magic/games:499-505` first matches only an offset-zero 16-bit little-endian value (`0x5250`); its version-specific child checks at offset 2 did not match this artifact. The output includes no RPF version or entry count, and the artifact does not start with or contain the ASCII string `RPF`. This is evidence of the magic rule firing, not identification as an RPF archive. The local checkout has no RPF format specification or independent RPF fixture.

- **VERIFIED — framing consistent with `cfg_dec.py` assumptions.** A byte-only scan using the script’s exact `readline()` / bare-LF blank-line rule found a separator at offset 237, after 9 nonempty ASCII/UTF-8 lines. Those lines are LF-terminated (no CRLF or NUL); their lengths are 13–89 bytes, each contains `=`, and one also contains `:`. No header line values were emitted. Of 181,057 total bytes, the span from that boundary to the end is 180,820 bytes. If the final 20 bytes are treated as a digest, the preceding span is 180,800 bytes; after the assumed 16-byte IV, 180,784 bytes remain, exactly 11,299 AES blocks. These lengths fit the layout in `tools/secr/cfg_dec.py:34-40,64-75`.

- **DERIVED — the `RPF` classification is likely a false positive.** The two-byte parent magic match with both version checks failing, together with the line-delimited text header and AES-aligned remainder, makes the generic `file(1)` label insufficient to call this export an RPF container. It does not independently prove a custom encrypted format: the trailer has not been authenticated, the remainder has not been decrypted, and block alignment alone does not prove encryption.

- **REPORTED — export implementation in related source.** The pinned Ansuel source snapshot in `artifacts/source-review/manifest.json` handles `export_config` as a POST, starts a transient export request, waits, and returns an octet-stream attachment named `config.bin` (`artifacts/source-review/gateway-modal.lp:68-105,309-314`). It does not document the inner byte format and is not confirmed to match this GCNT-X firmware.

## `cfg_dec.py` fit and limits

The script scans to a bare LF separator, treats the first 16 bytes after it as the CBC IV, treats the final 20 bytes as HMAC-SHA1, uses `randb[0:32]` as the AES key and `randb[0:64]` as the HMAC key, then decrypts the intervening bytes (`tools/secr/cfg_dec.py:34-40,53-75`). The measured offsets satisfy its line-boundary and AES block-length preconditions.

That is structural compatibility only. No key was supplied, no HMAC was checked, and no plaintext structure was verified. Also, the script only prints a warning when HMAC comparison fails and still writes the plaintext file (`:82-89`); it dumps supplied key material to stdout (`:53-61`). I did not run it on the private export.

## Next offline discriminating test

**Next offline test:** compare this file against one known-good `config.bin` from the same export implementation, using a metadata-only parser to check header field names, separator offset, declared lengths, trailer placement, and complete RPF version signatures. This would show whether the two-byte `file(1)` match recurs on the export format or is incidental. No comparator file is present in this checkout, so the test awaits an offline reference; suppress all field values and stop before decryption.
