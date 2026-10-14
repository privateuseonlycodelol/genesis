# F1 web API map — 23.1.b

**When:** 2026-10-11  
**Gateway:** `http://192.168.2.1`  
**Config changed:** none. Every live call was a GET, or the two SRP login posts. No save, reset, reboot, export, or upload was sent.

Verified means the response or the saved file shows it. Hypothesis means the file suggests it and this pass did not run it.

## Auth (verified)

`GET /login.lp` returns the login form, a CSRF meta tag, and a session cookie.

Login is SRP in two posts to `/authenticate`, matching `artifacts/ui/srp-min.js` and `scripts/f1_srp_login.py`:

1. `I` (username) and `A` (client value). The box returns salt `s` and `B`.
2. `M` (client proof). The box returns its own `M`. A match is a logged-in session.

After that, `GET` of a `*.lp` path with the cookie returns the admin fragment. `main-min.js` `loadModal` does that GET. If the fragment contains the login form, or the status is 403, the script sends the browser to `/login.lp`.

A poll, `GET /gateway.lp?auto_update=true&getSessionStatus=true`, returns the current role. That poll was already in an older capture. It was not repeated here.

The saved admin surface is mostly **forms** and **`.lp` GETs**, including a **session-status poll** on `gateway.lp`. A `.lp` URL can still return **structured data** (JSON) for some `action=` query parameters; that is not a separate REST API beside the Homeware page model. Each modal is also a form whose `method` is `post` and whose `action` is its own path, plus `CSRFtoken`.

### GET JSON verified later (04:56:48Z UI grab, offline)

These were not exercised in the 2026-10-11 live map pass; they are **VERIFIED** in [`f1-grab-045648-review.md`](f1-grab-045648-review.md) from a finished Tampermonkey archive (admin session cookie, GET only). Values that identify the LAN or Wi-Fi are omitted here.

**Session scope:** Tampermonkey `GM_xmlhttpRequest` GETs use the **browser cookie jar**. Archives exported while still signed in (including `notloggedin.zip`, which matches the ~05:57:18Z admin grab) therefore show JSON for these probes. They do **not** prove unauthenticated access; see [`f1-hidden-action-boundary-2026-10-12.md`](f1-hidden-action-boundary-2026-10-12.md) and [`f1-grab-notloggedin-2026-10-12.md`](f1-grab-notloggedin-2026-10-12.md).

| Request | Shape (keys / notes) |
| --- | --- |
| `GET /gateway.lp?auto_update=true&getSessionStatus=true` | `current_role` (observed `admin`) |
| `GET /gateway.lp?action=scheduleReboot` | `systemTime`, `rebootTime`, `alertMsg`, `popupHeader` |
| `POST /gateway.lp` `action=URL` + `urlVal` | HTTP 200 Advanced dashboard HTML (17,267 B); **no** change in body for loopback/CUPS/WPS/`file://` test values — [f1-gateway-url-action-2026-10-12.md](f1-gateway-url-action-2026-10-12.md) |
| `GET /modals/parental-modal.lp?action=smartwifi` | `current_state`, `current_phase` |
| `GET /modals/system-config-modal.lp?action=getbanksize` | `success`, `banksize` (128 MiB string) |
| `GET /ajax/wirelesscard.lua?auto_update=true` | JSON **array** of objects: `listatus`, `ssid`, `radio` (bare `/ajax/wirelesscard.lua` still 0 B) |
| `GET /modals/time-management-modal.lp?getNTP=true&auto_update=true` | JSON string body listing Telia NTP hostnames |
| `GET /modals/ethernet-modal.lp?intf=guest` | HTML guest-LAN modal (distinct from bare LAN modal) |

`GET …?action=upgradefwstatus` on the configuration modal returned the same normalized HTML as `action=gf1nosuchaction`, not a JSON status object. That does not disprove POST upgrade polling from `system-config-min.js`.

## Ordinary pages (verified GET 200)

These show status or a settings form. They are not a shell. Posting the form would change settings; that was not done.

| Path | What the GET returned |
|------|------------------------|
| `/gateway.lp` | Advanced dashboard of cards |
| `/modals/broadband-modal.lp` | Ethernet link up, 1000 Mbps |
| `/modals/internet-modal.lp` | WAN DHCP connected |
| `/modals/ethernet-modal.lp` | LAN address and subnet |
| `/modals/device-modal.lp` | Client list |
| `/modals/firewall-modal.lp` | Firewall level and rules |
| `/modals/parental-modal.lp` | Site blocking |
| `/modals/tod-modal.lp` | Time-of-day rules |
| `/modals/diagnostics-connection-modal.lp` | WAN check |
| `/modals/diagnostics-network-modal.lp` | Port counters |
| `/modals/diagnostics-ping-modal.lp` | Ping and trace form (`action=PING` / `TRACE`; fields `ipAddress`, `ipAddressTrace`, …) |
| `/modals/diagnostics-igmpproxy-modal.lp` | IGMP counters |
| `/modals/wireless-radio-modal-newEM.lp` | 2.4 and 5 GHz radio form |
| `/modals/wireless-wps-modal-newEM.lp` | WPS form |
| `/modals/wireless-ap-modal-newEM.lp` | SSID and security form |
| `/modals/time-management-modal.lp` | Clock, timezone Europe/Stockholm |
| `/modals/system-info-modal.lp` | Vendor Vantiva, product Telia F1, software 23.1.b, hardware version GCNT-X. No SoC, flash chip, or Wi-Fi chip |
| `/modals/logviewer-modal.lp` | 283 syslog rows. No firmware host and no `.rbi` name |
| `/modals/basicview-accesscode-modal.lp` | Guided setup: router password, SSID, guest Wi-Fi |
| `/password.lp` | Change-password form |

`/modals/dmz-modal.lp` is the “Bridge ETH port 4” form (a public-IP bridge). Still a settings form.

## Pages that can change the box (verified present, not invoked)

Posting these would change the gateway. This pass only downloaded them.

| Path | If posted |
|------|-----------|
| `/modals/wanservices-modal.lp` | Port forward and UPnP |
| `/modals/dyndns-wanservices-modal.lp` | DynDNS account (currently disabled) |

### WAN Services modal — verified POST behavior (`wanetc.har`, 2026-10-12)

Offline browser capture on 23.1.b; not replayed. See [f1-har-wanetc-2026-10-12.md](f1-har-wanetc-2026-10-12.md).

| POST `action` | Tables / fields (names only) | Observed result |
| --- | --- | --- |
| `TABLE-NEW` | `tableid` `portforwarding` or `fwrules_v6` | HTTP 200 HTML scaffold |
| `TABLE-ADD` | IPv4: `destinationip`, `sourceip`, `wanport`, `lanport`, `protocol`, `enabled`; IPv6: `dest_ip_v6`, `src_ip_v6`, `wanport`, `enabled_v6` | HTTP 200; one attempt showed `Please enter valid IPv4` for bad destination |
| `TABLE-DELETE` | `tableid`, `index` | HTTP 200 |
| `SAVE` | `fromModal`, `upnp_status`, `upnp_natpmp`, `upnp_secure_mode`, `upnp_igd_version`, optional `enabled` | HTTP 200; “Changes saved successfully”; UPnP/NAT-PMP toggled in capture |

Matches the shared `main-min.js` table handlers ([f1-js-deep-2026-10-12.md](f1-js-deep-2026-10-12.md)). Field validators and exploit assessment (no RCE; UPnP policy only): [f1-har-wanetc-2026-10-12.md](f1-har-wanetc-2026-10-12.md) § Exploit and injection assessment.
| `/modals/l2tp-ipsec-server-modal.lp` | VPN server, including a pre-shared key field (value removed from the saved copy) |
| `/modals/contentsharing-modal.lp` | Samba, DLNA, USB mode (USB 3.1 says it reboots) |
| `/modals/system-config-modal.lp` | Restart, factory reset, semi-reset. The buttons on the page are only those three |
| `/password.lp` and the guided-view modal | Replace the admin password |

`/js/system-config-min.js` (6816 bytes, GET 200) is loaded by the configuration modal. It posts back to that modal’s form action. Actions named in the script:

- `system_reboot`, factory reset, semi-reset (the buttons that are on the page)
- `export_config`, import, `schedulerebootset`
- `system_bootp` behind a “LAN Upgrade” confirm
- `upgradefw` file upload, then `upgradefwstatus` and `getbanksize`

The upload accepts file extensions `rbi`, `fw`, and `pkgtb`. A failed upgrade string says “build signed with wrong key”.

**Verified:** the saved configuration HTML does not contain `#file-upgradefw`, `#btn-system-bootp`, or the export/import controls.

**Verified:** `system-config-min.js` still defines an **upgrade handler** (`upgradefw`, `upgradefwstatus`, `getbanksize`, import/export, BOOTP confirm).

**Not tested on :80:** reboot, factory reset, import, `POST system_bootp`, and firmware upload in the [2026-10-12 boundary pass](f1-hidden-action-boundary-2026-10-12.md). **Hardware BOOT-P** (U-Boot `b` + LAN DHCP) is separate — listen-only capture done; see [BOOT-P LAN](f1-bootp-lan-2026-10-13.md). A hand-built `POST` with `action=upgradefwstatus` returned **403** from nginx in an earlier pass (see `findings/tried.md`). Authenticated `POST export_config` does return a config envelope; the same POST without an admin session returns the login page.

**Key-surface sweep (2026-10-12):** `scripts/f1_config_key_probe.py` sent **119** authenticated GETs (rip/backup/debug `action=` names, fake `/proc/rip` paths, traversal). **No** new JSON or binary key material; only the known JSON pair above plus HTML shells. Details: [`f1-hardware-key-blocker-2026-10-12.md`](f1-hardware-key-blocker-2026-10-12.md). Followed by nginx **503** on new logins until cooldown.

`main-min.js` also GETs `/gateway.lp?action=scheduleReboot` to read a scheduled time. That URL was not called again.

### Diagnostics ping modal — verified POST behavior (2026-10-12)

Authenticated session and CSRF required (same model as other modals). **VERIFIED** on this 23.1.b unit:

| POST `action` | Observed behavior |
| --- | --- |
| `PING` + valid loopback `ipAddress` | HTTP 200; status `Ongoing` then completed success row; transformer logs `async run: /usr/bin/ipping_helper` with **no** trailing arguments ([f1-ipping-helper-2026-10-12.md](f1-ipping-helper-2026-10-12.md)). |
| `PING` + newline/`logger` or backtick host | HTTP 200; `Please enter valid ipv4/domain address`; echoed raw host; **no** new `ipping_helper` line ([f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md)). |
| `PING` + two `ipAddress` fields | HTTP **500** (170-byte nginx stub); Lua abort in `GetIPType` / `inet_pton` (`string expected, got table`); **no** helper ([f1-ipping-host-2026-10-12.md](f1-ipping-host-2026-10-12.md)). |
| `TRACE` + loopback `ipAddressTrace`, hops 1 | HTTP 200; transformer logs **`igd_traceroute_helper`** (not `ipping_helper`) — [f1-trace-helper-2026-10-12.md](f1-trace-helper-2026-10-12.md) |
| `TRACE` + `$(printf 127.0.0.1)` / newline / backtick host | HTTP 200; validation phrase; **no** new helper ([f1-trace-helper-2026-10-12.md](f1-trace-helper-2026-10-12.md), [f1-trace-path-2026-10-12.md](f1-trace-path-2026-10-12.md)) |

**Connection modal** (`/modals/diagnostics-connection-modal.lp`): POST `action=SAVE` + `operation=RESTART` → HTTP 200; transformer logs `async run: /usr/bin/ipping_helper` in the same second ([f1-diagnostics-connection-restart-2026-10-12.md](f1-diagnostics-connection-restart-2026-10-12.md)). Driver: `scripts/f1_diagnostics_connection_control.py`.

Drivers: `scripts/f1_ipping_control.py`, `scripts/f1_ipping_host_probe.py`. Pace requests; stop on nginx **503** after burst probes ([f1-ui-leads-23.1b.md](f1-ui-leads-23.1b.md)).

## Parallel surfaces (not the `:80` Homeware API)

This file maps **session-gated** `*.lp` / `gateway.lp` / `authenticate` on **port 80**. Other listeners use different auth and protocols; they are **not** rows in the tables above.

| Surface | Port / transport | Auth vs web UI | Canonical finding |
| --- | --- | --- | --- |
| WFA WLANConfig (WPS over UPnP) | TCP **49152**; SSDP UDP 1900 | **No** HTTP session on tested LAN SOAP/SUBSCRIBE | [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md), [auth-session-and-wps-2026-10-12.md](auth-session-and-wps-2026-10-12.md) |
| CUPS / IPP | TCP **631** | Browser GET/HEAD **403** (`CUPS v2.2.10` in body); **`application/ipp` POST** allows anonymous reads (e.g. **Get-Jobs** `successful-ok`); helpers `cups-deviced`/`cups-driverd` fail internally; remote queue create blocked; **not** Homeware session | [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md), [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md), [management-auth-boundaries-2026-10-12.md](management-auth-boundaries-2026-10-12.md) |
| Alternate HTTP | TCP **8080** (observed **404** on UI paths) | Unknown handler; not the main UI | [management-auth-boundaries-2026-10-12.md](management-auth-boundaries-2026-10-12.md) |
| Physical UART / BOOT-P (U-Boot) | `serial0` / `ttyS0`, **115200n8**; `b` → BOOT-P | No Linux shell; serial root denied; **LAN wire:** BOOTREQUEST boot file **`GCNT-X`**, no server ([BOOT-P LAN](f1-bootp-lan-2026-10-13.md)); PC BOOTP reply **not tried** | [f1-uart-interaction-2026-10-12.md](f1-uart-interaction-2026-10-12.md), [f1-bootp-lan-2026-10-13.md](f1-bootp-lan-2026-10-13.md), [f1-boot-log-2026-10-12.md](f1-boot-log-2026-10-12.md) |

The admin **WPS form** (`/modals/wireless-wps-modal-newEM.lp`) is still Homeware UI state; **49152** is the separate Wi‑Fi Alliance UPnP registrar/enrollee control plane documented in the WFA finding. No demonstrated chain from UI session to unauthenticated 49152 bypass was shown.

Drivers for 49152: `scripts/wfa_wlanconfig_*.py`, `scripts/wps_device_info.py`.

CUPS :631 index: [docs/f1-cups-631.md](../docs/f1-cups-631.md). Drivers: `scripts/cups_ipp_readonly_matrix.py`, `scripts/cups_ipp_followup.py`, `scripts/cups_ipp_policy_probe.py` (`scripts/test_cups_ipp_readonly_matrix.py` for encoder fixture).

## Not fetched on purpose

`/modals/wireless-qrcode-modal.lp` returns Wi-Fi QR markup (includes key material in the response). **VERIFIED 2026-10-12:** bare GET → HTTP **500**; GET with AP-modal query (`iface`, `broadcastiface`, `splitState`, `band6gOnly`, …) → HTTP **200** when authenticated. See [f1-wireless-qrcode-context-2026-10-12.md](f1-wireless-qrcode-context-2026-10-12.md). Do not archive bodies in git.

## Firmware and keys in the UI

No page and no log row names an update server, a `.rbi` URL, `teliasmartrgw`, or `rgw`. The only `.rbi` mention is the upload extension list in `system-config-min.js`.

System Info does not name a SoC, a flash part, or a Wi-Fi chip.

## Public files (not executed)

Vantiva publishes an EWA1330TCS **19.4** open-source **report** (a PDF list of GPL module names), not a source tree and not a boot image: `https://www.vantiva.com/app/uploads/2024/04/EWA1330TCS_19.4_COSP-3469_external-1.pdf`.

hack-technicolor’s firmware table does not list a GCNT-X bank dump. Issue 321 and this repo’s `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` are sealed RBI images. Decryption was not run again. Ghidra was not used. There is no public GCNT-X executable to open.

## Compared with issue 321

A later public 19.4.0856 GCNT-X boot log, linked from issue 321, does print `CPU : BCM68360_B1`, 4096-byte NAND pages, and an MTD map. That log is not this 23.1.b unit. See `findings/gcnt-x-public-hardware.md`.

This UI pass added nothing on Linux hardware, boot, or OpenWrt. It confirmed the software string `23.1.b` and hardware string `GCNT-X`. At that time no owned-unit boot log was available, and syslog `restricted_shell` references did not establish UART behavior. **Superseded for boot evidence:** [the later supplied capture](f1-boot-log-2026-10-12.md) establishes **4.19.235**, storage/crypto setup and serial invitations; no interactive shell is shown. Driver strings identify Toshiba/KIOXIA-class NAND (`TC58NVG2S0H` in log); **2026-10-14** owner marking **TC58NVG2S0HTAI0** ([f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md)). Wi-Fi chip marking remains unstated; `43684b0` radio-firmware path only.

## Next

The owned-unit boot log and UART input follow-ups are documented in [f1-uart-interaction-2026-10-12.md](f1-uart-interaction-2026-10-12.md). **VERIFIED:** logviewer export shows tty `restricted_shell` and Clash `User root has no serial access` after console activation — serial root shell is policy-blocked on this unit. BOOT-P with a connected LAN Ethernet link is still untested. The public **19.4.0856** reference remains separate — [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md).
