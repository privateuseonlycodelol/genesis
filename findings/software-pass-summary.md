# Software-only research pass — 2026-10-12

Scope: owned Telia F1 GCNT-X on the recorded 23.1.b build, ordinary authenticated reads/configuration exports, bounded service discovery, offline capture/parser validation, and related public-source comparison. Three GPT-6 Luna subagents were dispatched with xhigh reasoning and narrowly assigned files/tasks. The parent reviewed results, ran the live controls, reran validation, and requested corrections where tests or conclusions were too broad.

## Evidence found

**Later owner-supplied UART review (same date):** [extensive boot analysis](f1-boot-log-2026-10-12.md) and [line-indexed evidence](f1-boot-log-2026-10-12-evidence.md) establish the recorded **4.19.235 AArch64** kernel, Bank 2 and UBI → verity → AES-XTS root stack. The subsequent [live interaction follow-up](f1-uart-interaction-2026-10-12.md) verifies `b` enters BOOT-P; early attempts had **no Ethernet** (`no active_port set`); a later capture had link up but still **BOOTP Reply timeout** without a PC server. **2026-10-13:** Windows PC on LAN recorded full BOOTREQUESTs with boot file **`GCNT-X`**, no Offer ([BOOT-P LAN](f1-bootp-lan-2026-10-13.md)). Linux Return/`id`/Ctrl+J produced no shell; logviewer verified serial denied for root. A later re-read of that same log found cooked-tty echo of Up-arrow (`^[[A`) and another invitation, still with no command output. A follow-up `/login.lp` check from this Mac timed out; its default route was not the F1 LAN. A later logviewer export on this unit **verified** tty `restricted_shell` plus Clash `User root has no serial access` / `No suitable login found for root on serial` ([UART interaction](f1-uart-interaction-2026-10-12.md)). The **4.1.52** module applies to the older public reference, not this kernel.

| Track | Actual result | Evidence |
| --- | --- | --- |
| Valid ordinary request/session control | Normal SRP login and server proof verified; base page and admin-role poll succeeded | [Live controls](software-pass-live-access.md) |
| Hidden read/export functionality | `getbanksize` returned 128 MiB; export succeeded twice using the authenticated CSRF token, despite absent UI controls | [Live controls](software-pass-live-access.md), [export structure](software-pass-config-export.md) |
| Bounded network inventory | TCP 53/80/631/8080 open among 19 checked; Wi-Fi provisioning descriptions retrieved on 49152 following one unicast SSDP request | [Live controls](software-pass-live-access.md) |
| CUPS :631 (follow-up, same day) | IPP read matrix + ipptool: anonymous **Get-Jobs** / completed jobs OK; HTTP pages **403**; `cups-deviced`/`cups-driverd` internal errors; no queue created; effective `cupsd.conf` still unknown | [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md), [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md) |
| WFA WLANConfig on 49152 (follow-up, same day) | Paced probes: negative SOAP, `GetDeviceInfo` peer state, unauth `SUBSCRIBE`/NOTIFY, shell M2→WSC_NACK; no PIN or completed enrollment | [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md), [session/WPS](auth-session-and-wps-2026-10-12.md) |
| WAN capture reliability | Old verifier could classify DHCP broadcasts as enough for MIRROR OK; both prior captures contain raw-IP records under Ethernet metadata | [Capture audit](software-pass-capture-review.md) |
| RBI correctness | Real reference header/hash verified; six malformed-header cases now rejected consistently; synthetic crypto cross-check passes | [Crypto validation](software-pass-crypto-validation.md) |
| Related source | Actual public CSRF and error-rendering functions exercised with mocks; related export/status dispatch inspected at pinned commit | [Source comparison](software-pass-source-comparison.md) |
| Saved browser evidence | Same metadata URL returned login HTML before login and JSON after login, both HTTP 200 | [Request audit](software-pass-request-review.md) |
| New `7.har` evidence | 444 captured entries, including 106 CSRF-bearing POSTs; 123 JavaScript occurrences, 14 distinct basename/hash pairs; four match saved scripts and ten add local evidence | [HAR request review](software-pass-har7-review.md), [HAR script comparison](software-pass-har7-js.md) |
| Finished UI grab (04:56:48Z) | Verbatim 114×200 bodies; GET JSON for Wi-Fi card, NTP, session poll, `scheduleReboot`, `smartwifi`, `getbanksize`; guest LAN and IPv6 DHCP modals; QR still bare 500 | [04:56:48 grab review](f1-grab-045648-review.md) |
| Config export decrypt (Tier 1) | `THENC`/`GW` envelope verified on three saves; HMAC layout matches Technicolor model; plaintext **blocked** without `RIP_ID_RANDOM_KEY_B` | [f1-config-export-decrypt-2026-10-12.md](f1-config-export-decrypt-2026-10-12.md), [hardware-key blocker](f1-hardware-key-blocker-2026-10-12.md) |
| Diagnostics PING → `ipping_helper` (follow-up, same day) | One loopback PING caused a same-second transformer `ipping_helper` line (no argv); host metacharacters and duplicate `ipAddress` rejected before helper; no RCE | [f1-ipping-helper-2026-10-12.md](f1-ipping-helper-2026-10-12.md), [host validation](f1-ipping-host-2026-10-12.md) |
| Diagnostics TRACE → `igd_traceroute_helper` (follow-up, same day) | Loopback TRACE tied to **`igd_traceroute_helper`** (prior pass wrongly used `ipping_helper` oracle); host probes same as PING — no injection | [f1-trace-helper-2026-10-12.md](f1-trace-helper-2026-10-12.md), [f1-trace-path-2026-10-12.md](f1-trace-path-2026-10-12.md) |
| USP/CWMP `IPPing.Host` from LAN (follow-up, same day) | CWMP **7547** and common USP transports **closed**; no USP Set exercised; `obuspa_retriever` in cron logs | [f1-usp-ipping-2026-10-12.md](f1-usp-ipping-2026-10-12.md) |
| WAN Services HAR (`wanetc.har`) | Admin `TABLE-*` / UPnP saves; validators block injection class; no RCE path vs diagnostics `io.popen` | [f1-har-wanetc-2026-10-12.md](f1-har-wanetc-2026-10-12.md) |
| **19.x RBI + boot log (offline, same day)** | Sealed **19.4.0507** RBI unchanged; **71** OSCK trials incl. **19.4.0856** UART constants — all `bad_osck`; `:7577` sibling **403**; **`r2secr.arm64.4.1.52.ko`** built for aarch64 **4.1.52** | [rbi-crypto-attempt3.md](rbi-crypto-attempt3.md), [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md), [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md) |
| **`POST gateway.lp` `action=URL` + port 8080** | Twelve SSRF-style `urlVal` values → identical dashboard HTML; TCP **8080** fixed paths all nginx **404**; CUPS `file://` printer-uri → **400** | [f1-gateway-url-action-2026-10-12.md](f1-gateway-url-action-2026-10-12.md) |
| **Aggressive injection battery (evening)** | `f1_aggressive_software_pass.py`: diagnostics/SSRF/device/log/import/sched reboot/WAN table/AJAX — **no** demonstrated exploit; **503** after burst | [f1-aggressive-software-pass-2026-10-12.md](f1-aggressive-software-pass-2026-10-12.md) |
| **Gap pass (evening; script later retired)** | Sched oracle, blind SSRF, offline export header — negative; auth matrix partial then **dropped** as duplicate of boundaries | [f1-gap-attack-pass-2026-10-12.md](f1-gap-attack-pass-2026-10-12.md) |
| **BOOT-P on LAN (2026-10-13)** | pktmon + Wireshark on cabled Windows PC: **17** BOOTREQUESTs, **`GCNT-X`**, no server; `f1-bootp-reply.ps1` prepared, **not run** | [f1-bootp-lan-2026-10-13.md](f1-bootp-lan-2026-10-13.md), [composite index](f1-research-composite-2026-10-13.md) |
| **Password encoding (2026-10-15, offline)** | Client UTF-8 SRP vs low-byte `sha512crypt` reaffirmed; community Clash/`pwcrypt` consumer traced; collision pairs share crypt hash, not SRP; **no** live auth impact on F1 | [f1-grab-033853-auth-crypto.md](f1-grab-033853-auth-crypto.md), [CLI trace](f1-password-encoding-cli-trace-2026-10-15.md) |

## Work performed and validation

Changed `scripts/rbi_header.py` to reject invalid BLI2 magic, impossible offsets/sizes, and incomplete TLVs. Changed `scripts/verify_mirror_pcap.sh` so aggregate counts cannot certify or declare a physical mirror broken. Added the read-only designated-flow preflight, sanitized HAR inspector, normal-login read/export control, and regression harnesses. Added `scripts/decrypt_f1_config_export.py`, `scripts/test_decrypt_f1_config_export.py`, `scripts/f1_config_key_probe.py`, and `scripts/acquire_f1_config_key.sh`. Corrected stale conclusions in the earlier bypass/crypto findings.

Actual successful checks:

```sh
tools/venv/bin/python scripts/test_rbi_validation.py
tools/venv/bin/python scripts/test_decrypt_f1_config_export.py
python3 scripts/capture_preflight.py --self-test
python3 scripts/test_f1_readonly_control.py
python3 scripts/test_inspect_ui_har.py
lua scripts/test_related_csrf.lua
bash -n scripts/verify_mirror_pcap.sh
cd scripts && python3 -m unittest test_cups_ipp_readonly_matrix test_management_boundary_probe -v
git diff --check
```

Live CUPS probes (same day, paced): `cups_ipp_readonly_matrix.py`, `cups_ipp_followup.py`, `cups_ipp_policy_probe.py` on `192.168.2.1:631` — see [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md).

The capture positive is a synthetic HTTP exchange cross-checked by tshark, not a physical mirror observation. The crypto positive is synthetic and checked by two crypto libraries, not a real firmware decryption. The live script regression tests mock HTTP; the separate recorded live responses provide device evidence.

## What changed

The UI/backend is not exhausted: a hidden configuration-export handler works for the normal admin session. An initial export rejection was followed by success after obtaining the current authenticated-page CSRF token. A fresh configuration artifact is now available for offline analysis. This is not privilege escalation and does not supply the RBI decryption key.

**Follow-up (same day):** Tier 1 offline work verified the Technicolor `THENC` / `GW` envelope and added decrypt/HMAC tooling (`scripts/decrypt_f1_config_export.py`). Plaintext decryption remains **blocked** on per-device `RIP_ID_RANDOM_KEY_B` (`findings/f1-config-export-decrypt-2026-10-12.md`, `findings/f1-hardware-key-blocker-2026-10-12.md`). A 119-request authenticated key-surface probe found **no** new handlers; it was followed by nginx **503** on new logins until cooldown (`findings/f1-ui-leads-23.1b.md`).

The legacy 16-bit payload-offset read is not wrong on this reference RBI; both implementations read 363. It remains limited for larger offsets. The earlier blanket incorrect-seek explanation was corrected. The old capture OK verdict was also unsound and has been removed from the verifier.

The newly supplied `7.har` was inspected offline and left unchanged. Its 444 entries comprise 338 GETs and 106 POSTs. All 106 POSTs include a CSRF field; 105 have HTTP 200 and one has status 0 (no HTTP response recorded), with no recorded 403. HTTP 200 alone does not establish application success. Newly observed scripts construct `/ajax/wirelesscard.lua` requests and a conditional gateway `action=URL` request. These are client-code observations, not verified backend capabilities. Extracted scripts and their sanitized hash manifest remain ignored/private. No captured requests were replayed.

## Next discriminating work and limits

**Pass index (2026-10-13):** [f1-research-composite-2026-10-13.md](f1-research-composite-2026-10-13.md) — blocked vs open queue (BOOTP reply, ipping probe, signed recovery, hardware key).

**Config plaintext:** obtain `RIP_ID_RANDOM_KEY_B` (root `dd` of `/proc/rip/0108` or `eripv2` MTD + ECK), then run `scripts/decrypt_f1_config_export.py --randb …`. Further export downloads or UI action fuzzing will not derive the key.

The Wi-Fi provisioning service on **49152** is a **measured** LAN control plane ([f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md)). **CUPS :631** is also measured: unauthenticated IPP **reads** on an empty queue ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)). **Diagnostics ping** on **:80** ties PING to `ipping_helper` but blocks web-form host injection ([f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md)); **TRACE** uses `igd_traceroute_helper` ([f1-trace-helper-2026-10-12.md](f1-trace-helper-2026-10-12.md)). LAN **USP/CWMP Set** on `IPPing.Host` was **blocked** ([f1-usp-ipping-2026-10-12.md](f1-usp-ipping-2026-10-12.md)). Confirm `/usr/bin/ipping` from rootfs if a non-UI writer appears. Ground-truth `cupsd.conf` and ipping binaries still need **23.1.b rootfs** or shell ([decomp-kickoff.md](decomp-kickoff.md)).

A real authorized matching BLI2/OSCK fixture remains necessary for end-to-end **firmware** decryption (community + boot-log-derived guesses exhausted in [rbi-crypto-attempt3.md](rbi-crypto-attempt3.md)). No 23.1 firmware image, root shell, exploit, or decrypted configuration plaintext was obtained. **`r2secr` for 4.1.52 aarch64** was prepared for the older public reference; the later owned-unit **4.19.235** capture has **no matching module**, and neither module ABI nor current eRIP acquisition path is validated ([r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md)). **Wait for HTTP 200 on `/login.lp`** before paced live work (503 observed after the key probe). IPv6 inventory and WAN mirror gaps unchanged. Raw responses, cookies, exports, and device-identifying XML remain ignored/private. This research agent did not create commits or reset concurrent workspace changes.

**04:00 archive comparison finalized:** [paired review](f1-grab-040001-review.md) and [runtime delta](f1-grab-040001-runtime-delta.md) verify six repaired scripts, seven queued page omissions, and two QR failure contexts within 135 log rows. These historical gaps are linked to later completed collection and QR controls; no new live requests, firmware, key recovery, or exploit resulted from this offline pass. Eight archive-tool regression cases pass.

**2026-10-27 offline follow-up (REA/HAR track):** analyzing the full 24-file UI grab tree (vs. the 10-file subset used on 2026-10-17) located the `export_config` click handler in `js__system-config-min.js` — a plain `fileDownload` POST to the modal's own form action, no hidden endpoint. Closes the 10-17 `trace_application_feature` no-match as a tooling-coverage gap, not evidence of a missing trigger. A keyword sweep of the 14 newly-available JS files found no hidden actions, `eval(`, or hardcoded secrets. Separately, a hash mismatch between two 2026-10-12 grabs' `srp-min.js` was traced to a sanitization-substitution artifact in one grab's own review pipeline, not a real build difference — all copies are byte-identical once reversed. See [f1-rea-har-pass-2026-10-17.md](f1-rea-har-pass-2026-10-17.md) addendum. No live device requests this pass.
