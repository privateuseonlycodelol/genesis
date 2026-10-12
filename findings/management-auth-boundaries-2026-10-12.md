# Exposed management services and authentication boundaries — 2026-10-12

## Result and scope

**Canonical CUPS follow-up (2026-10-12, same device):** [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md) (policy model, ipptool, write discriminators) and [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md) (19-probe matrix). This file records the **initial** boundary pass below; rows marked “mechanism not established” for HTTP **403** are **superseded** by the derived `<Location>` vs IPP split in the policy finding.

**Diagnostics on port 80 (same day, separate pass):** authenticated `POST` to `/modals/diagnostics-ping-modal.lp` requires a valid admin session (not tested unauthenticated here). Host metacharacters and duplicate `ipAddress` were rejected or aborted before `transformer` launched `/usr/bin/ipping_helper`; see [f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md). TR-069/CWMP (**7547**) was **closed** on LAN in the software-pass inventory — no ACS bypass was attempted.

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

**VERIFIED in related community source only:** port 8080 is configured with `tproxy` and `web.intercept.process()`, while the main UI uses session checks and exact `/api` uses a token authenticator. **HYPOTHESIS:** the live 8080 service may be a traffic-interception handler rather than an alternate UI listener. Its three route 404s do not identify the implementation. The community snapshot is not the shipped 23.1.b configuration.

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
