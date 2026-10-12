# Live read-only access checks — 2026-10-12

Target: the owner's F1 at `192.168.2.1`; no other network host was probed. Normal authenticated read controls and configuration export were performed after connectivity recovered. No settings, reboot, import, upload, or firmware operations were performed. Export can create temporary backend state; no persistent settings change was requested.

## Initial connection failure, subsequently resolved

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

**VERIFIED:** `GET /modals/system-config-modal.lp?action=getbanksize` returned HTTP 200, 44 bytes, JSON `{"success":"true","banksize":"134217728"}`. This is **128 MiB reported by the backend**, not independently measured physical NAND or a verified current partition map.

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

**VERIFIED:** one standard `localhost A` DNS lookup over UDP and one over TCP to the router both completed with `NOERROR` and one answer. Thus a DNS-speaking service was observed on both transports, rather than inferred solely from port 53. Only status/counts are recorded in `artifacts/logs/software-pass-dns.json`; no answer values are published.

**VERIFIED:** one unicast SSDP discovery request to the owned router's UDP 1900 received HTTP-like status 200. Its advertised description and service-description URLs pointed back to the same IPv4 router, on **TCP 49152**. Both descriptions were retrieved with ordinary GETs. The XML advertised `urn:schemas-wifialliance-org:device:WFADevice:1` and `urn:schemas-wifialliance-org:service:WFAWLANConfig:1`; action names: `GetDeviceInfo`, `PutMessage`, `PutWLANResponse`, `SetSelectedRegistrar`. **None was invoked.** Advertisement describes a Wi-Fi provisioning interface, not proof of an authentication flaw or shell access. Raw XML contains private identifiers and remains ignored under `artifacts/logs/software-pass-ssdp/`.

## Remaining access limits

IPv6 neighbor entries did not identify an address matching the IPv4 router's L2 identity, and a default-IPv6 route query yielded no usable gateway. No neighboring IPv6 addresses were guessed or scanned; the router's IPv6 service surface remains UNKNOWN. A physical WAN mirror was not configured or revalidated. The new offline capture preflight and its synthetic controls do not supply that missing live evidence.
