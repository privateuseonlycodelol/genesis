# core-lcm package channel — deep audit (2026-11-07)

Supersedes the string-level "core-lcm crypto audit (2026-11-07)" and "Container package channel (2026-11-07)" paragraphs in [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md). This pass disassembled the daemon, decompiled the native Lua installer, read the live process memory and logs, and fetched real backend content.

**No packets were sent to the router's LAN services for this audit. All device reads were over the documented root SSH. Backend fetches are the same GETs the device itself performs hourly.**

## Binary identity and linkage (VERIFIED)

`core-lcm.bin` (copied from `/opt/lcm.technicolor.com/upper/usr/bin/core-lcm`, read-only): ELF 32-bit LSB ARM EABI5, stripped, 3,826,636 bytes, SHA-256 `546f0cbd62a21c2b24877e883149126c7c5ff897b61c742911f72ef0bdcbf00c`. Built with Buildroot 2021.02.4 / GCC 10.3.0. Version strings inside: `5.0.23.21` (matches the live `tc_lcm` app1 version).

Dynamic libraries: **only** `libuci.so`, `libstdc++.so.6`, `libgcc_s.so.1`, `libpthread.so.0`, `libc.so.6`. The 2026-11-06 finding's "links libcurl with OpenSSL" is correct only in the *static* sense: debug paths show `../subprojects/curl-8.0.1/...` and `../subprojects/openssl-3.0.7/...` plus nlohmann-json 3.11.2, all statically linked. Application namespaces reconstructed by rizin: `telia::backend_client::BackendClientImpl`, `telia::package_signer::{Signature,SignatureImpl,IpkPackage,IpkPackageImpl,EncryptDecrypt}`, updater at `../src/telia/lcm/updater_internal.cpp`, signer at `../src/telia/package_signer/signature.cpp`, `../src/telia/package_signer/ipk_package.cpp`.

## Live channel configuration (VERIFIED)

- ROM (bank-1) `/etc/telia_app_config/tc_lcm`: `backend_url 'none'`, `enabled '0'`, `backend_channel 'prod'` — the channel is shipped disabled.
- Live host and container config (same file, overlay-provisioned): `backend_url 'http://lcm.teliasmartrgw.com/'`, `backend_channel 'F1_5.04_prod'`, `enabled '1'`.
- Runtime globals of the live process (PID 18103, read from `/proc/PID/mem`): the built-in URL parts are `/ipk/hw/`, `/fw/`, `/chan/`, `/sn/`, `/files/`, `/tmp/`. The constructed apps-list URL is `http://lcm.teliasmartrgw.com/ipk/hw/GCNT-X/fw/23.1/chan/F1_5.04_prod/sn/<unit-serial>`.
- `core-lcm.log` (`/opt/lcm.technicolor.com/upper/var/log/core-lcm.log`) shows the fetch and install loop of 2026-11-06: 18:33:27 fetch → `Package verified: /tmp/core-lcm_5.0.23.21.ipk` → install; then core-watchdog 5.0.23.16, **`airties_EWA1331_4.205.7.2.169_arm_cortex-a53.ipk`**, telia-systeminfo 15.0.12, telia-pub_rgw_messages 15.0.12. Repeated fetches ~hourly (18:33, 18:34, 19:46, 20:44). The Airties mesh suite is therefore one backend push away from running; on this unit its daemons were stopped by earlier lab work (see [f1-idle-services-stopped-2026-11-06.md](f1-idle-services-stopped-2026-11-06.md)), not by the channel.

## Backend exposure (VERIFIED)

From the lab host, with a plain curl and **no credentials, no cookies, no token**:

- Apps list: `GET http://lcm.teliasmartrgw.com/ipk/hw/GCNT-X/fw/23.1/chan/F1_5.04_prod/sn/<unit-serial>` → HTTP 200, JSON array of `{name, version, url, filename, kind}`. Response header `x-amzn-RequestId` (API Gateway/S3-backed CloudFront).
- Package: `GET http://lcm.teliasmartrgw.com/files/<url>/<filename>` → HTTP 200, `binary/octet-stream`, transport-gzipped tar-format ipk. Example fetched: `core-watchdog_5.0.23.16.ipk` (166,292 B gz / 184,320 B raw).

**The "token-authenticated downloads" claim is refuted.** The string `!token_string.empty()` that motivated it belongs to the statically linked nlohmann-json lexer (`../subprojects/nlohmann_json/.../lexer.hpp`), not to any app token. No authorization header exists in the daemon's memory; the backend serves the same content to an unauthenticated third-party curl.

**The "MITM needs DNS control plus an Amazon-chained cert" derivation is superseded.** `/etc/tc_lcm_backend.crt` in the container is indeed the self-signed `Amazon Root CA 1`, but the live `backend_url` is **plain `http://`**; curl never performs TLS on this channel, so no certificate of any kind is needed to intercept it. A network-position attacker (or DNS control) can read and rewrite both the apps list and the package bytes. The response memory shows the same plain-HTTP URL the daemon logs.

## Package verification (VERIFIED)

Package layout (tar-format ipk, all members):

| Member | Signature sibling |
| --- | --- |
| `debian-binary` | `debian-binary-checksum.sgn` |
| `control.tar.gz` | `control.tar.gz-checksum.sgn` |
| `data.tar.gz` | `data.tar.gz-checksum.sgn` |

Each `.sgn` is one text header line (`/tmp/signedfolder/<member>-checksum.sgn`) followed by a 256-byte **RSA-2048/SHA-256 (PKCS#1 v1.5) signature over the entire member content**. All three verify against the container's `/etc/tc_public.pem` (RSA-2048, modulus SHA-256 `2d76c2b8c1056f89d1cb52c9b92ca69422f31bbbc11fdb3e23111712ff765fc9`):

```
openssl dgst -sha256 -verify tc_public.pem -signature sig_data.bin cw_x/data.tar.gz
→ Verified OK   (control.tar.gz and debian-binary likewise)
```

Daemon-side control flow (VERIFIED, disassembly): `install_app`/`update_app` (`updater_internal.cpp`) log "Verifying Package", call the package object's verify virtual; a zero return goes to **"Failed to verify package: <name> . Will not be used."** and no install happens; an exception is caught and logged "LCM install/upgrade failed". The signature verify core (`SignatureImpl`, `signature.cpp`) runs the OpenSSL EVP chain and gates on the exact success value (`cmp r0, 1; bne fail`), then logs "File verified". No skip flag exists in the C++ daemon.

Native host-side installer (VERIFIED, decompiled from `usr/lib/lua/lcm/execenv/native/ipk.lua` — compiled Lua 5.1 + **LNUM patch**, byte-converted with the new `scripts/lua51_header_convert.py`):

- `skip_signature()` returns true **only** when `/proc/efu/allowed` contains the literal `skip_lcm_signature_check`. The live `/proc/efu/allowed` is **empty** — production unit, no skip.
- A native ipk must carry `intermediate.cert`, `leaf.cert`, `checksums`, `checksums.sig`; the cert chain is verified by `tch.crypto.x509` against the **per-device board certificate `/proc/rip/011a.cert`** (live read: subject `CN=A0B53C-<serial>`, issuer `CN=Gateway Certificate Authority`, Technicolor, valid 2022-2036), the checksums are SHA-256 and compared against package members (`calculated_sha256sum` vs `signed_sha`). Errors: "Supplied certificate could not be verified by the certificate of the board. Unable to establish trust.", "The provided signature does not prove the provided checksums are correct."

## Residual exposure (DERIVED)

With a network position (or DNS control) an attacker can, without any secret:

Also noted from the same live reads (VERIFIED, value not recorded here): the container's `/etc/config/tc_apps` stores a **plaintext MQTT credential** (`user 'rgw'` + password) for `mqtt.teliasmartrgw.com:8883` used by the `telia-pub_rgw_messages` telemetry daemon. It is only readable with root on the box (mode-0600 store, root-only overlay), so it is not a remote exposure by itself, but it is a third-party-service credential present in the image's config tier and would be used by any process running in the container.

1. **Read** the apps list (contains the unit serial it was queried with) and every package.
2. **Rewrite the apps list** (it is unsigned JSON over HTTP) to make the daemon install *any vendor-signed package that exists in the repo*, including **older versions** (downgrade), or set `requested_status`/`install_action` to drive installs/uninstalls. Install still requires a valid vendor signature, so content cannot be injected.
3. **Block or break** the update loop (DoS).

What this does **not** give: code execution with attacker-chosen bytes (needs the vendor RSA-2048 private key), or TLS bypass (there is no TLS to bypass). The interesting realistic attack is a **downgrade to a historical vendor-signed package** — no demonstration was attempted.

## Tools

- `scripts/lua51_header_convert.py` — converts the F1's LNUM-patched Lua 5.1 precompiled chunks (4-byte `size_t`, integral flag byte `0x04`, constant tag `9` = int32) to stock 64-bit `luac 5.1.5` format for `luac -l -l` listing. Validated against `string.dump` chunks generated on the device itself (`artifacts/firmware/container-2026-11-07/dev_d.bin`, `dev_g2.bin`); the reference chunk parses end-to-end with zero trailing bytes.
- rizin project of `core-lcm.bin`: `artifacts/firmware/container-2026-11-07/lcm_proj` (full analysis ~2:46 min); `ipk-lua-listing.txt` is the full `luac -l -l` of `ipk.lua`.

## Evidence (private, gitignored)

`artifacts/firmware/container-2026-11-07/`: `core-lcm.bin`, `core-lcm.init`, `tc_public.pem`, `tc_lcm_backend.crt`, `core-lcm.log` (full), `lcm_mem.bin` (data+bss+heap dump of live PID 18103), `cw.ipk` + extracted members and signatures, disassembly extracts. The unit serial appears in the URL and log; it is already recorded in [f1-uart-credentials-and-web-triage-2026-11-06.md](f1-uart-credentials-and-web-triage-2026-11-06.md).

## What was not shown

- No packet capture of the daemon's own outbound fetch (headers inferred from static curl linkage + successful unauthenticated third-party fetch; backend does not check any credential).
- No downgrade or fake-apps-list was *delivered* to the device; the residual attack is derived, not demonstrated.
- `control.tar.gz` (postinst/maintainer scripts) of vendor packages was not audited — vendor scripts run as root by design.
- The `EncryptDecrypt`/`EncryptDecryptImpl` signer class (create_signature path) was not audited beyond identifying it; it is the vendor-side signing code embedded in the binary, not a device-side check.
- Whether the backend validates the serial in `/sn/` beyond routing was not tested.

## Live demonstration: apps-list substitution → forced install (2026-11-07, VERIFIED)

The DERIVED downgrade exposure above was demonstrated end-to-end on the owned unit, under controlled conditions (our root on the box substitutes the backend locally; the equivalent network-position attack substitutes the plain-HTTP traffic without touching the box).

Method: save the original `/etc/telia_app_config/tc_lcm` (md5 `4bd8c20e43d72dcbd4f7f7040a78cf59`, backup at `/tmp/tc_lcm.orig.bak`); point `backend_url` at a local lab server; restart `core-lcm` (TERM; the container does not auto-respawn the daemon — it was restarted via `chroot /proc/18070/root /etc/init.d/core-lcm start`, which is this lab's own root access). The server served a crafted apps list (`core-lcm` at its real installed version, plus `core-watchdog` at an attacker-chosen **downgrade** version `5.0.23.10` with the URL/filename pointing at the *genuine vendor-signed* `core-watchdog_5.0.23.16.ipk` verified earlier in this finding) and that package, gzip-wrapped to match the real backend's transport encoding.

**Result (daemon log + server access log, VERIFIED):**

1. The daemon built the apps-list URL from the substituted backend (`fetching from backend: http://<local>/ipk/hw/GCNT-X/fw/23.1/chan/F1_5.04_prod/sn/<serial>`) and fetched it (access log 03:24:34).
2. It **obeyed the attacker-chosen version**: `LCM upgrade core-watchdog v5.0.23.10` — lower than the installed 5.0.23.16. **No downgrade protection in the state machine.**
3. It downloaded the package **from the attacker-specified path on the substituted server** (`GET /files/technicolor/23.1/arm/f1x/5.0.23.16/core-watchdog_5.0.23.16.ipk`).
4. Signature verification passed (genuine package) → **`install: /tmp/core-watchdog_5.0.23.16.ipk` → `install done`** — the attacker-chosen package was installed.

An intermediate run also verified fail-closed against transport tampering: the same genuine package served **without** the backend's gzip transport wrapping was refused (`Exception in decompress!! / Package NOT verified / Will not be used.`) and not installed. A first attempt with a lab-Mac HTTP server was refused by the macOS application firewall (`Failed to connect to 192.168.1.150 port 8000`); a loopback server on the router was used instead.

**Restore (VERIFIED):** `backend_url` restored to `http://lcm.teliasmartrgw.com/` (file md5 identical to the original backup), daemon restarted, next cycle fetched the real backend normally, `core-watchdog` running unchanged (pid 18070 before and after). Demo files removed from the router `/tmp`.

**What this proves:** an attacker who controls the channel (network position or DNS, no credentials) can make the router download, verify, and **install any package present in the vendor's repository, at a version of the attacker's choosing, including downgrades**. **Not proven:** execution of attacker-authored code (vendor RSA-2048 signature still gates content), and no MITM was performed in the router's WAN path — the substitution was local as root, equivalent from the daemon's perspective. Realistic exploitation: install a *historical* vendor-signed package with known vulnerabilities, or force the Airties suite on.

**Evidence (private):** `artifacts/lcm-demo-2026-11-07/` — server root with the crafted list and package, `router-side-access.log` (7 requests incl. both fetch windows), `daemon-log-demo-window.log`, handler and serve scripts.
