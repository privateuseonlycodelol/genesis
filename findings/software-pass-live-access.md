# Live read-only access checks — 2026-10-12

Target: the owner's F1 at `192.168.2.1`; no other network host was probed. Normal authenticated read controls and configuration export were performed after connectivity recovered. No settings, reboot, import, upload, or firmware operations were performed. Export can create temporary backend state; no persistent settings change was requested.

## Initial connection failure, subsequently resolved

**Later offline hardware evidence:** the [owner-supplied UART capture](f1-boot-log-2026-10-12.md) now records GCNT-X / **4.19.235 AArch64**, Bank 2, five physical partition ranges, UBI rootfs2, verity + AES-XTS and UBIFS overlay. No new network check was made. The earlier 128 MiB `banksize` below remains a logical backend value; neither the 502 MiB UBI image region nor the ~52.824 MiB mapped root independently measures configured bank allocation. No shell/root is shown.

**VERIFIED:** a normal HTTP GET of `/login.lp` failed from the command-line client, including after sandbox escalation. Curl returned exit 7, HTTP `000`, zero response bytes. A separate Python socket connection to TCP 80 returned errno 65, `No route to host`. No proxy environment variables were present. A route lookup nevertheless showed the destination associated with `en0`.

**VERIFIED:** the Codex in-app browser could not open the same URL; its error was `net::ERR_ADDRESS_UNREACHABLE`.

**REPORTED by the user:** their browser can reach the F1. At this stage, the discrepancy with tool observations was unexplained. It was not evidence of an F1 authentication failure or HTTP 503 cooldown. The later permission change and recovery below support an app/process-specific network access explanation, without an OS-level causal trace.

**VERIFIED tool output, limited interpretation:** one paced TCP connect inventory against eight ports returned `filtered` for all: 22, 23, 53, 80, 443, 445, 8080, 8443. Command:

```sh
/Applications/nmap.app/Contents/Resources/bin/nmap -sT -Pn -n --max-retries 0 --host-timeout 15s --max-rate 2 -p 22,23,53,80,443,445,8080,8443 192.168.2.1
```

Nmap 7.991 exited 0. Its `Host is up` text is not independent reachability evidence because `-Pn` bypasses discovery. With the socket/browser failures, these classifications do not establish the router's actual service inventory or firewall policy.

## Recovery and authenticated controls

**REPORTED:** the user enabled local-network access for the app listed as ChatGPT in macOS settings. **VERIFIED:** the next ordinary login-page GET returned HTTP 200 / 5,784 bytes. This temporal sequence is consistent with the local-network permission causing the earlier failures; no OS-level permission trace was collected.

**VERIFIED:** `scripts/f1_readonly_control.py --export` performed normal SRP login using terminal password input with echo disabled. Both authentication POSTs returned HTTP 200, and the client verified the server proof. The subsequent base `/gateway.lp` GET returned 17,267 bytes without login markers; the session-status GET returned `current_role: admin`. No password was saved by this script.

**VERIFIED:** `GET /modals/system-config-modal.lp?action=getbanksize` returned HTTP 200, 44 bytes, JSON `{"success":"true","banksize":"134217728"}`. This is **128 MiB reported by the backend**, not independently measured physical NAND or a verified current partition map. The same JSON shape and byte length were reproduced offline in the [04:56:48Z UI grab](f1-grab-045648-review.md) (`success` is the string `"true"`, not a JSON boolean).

**VERIFIED:** the first export POST used the pre-authentication login-page CSRF token and returned 403 / 146 bytes. A private comparison established that the token on the authenticated page differed. In the same cookie session, a fresh base-page GET supplied the current token, a session-status GET again verified admin, and one corrected `POST action=export_config` returned 200 / 181,057 binary bytes. SHA-256: `430de53785019e67b4391a8adf296f7d0424a37e0863aab8c6bf4fb38193bdd0`.

**DERIVED:** this controlled sequence supports CSRF-token state as the explanation for the failed export attempt. It disproves the claim that this hidden export operation is unavailable to the ordinary admin session merely because its button is absent. It does not diagnose every prior 403 or establish any privilege escalation.

**VERIFIED outer-header identity check:** both downloaded exports declare board `GCNT-X`, a build beginning `23.1.b`, and the public analogue's `THENC` preamble. Board, build, and serial fields match across the two files; serial values are not published. These are outer metadata labels from the live-export responses, not independently authenticated inner contents.

Private responses and cookie jar: ignored `artifacts/ui/readonly-control-20261012T021317Z/`; directory mode 0700, response files mode 0600. `summary.json` preserves request order, methods, static paths/actions, response sizes, hashes and safe classification. Requests 1–7 are the initial run; 8–10 are the corrected replay. Requests 11–13 repeat the base/admin controls and take one second ordinary export specifically for an envelope comparison: 181,089 bytes, SHA-256 `90d9833b519ddad18b183321196b8f0584ece549154ccb17081417a6434fe390`. Across these 13 requests, 12 returned 200 and the one stale-token export returned 403; no 503 occurred. The control script now refreshes CSRF from the authenticated page, requires valid bank-size JSON, and reports failure for a rejected or unrecognized export response. Five mocked sequencing tests in `scripts/test_f1_readonly_control.py` cover token rotation, failed base/bank controls, export 403, and HTTP 200 HTML pretending to be a download. These tests are not live router evidence. See `software-pass-config-export.md` for offline format checks; no successful decryption is claimed.

## Working-connection service inventory

**VERIFIED:** a second paced TCP-connect inventory with working access checked 19 selected ports. Open: **53, 80, 631, 8080**. Closed: 21, 22, 23, 111, 139, 443, 445, 515, 1900, 2049, 5000, 7547, 8443, 8888, 9000. This is a bounded selection, not a complete port scan. Nmap service names are port labels, not daemon identification.

```sh
/Applications/nmap.app/Contents/Resources/bin/nmap -sT -Pn -n --max-retries 1 --host-timeout 45s --max-rate 3 -p 21,22,23,53,80,111,139,443,445,515,631,1900,2049,5000,7547,8080,8443,8888,9000 192.168.2.1 -oN artifacts/logs/software-pass-router-tcp.txt
```

Ordinary unauthenticated HTTP GET `/` on 631 returned 403 / 343 bytes with a CUPS family marker in its Server header; this is a header-reported identity only. Port 8080 returned 404 / 146 bytes with an nginx marker. Bodies/headers remain private under `artifacts/logs/software-pass-http-services/`. Neither root response excludes additional handlers. No service actions were invoked.

**Superseded for CUPS behavior (2026-10-12 later pass):** the same port accepts unauthenticated **`application/ipp`** reads (including **Get-Jobs** with `successful-ok` on an empty queue) while browser GET/HEAD and `GET /admin/conf/cupsd.conf` stay at **403**. Full matrix, ipptool cross-check, and policy model: [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md), [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md). Drivers: `scripts/cups_ipp_readonly_matrix.py`, `scripts/cups_ipp_followup.py`, `scripts/cups_ipp_policy_probe.py`.

**VERIFIED:** one standard `localhost A` DNS lookup over UDP and one over TCP to the router both completed with `NOERROR` and one answer. Thus a DNS-speaking service was observed on both transports, rather than inferred solely from port 53. Only status/counts are recorded in `artifacts/logs/software-pass-dns.json`; no answer values are published.

**VERIFIED:** one unicast SSDP discovery request to the owned router's UDP 1900 received HTTP-like status 200. Its advertised description and service-description URLs pointed back to the same IPv4 router, on **TCP 49152**. Both descriptions were retrieved with ordinary GETs. The XML advertised `urn:schemas-wifialliance-org:device:WFADevice:1` and `urn:schemas-wifialliance-org:service:WFAWLANConfig:1`; action names: `GetDeviceInfo`, `PutMessage`, `PutWLANResponse`, `SetSelectedRegistrar`. **At the time of this pass, none of those actions was invoked** (description GETs only). Later bounded probes on the same service are recorded in [auth-session-and-wps-2026-10-12.md](auth-session-and-wps-2026-10-12.md) (`GetDeviceInfo` / M1) and [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md) (negative SOAP, peer state, `SUBSCRIBE`/NOTIFY, shell M2/NACK). Those follow-ups established LAN-unauthenticated control-plane reachability, not WPS completion, credential disclosure, or a demonstrated exploit. Raw XML from this pass remains ignored under `artifacts/logs/software-pass-ssdp/`.

## Diagnostics ping (follow-up, same day)

**VERIFIED:** authenticated `POST /modals/diagnostics-ping-modal.lp` with `action=PING` and `ipAddress=127.0.0.1` (one repetition, 56 bytes) added one transformer log row `async run: /usr/bin/ipping_helper` in the same second; the logged command has no arguments. **VERIFIED:** newline-plus-`logger` and backtick host strings were rejected with `Please enter valid ipv4/domain address` before the helper ran; duplicate `ipAddress` fields returned nginx HTTP **500** from `inet_pton` (`string expected, got table`) inside `validateObject` / `restartTest`. No command execution or syslog marker. TCP **7547** remained **closed** in the inventory above; a **2026-10-12** follow-up also found common USP transports closed and could not issue a USP/CWMP **Set** on `IPPing.Host` ([f1-usp-ipping-2026-10-12.md](f1-usp-ipping-2026-10-12.md)). Details: [f1-ipping-helper-2026-10-12.md](f1-ipping-helper-2026-10-12.md), [f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md). Drivers: `scripts/f1_ipping_control.py`, `scripts/f1_ipping_host_probe.py`, `scripts/f1_usp_ipping_probe.py`.

## Remaining access limits

IPv6 neighbor entries did not identify an address matching the IPv4 router's L2 identity, and a default-IPv6 route query yielded no usable gateway. No neighboring IPv6 addresses were guessed or scanned; the router's IPv6 service surface remains UNKNOWN. A physical WAN mirror was not configured or revalidated. The new offline capture preflight and its synthetic controls do not supply that missing live evidence.
