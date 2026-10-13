# Verified web session/CSRF boundaries and WPS information access

Date: 2026-10-12. Target: owner's Telia F1 at `192.168.2.1`, recorded GCNT-X / 23.1.b build. This follows [the management-service inventory](management-auth-boundaries-2026-10-12.md). Only the owned IPv4 target was contacted. No reboot, settings change, firmware operation, password change, PIN guess, WPS M2, registrar-selection action, event subscription, or provisioning completion was sent.

## Evidence found

**Later physical-console evidence:** [owned-unit UART interaction follow-up](f1-uart-interaction-2026-10-12.md) verifies `b` enters BOOT-P and the no-Ethernet recovery attempt times out; Linux Return/`id`/Ctrl+J produced no shell/login/UID. This is a separate boundary from web sessions, WPS **49152** and IPP **631**; no boot message demonstrates an HTTP/session bypass, WPS credential disclosure or CUPS administration. No network action was made in that UART pass.

**VERIFIED:** a normal SRP login succeeded and its server proof verified. The server issued a different session ID during proof completion, and the authenticated page contained a different CSRF token. A copied pre-login cookie did not gain admin access. The export handler rejected the wrong-session, missing, and pre-login tokens, while the correct admin token returned a configuration-export envelope. An anonymous session supplied with the admin token still received login HTML.

**VERIFIED:** a separate WPS `GetDeviceInfo` request on port 49152, without cookies or HTTP credentials, returned an initial WPS M1 message. A second decoder independently confirmed its message type and core field lengths. This establishes access to the initial provisioning stage from this LAN client, not WPS completion, PIN recovery, credential disclosure, or a vulnerability.

**VERIFIED tooling correction:** curl and Python do not interchange the session-cookie expiry field transparently in the observed jars. Curl's zero expiry was loaded by Python as an already expired cookie and omitted from a request. Python's blank expiry needed conversion to zero for the independent curl replay. These interoperability failures were diagnosed before interpreting the affected requests as authentication results.

## Hypotheses, distinguishing controls, and stopping rules

Before the login experiment, the alternatives were: a pre-login cookie might retain authenticated authority after login, or the server might rotate identity and leave the old cookie unauthenticated. CSRF might be accepted independently of session identity, or require the authenticated session's current token. The experiment therefore copied the pre-login cookie before login, compared identities/tokens privately, bracketed negative controls with admin-role polls, and used exactly one correct-token export as the handler-positive control. A transport error, HTTP 503, failed SRP proof, failed admin control, or unexpected export in a negative case stops execution. It never retries a failed password.

For WPS, readable descriptions alone left the control boundary unknown. The discriminating request was exactly one advertised `GetDeviceInfo` action after a valid service-description control. Possible outcomes included authentication denial, a SOAP fault, or a structurally recognizable M1. Source inspection established in advance that this action can allocate transient WPS peer state; it was not treated as a zero-state-change GET. No subsequent WPS message was sent.

## Web login and paired controls

Private ordered evidence: `artifacts/management/session-boundary-20261012T032135Z/`. Three seconds separate requests. All 16 requests completed; none returned 503. HTTP 200 alone was never considered proof of authentication or export success.

| Request | Control | Observed result |
|---|---|---|
| 1–2 | Previously issued anonymous session: login page and session-status poll | Both 200 / 5,784-byte login HTML; no admin-role JSON |
| 3–4 | One normal SRP identify/proof exchange | Both 200; server proof verified |
| 5–6 | Authenticated page and admin-role positive control | 17,267-byte page, then `current_role=admin` JSON |
| 7 | Copied pre-login cookie, after successful login | 200 / login HTML; no admin-role JSON |
| 8 | Original authenticated session recheck | `current_role=admin` |
| 9 | Second independent anonymous session | 200 / login HTML; different CSRF token |
| 10 | Authenticated export with the second session's token | 403 / 146 bytes; no export envelope |
| 11 | Authenticated export with no CSRF token | 403 / same body |
| 12 | Authenticated export with the pre-login token | 403 / same body |
| 13 | Anonymous export request with the current admin token | 200 / login HTML; no export envelope |
| 14 | Admin-role control after negatives | `current_role=admin` |
| 15 | Authenticated export with the current matching token | 200 / 181,089-byte export envelope |
| 16 | Admin-role control after export | `current_role=admin` |

Export SHA-256: `ae817f92f1d49cb646605bf068672f879d7d931e9e11fe486ea1c0019bfecaf4`. The check recognizes the previously observed outer envelope, not decrypted contents or cryptographic authenticity. Export can create temporary backend files/state; no persistent configuration change was requested.

An independent check parsed the proof response's `Set-Cookie` using an RFC-style header parser, including folded header serialization, and confirmed that the issued session ID differs from the original anonymous ID. A separate comparison of the two actual page bodies confirmed CSRF rotation. Values were not printed or published.

**VERIFIED independent HTTP-client control:** after converting the Python jar's blank session-expiry fields to curl's zero representation, curl read the same session-status URL and returned exactly `{"current_role":"admin"}`. The first unconverted curl attempt had returned login HTML with HTTP 200; it is preserved as a failed client-interoperability control and is not counted as authenticated success. The authenticated jar also contains the export handler's `fileDownload` cookie; cookie-value rotation was independently checked specifically for `sessionID`, not inferred from adding that download cookie.

**DERIVED, bounded conclusion:** the tested login flow rotates the session ID and CSRF token; the copied old cookie does not inherit the new admin role; the tested export handler requires an authenticated session and its matching token. These tests do not establish every route's CSRF coverage, cookie entropy, logout revocation, absolute session lifetime, cross-device binding, WAN isolation, or privileged upload/import behavior.

## HTTP 503 and the client discrepancy

The first fresh login-page GET returned nginx 503 / 190 bytes before any authentication POST. One cookie-free curl comparison also returned the same 503 body. A curl GET using the earlier anonymous cookie instead returned 200 / login HTML.

The first attempt to reuse that jar in Python still returned 503. Offline preparation of the request showed why: `MozillaCookieJar` loaded curl's expiry `0` as Unix epoch, considered it expired, and attached **no Cookie header**. Import now normalizes that representation to `expires=None, discard=True`; a regression test and preparation of the actual jar confirmed the header is present without sending a request. The corrected run completed the normal login and all paired controls above.

The reverse representation difference also affected the independent curl role check: converting Python's blank expiry to curl's zero representation produced the working replay. Original jars were preserved unchanged; imported and converted copies stayed private.

**VERIFIED in related source, not the F1 runtime:** [sessionmgr.lua at the pinned community commit](https://github.com/Ansuel/tch-nginx-gui/blob/ecd493c591afd7de47e624245bd1ac1bd9a526a2/decompressed/gui_file/usr/lib/lua/web/sessionmgr.lua) has an explicit new-session capacity check and a 503 path when no session can be obtained. A recognized existing session can avoid new allocation. [The source review](session-source-availability-boundary.md) records exact conditions, configurable limits, defaults, missing includes, and version limitations.

**HYPOTHESIS:** session allocation/capacity contributed to the observed cookie-free 503 while an existing session worked. The F1's effective limits, counters and logs were not retrieved, and these requests were sequential rather than a simultaneous controlled pair. Later replacement-session behavior shows that availability can change over time. Rate limiting, temporary backend conditions, and other gates are not conclusively excluded. A cooldown or device-wide outage was not established. The supplied password was not rejected during the 503 attempts: those runs sent no SRP request.

## WPS control result and independent decoding

Private evidence: `artifacts/management/wps-info-20261012T032255Z/`.

1. GET `/wps_scpd.xml` returned 200 / 2,469 bytes; the XML identified the advertised action. SHA-256 `093f458cc0f7bfa8998d7b052e133cbdf7bc3fdabeed9a2644723842afc54ed4`.
2. After a three-second pause, POST `/wps_control` sent a standard SOAP 1.1 `GetDeviceInfo` request and matching WFA `SOAPAction`. It supplied no Cookie, Authorization, PIN or WPS continuation message. Response: HTTP 200 / 864 bytes, a WFA `GetDeviceInfoResponse`, no SOAP fault, containing one base64 `NewDeviceInfo` value. XML response SHA-256 `1008749e94a22482ce943cccc98e579db0c9eae99d30f38f3f59231f0b67eb0f`.
3. The decoded WPS payload is 394 bytes, SHA-256 `841cdd3d3c7ba811d7a0fe45be7bf0de252c292b6aab0464ba61e9488184c55a`.

| Actual WPS field | Type / offset in decoded payload | Observed value or length |
|---|---|---|
| Version | `0x104a`, offset 0 | One byte, `0x10` |
| Message Type | `0x1022`, offset 5 | One byte, `0x04` (M1) |
| Enrollee Nonce | `0x101a`, offset 40 | 16 bytes |
| Public Key | `0x1032`, offset 60 | 192 bytes |
| Device Password ID | `0x1012` | `0x0000` |
| Configuration Methods | `0x1008` | `0x2008` |

The local parser checked TLV boundaries, critical duplicate attributes, SOAP namespace/response structure and base64 validity. To avoid relying only on that new parser, OpenSSL independently decoded the base64 payload. Its exact bytes were placed in a **synthetic Ethernet/EAPOL/Expanded-EAP WSC wrapper** solely for Wireshark decoding. This is not an observed EAP exchange or network capture. TShark 4.6.9 independently decoded Version `0x10`, Message Type `0x04`, Device Password ID `0x0000`, Configuration Methods `0x2008`, a 16-byte nonce and a 192-byte public key, with no expert message. Actual nonce/key and device-identifying field values remain private.

**VERIFIED upstream comparison:** the entire service descriptor matches the static descriptor bytes at Android upstream commit `d7ff03d48f825360eec2a371e3361306f2fd721b`. [Pinned source review](wps-upnp-source-boundary.md) traces the AP-PIN prerequisite, M1 generation, retained peer state and cleanup boundaries. Descriptor equality does not identify the shipped executable. The observed M1 and upstream AP-PIN prerequisite do not independently disclose a PIN, prove its value, or establish a PIN-authentication weakness.

## Work, tools and reproducibility

The initial offline sequencing test caught an invalid attempt to deep-copy a CookieJar's thread lock. The harness was corrected to copy individual cookies into an independent jar before any authenticated live run; the final six tests pass. The later expiry-format failures and their fixes are recorded above rather than treated as device authentication failures.

New tools:

- `scripts/f1_session_boundary.py`: terminal password input, copied cookie controls, one normal login, bounded token checks and one correct-token export.
- `scripts/wps_device_info.py`: offline SOAP/TLV inspection or explicit `--live` description control plus one information action.
- `scripts/wfa_wlanconfig_*.py`: later paced 49152 surface, peer, event, deep, and registrar probes — see [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md).
- `scripts/test_f1_session_boundary.py`: six passing offline tests, including the real format incompatibility, old-cookie independence, negative-response classification and stopping before export on failed login.
- `scripts/test_wps_device_info.py`: four passing offline tests using literal wire fixtures, malformed/truncated inputs, duplicate critical fields, SOAP faults, and structural M1 checks. Synthetic fields are not represented as cryptographic validation or live evidence.

Actual successful commands:

```sh
python3 scripts/test_f1_session_boundary.py
python3 scripts/test_wps_device_info.py
python3 scripts/f1_session_boundary.py \
  --anonymous-cookie artifacts/management/20261012T025126Z/anonymous.cookies.txt \
  --other-anonymous-cookie artifacts/management/client-503-control/second-anonymous.cookies.txt
python3 scripts/wps_device_info.py --live
openssl base64 -d -A \
  -in artifacts/management/wps-info-20261012T032255Z/message.base64.private \
  -out artifacts/management/wps-info-20261012T032255Z/message.private
tshark -r artifacts/management/wps-info-20261012T032255Z/synthetic-eap-wrapper.private.pcap \
  -T fields -e wps.version -e wps.message_type -e wps.device_password_id -e wps.config_methods
```

The second anonymous jar was reconstructed locally from a previously saved `Set-Cookie` header; it was not guessed. Independent curl role reads and their conversion outputs are preserved in the successful session directory. Versions: Python 3.14.7, curl 8.7.1, OpenSSL 4.0.3, TShark 4.6.9. Raw evidence, exports, cookies and decoded WPS data remain ignored/private. The password was supplied through terminal input with echo disabled; it was not written into a script or report.

Two Luna xhigh execution tasks retrieved/hashed exact primary and related source snapshots. The parent selected hypotheses, implemented and validated live tools, diagnosed interoperability failures, executed experiments, and independently checked consequential outputs. [CUPS comparison](cups-http-ipp-source-boundary.md) now includes v2.2.10, matching the **body-reported** patch label from the saved error page. Later paced IPP work ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)) mapped anonymous reads vs HTTP **403**; binary identity and shipped `cupsd.conf` remain unknown.

## What changed and next attack on the problem

The earlier fresh-session blocker was narrowed and worked around without rebooting or guessing passwords. Login identity rotation, old-cookie separation, and CSRF binding for the export handler are now demonstrated with paired positive/negative controls. The WPS surface is no longer described merely as readable XML: the owned device demonstrably returns an initial M1 to a LAN client without HTTP credentials or a web session.

Follow-up on the same 49152 surface (negative SOAP, peer teardown, `SUBSCRIBE`/NOTIFY, shell M2→**WSC_NACK**, registrar binding after `SUBSCRIBE`) is consolidated in [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md) with drivers `scripts/wfa_wlanconfig_*.py`. **No demonstrated exploit** (no PIN/PSK recovery, no completed WPS, no admin bypass). Remaining high-value items: `WLANEvent` content classification, WAN reachability of 49152, and whether a cryptographically valid registrar exchange can complete from the LAN. For the web interface, route-specific authorization—especially upload/import handlers—remains separate from the now-mapped WPS control plane. **CUPS :631** is a separate non-session surface ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)); no upload/import, logout, or administrative CUPS write was tested in this document.
