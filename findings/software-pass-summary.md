# Software-only research pass — 2026-10-12

Scope: owned Telia F1 GCNT-X on the recorded 23.1.b build, ordinary authenticated reads/configuration exports, bounded service discovery, offline capture/parser validation, and related public-source comparison. Three GPT-6 Luna subagents were dispatched with xhigh reasoning and narrowly assigned files/tasks. The parent reviewed results, ran the live controls, reran validation, and requested corrections where tests or conclusions were too broad.

## Evidence found

| Track | Actual result | Evidence |
| --- | --- | --- |
| Valid ordinary request/session control | Normal SRP login and server proof verified; base page and admin-role poll succeeded | [Live controls](software-pass-live-access.md) |
| Hidden read/export functionality | `getbanksize` returned 128 MiB; export succeeded twice using the authenticated CSRF token, despite absent UI controls | [Live controls](software-pass-live-access.md), [export structure](software-pass-config-export.md) |
| Bounded network inventory | TCP 53/80/631/8080 open among 19 checked; Wi-Fi provisioning descriptions retrieved on 49152 following one unicast SSDP request | [Live controls](software-pass-live-access.md) |
| WAN capture reliability | Old verifier could classify DHCP broadcasts as enough for MIRROR OK; both prior captures contain raw-IP records under Ethernet metadata | [Capture audit](software-pass-capture-review.md) |
| RBI correctness | Real reference header/hash verified; six malformed-header cases now rejected consistently; synthetic crypto cross-check passes | [Crypto validation](software-pass-crypto-validation.md) |
| Related source | Actual public CSRF and error-rendering functions exercised with mocks; related export/status dispatch inspected at pinned commit | [Source comparison](software-pass-source-comparison.md) |
| Saved browser evidence | Same metadata URL returned login HTML before login and JSON after login, both HTTP 200 | [Request audit](software-pass-request-review.md) |
| New `7.har` evidence | 444 captured entries, including 106 CSRF-bearing POSTs; 123 JavaScript occurrences, 14 distinct basename/hash pairs; four match saved scripts and ten add local evidence | [HAR request review](software-pass-har7-review.md), [HAR script comparison](software-pass-har7-js.md) |

## Work performed and validation

Changed `scripts/rbi_header.py` to reject invalid BLI2 magic, impossible offsets/sizes, and incomplete TLVs. Changed `scripts/verify_mirror_pcap.sh` so aggregate counts cannot certify or declare a physical mirror broken. Added the read-only designated-flow preflight, sanitized HAR inspector, normal-login read/export control, and regression harnesses. Corrected stale conclusions in the earlier bypass/crypto findings.

Actual successful checks:

```sh
tools/venv/bin/python scripts/test_rbi_validation.py
python3 scripts/capture_preflight.py --self-test
python3 scripts/test_f1_readonly_control.py
python3 scripts/test_inspect_ui_har.py
lua scripts/test_related_csrf.lua
bash -n scripts/verify_mirror_pcap.sh
git diff --check
```

The capture positive is a synthetic HTTP exchange cross-checked by tshark, not a physical mirror observation. The crypto positive is synthetic and checked by two crypto libraries, not a real firmware decryption. The live script regression tests mock HTTP; the separate recorded live responses provide device evidence.

## What changed

The UI/backend is not exhausted: a hidden configuration-export handler works for the normal admin session. An initial export rejection was followed by success after obtaining the current authenticated-page CSRF token. A fresh configuration artifact is now available for offline analysis. This is not privilege escalation and does not supply the RBI decryption key.

The legacy 16-bit payload-offset read is not wrong on this reference RBI; both implementations read 363. It remains limited for larger offsets. The earlier blanket incorrect-seek explanation was corrected. The old capture OK verdict was also unsound and has been removed from the verifier.

The newly supplied `7.har` was inspected offline and left unchanged. Its 444 entries comprise 338 GETs and 106 POSTs. All 106 POSTs include a CSRF field; 105 have HTTP 200 and one has status 0 (no HTTP response recorded), with no recorded 403. HTTP 200 alone does not establish application success. Newly observed scripts construct `/ajax/wirelesscard.lua` requests and a conditional gateway `action=URL` request. These are client-code observations, not verified backend capabilities. Extracted scripts and their sanitized hash manifest remain ignored/private. No captured requests were replayed.

## Next discriminating work and limits

Continue offline export-envelope identification using the two real exports and exact producer/parser sources, without assuming encryption from entropy or block alignment. The advertised Wi-Fi provisioning service and header-reported CUPS service are concrete surfaces for implementation identification; neither is a demonstrated flaw. No provisioning actions were invoked.

A real authorized matching BLI2/OSCK fixture remains necessary for end-to-end firmware decryption validation. No current 23.1 firmware image, root shell, exploit, or decrypted configuration was obtained. IPv6 inventory remains incomplete because no router IPv6 address was established. The physical WAN mirror still needs a designated bidirectional control capture with correct link-type metadata. Raw responses, cookies, exports, and device-identifying XML remain ignored/private; no credentials were included in these reports. This research agent did not create commits or reset concurrent workspace changes.
