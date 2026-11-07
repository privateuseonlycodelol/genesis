# Exposed management services and authentication boundaries — 2026-10-12

## Result and scope

**Tailscale UI, live 2026-11-06:** [f1-tailscale-ui-2026-11-06.md](f1-tailscale-ui-2026-11-06.md). `http://100.91.82.75/` was nginx 401 because the Host header was not a LAN address. The login page now loads for this node's Tailscale address. A foreign Host header stays 401.

**miniupnpd and cwmpd, offline 2026-11-06:** [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md). SOAP action names are matched against a fixed table. The only `popen` runs the configured WAN script. Shipped UPnP is off. `cwmpd` has no `system` or `popen` symbol. No live request.

**Closed-case BOOT-P, offline 2026-11-06:** [f1-closed-case-bootp-2026-11-06.md](f1-closed-case-bootp-2026-11-06.md). The `system_bootp` POST is still session-gated and untested live. U-Boot itself enters BOOT-P when the prozone bootp bit is set. No new unauthenticated listener.

**Physical-console follow-up, offline 2026-10-12:** [owned F1 boot review](f1-boot-log-2026-10-12.md) observes bootloader `serial0`, Linux `ttyS0` at 115200n8, BOOT-P and Enter invitations, plus a JTAG-unlock warning. These define separate physical/debug leads; serial input, login/shell authorization and JTAG permission were not tested. `ubus (running as root!)` is a daemon status message, not an anonymous management boundary. No listener/session/CUPS/WPS behavior was retested or changed by this review.

**Live UART follow-up, 2026-10-12:** [interaction finding](f1-uart-interaction-2026-10-12.md) verifies `b` enters BOOT-P; early attempts had **no Ethernet link** (`no active_port set`); a later UART capture had link but **BOOTP Reply timeout** (no server). **2026-10-13:** Windows PC on LAN verified **428-byte** BOOTREQUESTs and boot file **`GCNT-X`**; still no Offer ([BOOT-P LAN](f1-bootp-lan-2026-10-13.md)). Linux serial denied for root (logviewer). **2026-10-27:** BOOTP reply and TFTP DATA served and ACKed via `scripts/f1_bootp_tftp_mac.py`; U-Boot executed `flash_upgrade_img_bundle`, validated `compatible = "GCNT-X"` without signature requirement, declared `INFO: Image upgrade successfull!!`, and switched active boot bank to Bank 1 ([BOOT-P LAN Addenda 5–8](f1-bootp-lan-2026-10-13.md)). Homeware :80/CUPS/WFA boundaries below unchanged. **2026-11-06 live overlay flash & UART credential triage:** Flashed 13.9 MB `rootfs_data` bundle; U-Boot allocated 67 LEBs (17.1 MB); syslog confirmed `procd` console triggers `restricted_shell` and Lua `[clash-access-control]` explicitly denies root on serial (`User root has no serial access`) ([f1-live-overlay-injection-2026-11-06.md](f1-live-overlay-injection-2026-11-06.md)). Probed 9 serial credential inputs; verified `restricted_shell` evaluates empty connecting username and aborts without accepting stdin credentials; triaged 16 web admin diagnostic endpoints ([f1-uart-credentials-and-web-triage-2026-11-06.md](f1-uart-credentials-and-web-triage-2026-11-06.md)). **2026-11-06 mount_root RTFD & Clash deconstruction:** Reverse-engineered `mount_root` lifecycle scripts (`20_rtfd_remove`, `80_rtfd_restore`) and `clash-access-control.lua`. Proved why recovery flash wipes bank overlays and why root is denied serial access (root bypasses UCI with no serial flag). Overcome via `/usr/lib/lua/clash-access-control.lua` override and native Technicolor `/overlay/rtfd_persistent_files/` staging ([f1-mount-root-rtfd-and-clash-deconstruction-2026-11-06.md](f1-mount-root-rtfd-and-clash-deconstruction-2026-11-06.md)).

**Canonical CUPS follow-up (2026-10-12, same device):** [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md) (policy model, ipptool, write discriminators) and [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md) (19-probe matrix). **2026-10-29 update:** [f1-ui-audit-hidden-modals-2026-10-29.md](f1-ui-audit-hidden-modals-2026-10-29.md) discovered `/modals/printersharing-modal.lp` is live (HTTP 200) and maps to `uci.printersharing.config.enabled=1` and `uci.printersharing.config.webui`; `/etc/init.d/cupsd` confirms `enabled=1` starts `/usr/sbin/cupsd`, explaining port 631 exposure. This file records the **initial** boundary pass below; rows marked “mechanism not established” for HTTP **403** are **superseded** by the derived `<Location>` vs IPP split in the policy finding.

**Diagnostics on port 80 (same day, separate pass):** authenticated `POST` to `/modals/diagnostics-ping-modal.lp` requires a valid admin session (not tested unauthenticated here). Host metacharacters and duplicate `ipAddress` were rejected or aborted before `transformer` launched `/usr/bin/ipping_helper`; see [f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md). TR-069/CWMP (**7547**) was **closed** on LAN in the software-pass inventory — no ACS bypass was attempted. WAN/management mTLS boundaries (`/proc/rip/011a.cert` + hardware keystore `0x11A`) and dynamic token distribution on `:7577` are documented in [f1-software-link-hunt-2026-10-29.md](f1-software-link-hunt-2026-10-29.md).

**VERIFIED:** the owned F1 processes an unauthenticated read-only CUPS IPP operation, although ordinary browser GETs on the same service return 403. This is a protocol-access finding, not an administrative authentication bypass. No printer administration, settings change, firmware operation, WPS message, event subscription, or login attempt was performed.

Target: only `192.168.2.1`. The current login page's static-asset build label is `23.1.b.0448-7241017-20260223134332-1bc56e11012dfec7d96d5c28eb498c16c196a568`, matching the recorded F1 build. Board identity remains supported by prior authenticated/export evidence, not a new hardware observation. This pass tested LAN access from this Mac; it establishes nothing about WAN, guest-network, other-client, or IPv6 exposure.

20 completed HTTP exchanges were performed: 13 fixed GET controls, two `/api` GETs, one ipptool request, one independent curl IPP request, two description GETs, and one IPP resource-path comparison. Requests in automated sequences were spaced by three seconds. No HTTP 503 occurred. An initial sandboxed login-page GET failed with curl exit 7 / HTTP 000; the same bounded experiment succeeded after sandbox escalation. That failed attempt is not router authentication evidence.

## Experiments defined before execution

1. **UI boundary:** either a known metadata handler is reachable without an authenticated session, or it returns the login page. Compare no cookie, a fresh server-issued anonymous cookie, and one fixed invalid cookie. Distinguishing observation: metadata JSON versus login HTML, regardless of HTTP 200. Check the saved session separately before treating it as a positive control. Stop on a transport error or 503; no credential guesses or path enumeration.
2. **Separate HTTP listeners:** either the known UI route is served on 8080, or these paths are rejected. Compare `/`, `/login.lp`, and the known bank-size route. The related source also supplies `/api` as a separate lead; test only GET on 80 and 8080. A 404 narrows these exact requests, not the listener's entire purpose.
3. **CUPS boundary:** either browser 403 reflects denial of the protocol read too, or IPP has different access behavior. First compare GET `/`, `/admin/`, `/printers/`; then use exactly one read-only `CUPS-Get-Printers` operation. Cross-check a consequential response with independent client encoding, and compare the same operation at `/admin/`. Do not send administrative or job-creation operations.
4. **WPS metadata boundary:** either the previously advertised descriptions remain publicly readable on the LAN, or they now require authentication/unavailable transport. Retrieve only the saved advertised device and service description URLs, verifying both resolve to the owned router on port 49152. Compare hashes. Do not invoke the advertised actions or subscribe to events.

## Verified boundary matrix

| Listener / request | Client authentication state | Actual response | What it establishes |
|---|---|---|---|
| 80: session-status poll | No cookie; fresh anonymous cookie | 200, 5,784-byte login HTML, no JSON | No session-role disclosure in these controls |
| 80: session-status poll | Tampermonkey UI grab (`notloggedin.zip`, 2026-10-12) | 200, 24-byte `current_role` JSON | **Not** an unauthenticated control — browser still held admin cookie; see [`f1-grab-notloggedin-2026-10-12.md`](f1-grab-notloggedin-2026-10-12.md) |
| 80: `system-config-modal.lp?action=getbanksize` | No cookie; fresh anonymous cookie; fixed invalid cookie | 200, 5,784-byte login HTML, no JSON | No bank-size handler bypass in these controls |
| 80: session-status poll | Previously saved session cookie jar | 200, login HTML | Saved jar is not a current authenticated positive control; reason unknown |
| 8080: `/`, `/login.lp`, known bank-size route | No cookie | 404, identical 146-byte bodies | These requests did not expose the UI/backend on 8080 |
| 80 and 8080: GET `/api` | No cookie | 404, same 146-byte nginx body | Related-source exact route is not exposed by these GET requests |
| 631: GET `/`, `/admin/`, `/printers/` | No credentials or cookies | 403, identical 343-byte bodies; no `WWW-Authenticate` | Browser requests refused (at pass time: mechanism **UNKNOWN**; later **DERIVED** as location ACL — see policy finding) |
| 631: POST `/`, IPP `CUPS-Get-Printers` | No credentials or cookies | HTTP 200, `application/ipp`, 113 bytes; IPP `client-error-not-found` | The read operation reaches the IPP handler without web login |
| 631: POST `/admin/`, identical IPP read | No credentials or cookies | Same HTTP status and byte-identical IPP body as `/` | The URL string `/admin/` alone does not impose a different result for this operation |
| 49152: advertised device and service description GETs | No credentials or cookies | 200, 777 and 2,469 bytes; no auth challenge | Description metadata is readable without the UI session |

The fresh anonymous session's login-page body, session-status response and bank-size response are byte-identical. Login pages for independent sessions differ; normalizing only the CSRF meta value made the first login body equal the invalid-cookie response. Neither a byte difference nor HTTP 200 is treated as evidence of authentication success.

**VERIFIED:** the login response sets a cookie with `Path=/; HttpOnly; SameSite=Strict`; no `Secure` attribute appeared in that HTTP response. The invalid-cookie and saved-session requests received replacement cookies with those same attributes. Cookie values remain private. These observations do not measure entropy, session fixation, authenticated-cookie attributes, session lifetime, or logout revocation. **UNKNOWN:** why the old session was no longer accepted; expiry, server invalidation, or another session-binding rule have not been distinguished.

## CUPS independent check

The response header reports `CUPS/2.2 IPP/2.1`; this is a claimed family/version string, not executable identification or a patch-level determination.

The [OpenPrinting operation specification](https://openprinting.github.io/cups/doc/spec-ipp.html#cups-get-printers-operation) defines `CUPS-Get-Printers` (`0x4002`) as a printer-attribute read. The [IPP encoding specification, RFC 8010](https://www.rfc-editor.org/rfc/rfc8010.html) defines the binary framing. The request used IPP 1.1, operation-attribute group, `attributes-charset=utf-8`, `attributes-natural-language=en`, and `requested-attributes=printer-state`. It supplied no requesting username, authorization header, cookie, job, or file payload.

1. Native `/usr/bin/ipptool` encoded the first request. It decoded a 113-byte response with `client-error-not-found` and `No destinations added.` The local fixture expected `successful-ok`, so ipptool exited **1** and printed **FAIL**. That check did not pass; the response nonetheless proves an IPP application result was received. Its output is preserved unchanged.
2. A separate Python standard-library encoder constructed a 110-byte request. Curl transmitted it as `application/ipp`, without cookies or credentials. The response was HTTP **200**, `application/ipp`, 113 bytes. Raw bytes 0–1 are IPP `01 01`; bytes 2–3 are status `04 06`; bytes 4–7 echo the chosen request ID `13 57 9b df`. The body contains `No destinations added.` No authentication challenge appeared.
3. Curl sent the identical body to `/admin/`. Its response equals the root response byte-for-byte, including the echoed request ID.

Independent curl request SHA-256: `980dcfaa2c71f2a54176caf494c2a85dda6fc3bbb13df7931a48527113dc39e6`.
Root and `/admin/` response SHA-256: `373ba70cd030ed50f43607276996b03c719a1ac7e9a9109593d94f9f58cb3c99`.

**DERIVED:** browser-page denial cannot be used to conclude that LAN access to CUPS is fully denied. At this pass only one IPP read was tested; later work mapped many read ops, **Get-Jobs** success, and helper failures ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)). **DERIVED (later):** HTTP **403** vs IPP **200** split matches separate location ACL and IPP policy; shipped `cupsd.conf` still **not** obtained. The response reports no destinations; it does not demonstrate printer enumeration impact, configuration access, authorization for write operations, or a vulnerability. [CUPS configuration documentation](https://openprinting.github.io/cups/doc/man-cupsd.conf.html) describes separate location and operation authorization facilities.

## WPS and related-source boundaries

The re-fetched descriptions exactly match the prior artifacts by SHA-256:

- Device description: `16c380ac7ffe8e5699b0bb1de6b9a9ee1b492fa58eaa98fedc91c116330508e2`.
- Service description: `093f458cc0f7bfa8998d7b052e133cbdf7bc3fdabeed9a2644723842afc54ed4`.

The extracted relative routes are `wps_control`, `wps_event`, and `wps_scpd.xml`. The service advertises `GetDeviceInfo`, `PutMessage`, `PutWLANResponse`, and `SetSelectedRegistrar`. **At the time of this pass**, only description GETs were sent; opaque base64 fields left message-level authentication **UNKNOWN**.

**Superseded for control-plane behavior:** later paced work on the same listener documents unauthenticated SOAP, `SUBSCRIBE`, and peer-state handling on 49152 — see [auth-session-and-wps-2026-10-12.md](auth-session-and-wps-2026-10-12.md) and [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md). That does not change the description-hash boundary recorded above; it refutes “actions might require the web session” for the tested LAN client.

[Offline executor evidence](management-offline-service-evidence.md) records exact fields and related-source line references. The Luna xhigh subagent only parsed the specified local files and inspected source; the parent selected experiments, executed live checks, and interpreted results. Parent review removed an incorrect path-mismatch sentence from the executor draft.

**At the time of this pass:** port 8080 direct GETs returned 404, and the community snapshot was not the shipped configuration. **Superseded for the shipped config (2026-11-07):** `etc/nginx/nginx.conf` in the 23.1.b root listens on 8080 with `tproxy` and redirects to the LAN address plus `/intercept.lp` or `/no-internet-connection-intercept.lp`. That second page does not call `handleAuth`, and its restart action queues `ifup wan`. See [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md). The earlier direct 404s are unchanged; this pass did not connect to 8080.

## Reproduction and evidence locations

Private evidence is ignored by Git. Directories are mode 0700 and files containing raw responses/cookies are mode 0600. Original inputs and the original saved cookie jar were left unchanged; the live control used a copy of that jar.

- `artifacts/management/20261012T025111Z/`: initial transport failure.
- `artifacts/management/20261012T025126Z/`: ordered 13-request summary, raw headers/bodies and private cookie jars.
- `artifacts/management/protocol-control/`: exact follow-up drivers, ipptool test/input/output, raw curl IPP packet and responses, XML descriptions and sanitized summaries.

Actual commands:

```sh
python3 scripts/management_boundary_probe.py
python3 artifacts/management/protocol-control/execute.py
curl --noproxy '*' --silent --show-error --connect-timeout 4 --max-time 12 \
  --max-filesize 1048576 \
  --dump-header artifacts/management/protocol-control/ipp-curl.headers.private \
  --output artifacts/management/protocol-control/ipp-curl.body.private \
  --write-out '%{http_code}' --header 'Content-Type: application/ipp' \
  --data-binary @artifacts/management/protocol-control/get-printers.request.private \
  http://192.168.2.1:631/
python3 artifacts/management/protocol-control/surface-controls.py
python3 scripts/test_management_boundary_probe.py
```

The private driver invoked:

```sh
/usr/bin/ipptool -4 -L -t -v -T 12 -V 1.1 \
  ipp://192.168.2.1:631/ artifacts/management/protocol-control/get-printers.test
```

Versions: Python 3.14.7, curl 8.7.1, native ipptool CUPS v2.3.4, macOS 27.0 arm64. Curl reports its own x86_64 build. Four offline regression tests passed, covering literal positive responses, login HTML, malformed/negative inputs, and immediate stopping on transport failure/503. Classification was also checked against separately recorded live admin-role and bank-size responses from the earlier pass. Mock tests establish tool behavior only; the new raw exchanges establish device behavior.

## What changed and next discriminating experiment

The broad claim “CUPS is inaccessible because `/` is 403” is now refuted for the tested read operation. Unauthenticated IPP processing is established, including at the `/admin/` resource. The tested UI metadata boundary held, and the WPS **description** boundary is distinct from the web session. Later work mapped the full 49152 control plane without HTTP credentials ([f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md)); that is provisioning exposure, not a demonstrated exploit. No administrative bypass, root access, or secret extraction was demonstrated in this pass.

The highest-value web follow-up is a fresh normal login with pre/post-login cookie and CSRF capture, followed by a small paired session test: confirm admin-role JSON, check whether the pre-login cookie alone remains unauthenticated, and test CSRF binding only with an already-authorized read/export action. This would distinguish identity rotation and session binding from merely accepting a supplied token. A working authenticated session is missing in this pass; do not infer the old jar's rejection mechanism or repeat guessed logins.

WPS-over-UPnP on 49152 was subsequently exercised in [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md) (drivers under `scripts/wfa_wlanconfig_*.py`). Open items: WAN/guest exposure, `WLANEvent` sensitivity, and whether a valid registrar message could complete enrollment — not demonstrated here. For CUPS, effective authorization is still **derived**, not extracted from `cupsd.conf` (no 23.1.b rootfs; HTTP config path **403**). Follow-up work:

- [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md) — 19 paced probes; anonymous **Get-Jobs** `successful-ok`; `CUPS-Get-Devices` reached `cups-deviced` (internal error).
- [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md) — ipptool PASS on job lists; `cups-driverd`/`cups-deviced` failures; **CUPS-Create-Local-Printer** forbidden from LAN; vendor opcode drift (`CUPS-Set-Default` / `0x4004` do not match upstream 2.2.10 create paths); **503** stopped authenticated `logviewer?process=cupsd` harvest.

Tools: `scripts/cups_ipp_readonly_matrix.py`, `scripts/cups_ipp_followup.py`, `scripts/cups_ipp_policy_probe.py`.

## Exhaustion-pass boundary updates (2026-11-06/07)

Dated addendum from the [miniupnpd/cwmpd pass](f1-miniupnpd-cwmpd-2026-11-06.md), which triaged every live listener, web handler, and message-taking binary:

- **Live listener set verified**: nginx 80/443/8080/55556 (+ localhost 55555), xinetd IPv6 60443 → local 443 (assistance login fails closed on the empty verifier), cupsd 631, websockd 7681, dnsmasq 53/67, dropbear 22, hostapd 49152 + UDP 1900, charon 500/4500 (no connections configured), tailscaled 49037/41641, ntpd IPv6 123, DHCP 68/546/547. Every process shares the host network namespace; the `lxc_ee` container differs only by mount namespace and currently runs no listener.
- **websockd 7681**: connects are accepted; the `mpstat → system()` path needs a session key that no shipped component ever sets — dead code.
- **tailscaled 49037**: refuses connections addressed to the LAN address despite the `0.0.0.0` bind; loopback/tailnet only.
- **Local sockets**: `/tmp/wifi_msg_bus` mode 755 (a 31-char prefix-checked word reaches `ifconfig`/`brctl` shell lines), `/var/run/ubus.sock` mode 666 (any local user incl. `nobody` passes the null-policy check), mosquitto and hostapd control sockets root-only (770). None is a LAN port.
- **RA guard absent**: ebtables filter tables empty; a main-LAN client can emit RAs that other main-LAN clients process.
- **Versions and public issues**: dnsmasq 2.85 (inside the CVE-2026-2291 range; the crafted response cannot pass the local dnsproxy's `miekg/dns` v1.1.72 255-octet budget), dropbear 2020.81 (no pre-auth server fix after it in the upstream changelog), cupsd 2.2.10 (policy resolved; SNMP CVEs unreachable; `httpPrintf` overflow present in binary form but trigger-closed; **2026-11-07 write-side probe**: anonymous requests pass the policy gate for most printer/job state ops (Cancel/Hold/Release-Job, Pause/Resume, Purge, Set-Printer-Attributes, Delete-Printer/Class, Accept/Reject, Set-Default, Move-Job, Create/Validate-Job, Authenticate-Job, Get-Document), stopping only at resource lookup while no queue exists; HTTP 401 wall only on CUPS-Add-Modify-Printer/Class; several earlier opcode labels were corrected), busybox 1.34.1, hostapd 2.10 (RADIUS/H2E/MLO advisories inapplicable), kernel 4.19.235 (h323 and sip conntrack CVEs in range, parser-confusion class). **Deepened 2026-11-07:** unauth WAN restart page VERIFIED live (`?action=restart` with no session executed `ifup wan`; WAN uptime reset, LAN SSH unaffected); kernel h323/sip parser engagement VERIFIED from a LAN client (one SIP INVITE+SDP produced `sip/audio` conntrack expectations; `bcm_alg` loads the helper modules and forces `nf_conntrack_helper=1`; no helper= shown in /proc on this BCM build — expectations are the reliable signal).
- **Onboarding-gated shell chain**: DPP credential strings flow from a completed exchange into `hostapd_cli`/`wpa_cli` lines with quotes-only protection; gated on a user-initiated onboarding window. **Deepened 2026-11-07:** the wps_pbcd loopback UDP 58032 protocol (msg types 7–26) was disassembled end-to-end — it is a state/UI notification bus; its only `system()` is a fully fixed `wpa_supplicant` launch command, unreachable through the type gate, with no datagram byte in the command line; the DPP applier sub-block is additionally gated by a credential-presence check, `wl_wlif_is_map_onboarding()`, and a backhaul-type check. **Pre-onboarding paths closed:** per-site format resolution shows only `set dpp_connector %s` and `set dpp_netaccesskey %s` take data (hostapd DPP events); `set ssid %s`, `set wpa_passphrase %s`, `set dpp_csign %s` are unreferenced dead strings in wps_pbcd, so the non-DPP WPS credential path is dead code — no pre-onboarding injection exists in this daemon. **Demonstrated 2026-11-07 (plumbing half):** with the onboarding state present (`wl0_dpp_role=enrollee`), a `DPP-CONNECTOR` event value flowed through the daemon's own parse to `system()` and an attacker-chosen second command after a `;` executed as root; see [f1-dpp-shell-chain-demonstrated-2026-11-07.md](f1-dpp-shell-chain-demonstrated-2026-11-07.md).
- **core-lcm package channel**: plain-HTTP fetches from `http://lcm.teliasmartrgw.com/` (no token, no TLS; the Amazon-root backend cert is unused), per-member RSA-2048 signatures against `tc_public.pem` are the only integrity control; fail-closed, no skip on this unit (EFU `/proc/efu/allowed` empty). Residual: unsigned apps list → MITM downgrade of vendor-signed packages. Deep audit: [f1-lcm-package-channel-deep-audit-2026-11-07.md](f1-lcm-package-channel-deep-audit-2026-11-07.md).
