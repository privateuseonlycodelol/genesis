# HAR review — `wanetc.har` (WAN Services UI) — 2026-10-12

**Scope:** offline read of `/Users/[redacted]/Downloads/wanetc.har` (copy at `artifacts/hars/wanetc.har`, gitignored). No requests were replayed. Passwords, CSRF tokens, cookies, LAN/WAN addresses, rule names, and port-forward targets are **not** recorded here.

**SHA-256:** `deaecf9c837035a9b1a2c5c5a62c37181a242aa757169d6ec2e77673b9e6f677`  
**Entries:** 64 (50 GET, 14 POST), all `http://192.168.2.1`, HTTP **200** throughout.  
**Wall time (HAR):** `2026-10-12T06:41:51.811Z` – `2026-10-12T06:43:34.506Z` (WebInspector).  
**Tooling:** `scripts/analyze_f1_har.py`, `scripts/inspect_ui_har.py` (sanitized paths only).

## Name vs content

The file name suggests broadband/Ethernet, but **no** `broadband-modal.lp`, `ethernet-modal.lp`, or `internet-modal.lp` appears. The session is **WAN Services** (`/modals/wanservices-modal.lp`), the **DNS & DynDNS** tab (`GET /modals/dyndns-wanservices-modal.lp` only — no DynDNS POST), plus the usual advanced dashboard loads (`gateway.lp`, `wanservices-min.js`, wireless card POSTs, session polls).

## Verified request sequence (new vs earlier HAR set)

Compared with the five nested HARs in [docs/f1-uploaded-hars.md](../docs/f1-uploaded-hars.md) and the `1.har`–`8.har` union in [f1-har-coverage-2026-10-12.md](f1-har-coverage-2026-10-12.md):

| Observation | Status |
| --- | --- |
| First captured **`POST /modals/wanservices-modal.lp`** with `TABLE-*` and `SAVE` in this repo | **VERIFIED** |
| `GET /modals/wanservices-modal.lp` body matches prior grab hash `317d4230…fd2e9` (13,146 bytes) | **VERIFIED** |
| `GET /modals/dyndns-wanservices-modal.lp` matches prior hash `ba8f3d2b…1178c77` (10,711 bytes) | **VERIFIED** |
| `action=scheduleReboot` JSON poll (184 bytes) | **VERIFIED** (same class as earlier HARs) |
| `POST /gateway.lp` `action=URL` + `POST /ajax/wirelesscard.lua` | **VERIFIED** (same as `1_a48a.har`) |

## POST actions on `wanservices-modal.lp`

All used `request_body_csrf_present: true` in the sanitized inspector. Field names below are from form keys only.

| # (HAR index) | `action` | Notable fields (names only) | Response size | Outcome (from HTML markers) |
| --- | --- | --- | --- | --- |
| 37 | `TABLE-NEW` | `tableid=portforwarding`, `index=-1` | 18,267 | Edit row scaffold |
| 39 | `TABLE-ADD` | `portforwarding`, `protocol`, `wanport`, `lanport`, `destinationip`, `sourceip`, `enabled` | 14,968 | **Validation:** phrase `Please enter valid IPv4` on destination (invalid test value; not recorded) |
| 43, 45, 47 | `TABLE-ADD` | same table, `index=1` | 14,998 / 14,974 / 13,978 | HTTP 200; no same validation phrase in body (rule may have been accepted — not verified against running config) |
| 49 | `SAVE` | `fromModal=YES`, `upnp_status`, `upnp_natpmp`, `upnp_secure_mode`, `upnp_igd_version`, `enabled` | 14,083 | **“Changes saved successfully”**; posted UPnP/NAT-PMP **on** (`upnp_status=1`, `upnp_natpmp=1`, `upnp_secure_mode=1`, `igdv1`) |
| 51 | `TABLE-DELETE` | `portforwarding`, `index=1` | 13,210 | Row delete path |
| 55 | `SAVE` | UPnP fields (no `enabled` key in POST) | 13,235 | **“Changes saved successfully”**; posted UPnP/NAT-PMP **off** (`upnp_status=0`, `upnp_natpmp=0`, secure mode still `1`) |
| 57 | `TABLE-NEW` | `tableid=fwrules_v6` | 16,593 | IPv6 rule scaffold |
| 59 | `TABLE-ADD` | `fwrules_v6`, `dest_ip_v6`, `src_ip_v6`, `wanport`, `protocol`, `enabled_v6` | 14,006 | HTTP 200 |
| 61 | `TABLE-DELETE` | `fwrules_v6`, `index=1` | 13,195 | IPv6 row delete |

**VERIFIED:** the Homeware table CRUD surface documented in [f1-js-deep-2026-10-12.md](f1-js-deep-2026-10-12.md) (`TABLE-NEW` / `TABLE-ADD` / `TABLE-DELETE` + modal `SAVE`) is exercised on a live 23.1.b admin session in this capture.  
**VERIFIED:** at least one **`SAVE`** changed UPnP/NAT-PMP persistence (on then off in two saves). Exact firewall/UPnP daemon impact was not observed from the HAR alone.

## Exploit and injection assessment

This section records whether the WAN Services POST surface is a practical injection or RCE path. It combines the HAR evidence above with the saved UI map ([f1-grab-033853-ui-surfaces.md](f1-grab-033853-ui-surfaces.md)), client handlers ([f1-js-deep-2026-10-12.md](f1-js-deep-2026-10-12.md)), and **REPORTED** upstream Homeware GUI source (`Ansuel/tch-nginx-gui` `decompressed/gui_file/www/docroot/modals/wanservices-modal.lp`). The 23.1.b on-box `.lp` bytes were **not** diffed against that tree; treat the Lua as a model until rootfs or a matching leak confirms it.

### Compared with diagnostics ping

| | Diagnostics `action=PING` | WAN Services `TABLE-*` / `SAVE` |
| --- | --- | --- |
| Sink model | **REPORTED:** `/usr/bin/ipping` builds `ping … <host>` with `io.popen`, host unquoted | **REPORTED:** `post_helper.handleTableQuery` → transformer `rpc.network.firewall.portforward.*` / UCI firewall helpers; `proxy.set` on structured paths |
| Web validator | **VERIFIED** on unit: metacharacter hosts rejected; duplicate `ipAddress` → HTTP 500 in `inet_pton` ([f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md)) | **VERIFIED** in HAR: invalid IPv4 destination → `Please enter valid IPv4` on `TABLE-ADD` |
| RCE demonstrated | **No** | **No** |

There is **no** analogous “paste shell syntax into one string that becomes a command” path on this modal in the published source.

### Field-level controls (REPORTED — upstream `wanservices-modal.lp`)

IPv4 table `portforwarding` uses `pfw_valid` and `getValidateName`:

| POST field | Validator (upstream names) | Injection relevance |
| --- | --- | --- |
| `name` | `getValidateName`: length 1–63; reserved `DMZ rule`; pattern `[^%w%-%s]` rejected | Blocks `;`, `$()`, quotes, `<`, `/`, etc. in the rule name |
| `destinationip` | `gOV(gAV(vSIDIP, vQTN))` — device IPv4 on LAN | Same class as other IP gates; HAR showed rejection of a bad destination |
| `sourceip` | Optional IP validators in column set | Not exercised for bypass in this HAR |
| `wanport` / `lanport` | `validateStringIsPort` / `validateStringIsPortRange`; overlap checks via `validPorts` | Numeric / range semantics, not free text |
| `protocol` | `getValidateInEnumSelect` — `tcp`, `udp`, `tcpudp` | Not user-defined strings |
| `destinationmac` | Optional `validateStringIsMAC` | Structured MAC, not a shell |
| `enabled` | `validateBoolean` | `0` / `1` style |

IPv6 table `fwrules_v6` uses parallel columns (`dest_ip_v6`, `src_ip_v6`, `validateStringIsIPv6`, etc.) in the same file. The HAR exercised `TABLE-ADD` / `TABLE-DELETE` on that table but did not show a validation error string.

Preset application names can call `update_firewall_helper` → `set_helper_port(helper, port)` on `uci.firewall.helper.*` when the rule **name** matches entries in `pfw_helper_map` (e.g. FTP/PPTP presets). That updates a **helper dest_port** in config, not a shell invocation.

Modal **`SAVE`** posts `upnp_status`, `upnp_natpmp`, `upnp_secure_mode`, `upnp_igd_version` through boolean/enum validators in the same modal (UPnP section). **VERIFIED** in the HAR: two saves returned “Changes saved successfully” with UPnP/NAT-PMP toggled on then off.

Client-side, `wanservices-min.js` does not add its own HTTP actions; rows go through `main-min.js` `G("TABLE-…")` / `#save-config` ([f1-js-deep-2026-10-12.md](f1-js-deep-2026-10-12.md)). Parental `URLfilter` / `keywfilter` tables have extra client checks in `G()`; **`portforwarding` is not in those branches.**

### Auth and CSRF

**VERIFIED:** every POST in the sanitized inspector had `request_body_csrf_present: true`.  
**VERIFIED (earlier pass):** without an admin session, hidden export/metadata GETs return the login page ([f1-hidden-action-boundary-2026-10-12.md](f1-hidden-action-boundary-2026-10-12.md)); login `Set-Cookie` used `HttpOnly` and `SameSite=Strict` ([management-auth-boundaries-2026-10-12.md](management-auth-boundaries-2026-10-12.md)).

**DERIVED:** remote unauthenticated injection into these POSTs is not supported by this evidence. Abuse requires a stolen admin session or physical/LAN access as an authenticated operator.

### Realistic impact (not RCE)

| Angle | Assessment |
| --- | --- |
| **Command / shell injection** via `TABLE-ADD` fields | **Not demonstrated.** Upstream validators are IP/port/enum/name charset; backend path is firewall RPC/UCI. Unlike [ipping host](f1-ipping-host-2026-10-12.md), no `io.popen` host string. |
| **Auth bypass / missing CSRF** | **Not shown** in this HAR. |
| **Intentional misconfiguration** (port forward, UPnP on) | **VERIFIED** capability for an admin: HAR `SAVE` turned UPnP/NAT-PMP on then off. That widens **LAN-side** IGD/NAT-PMP behavior; it is policy change, not code execution. Separate control plane on TCP **49152** is documented in [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md). |
| **Stored XSS** via rule `name` | **HYPOTHESIS only.** Upstream name charset excludes most HTML metacharacters; echo into table HTML was not tested with a live payload. |
| **Duplicate / polluted form keys** | **UNKNOWN.** Ping duplicate `ipAddress` aborted in `inet_pton` with HTTP 500 ([f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md)). Whether `TABLE-ADD` has a similar single-request crash was **not** tested on WAN Services. Best case would be request abort, not shown RCE. |
| **DynDNS tab** | **Not in scope of this HAR** (GET only). Password fields on that form are in the AES wrap list in `main-min.js` when saved from the UI ([f1-grab-033853-auth-crypto.md](f1-grab-033853-auth-crypto.md)). |

### Exploit status (summary)

**No inject-and-own-shell path** is established on `/modals/wanservices-modal.lp` from this capture or from the published modal source. The offensive upside here is **admin-level firewall and UPnP policy**, not a substitute for root, firmware, or the ipping/UCI popen chain when another writer can set `Host`.

**Highest-value follow-ups elsewhere (not this form):** per-device config key / rootfs, non-UI UCI writers (USP/CWMP when ACS is reachable), **49152**, CUPS, firmware `import`/`upgradefw`. A single bounded duplicate-field probe on `TABLE-ADD` is optional only to hunt validator crashes.

## What this does not show

- No exploit, no auth bypass, no new routes beyond the known wanservices modal.
- No proof that the repeated IPv4 `TABLE-ADD` rows remained after delete/save (only HTTP 200 and HTML).
- No broadband link statistics, LAN DHCP edits, or WAN DHCP release/renew (`internet-modal.lp` / `ethernet-min.js` actions were not captured).
- DynDNS credentials were not submitted (GET-only tab).

## Reproduction (offline)

```sh
python3 scripts/analyze_f1_har.py /path/to/wanetc.har
python3 scripts/inspect_ui_har.py /path/to/wanetc.har | python3 -c 'import sys,json; [print(json.dumps(json.loads(l))) for l in sys.stdin]'
```

Store the original HAR outside git (`artifacts/` is ignored).
