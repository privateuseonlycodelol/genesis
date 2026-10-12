# Uploaded F1 HARs (12 Oct 2026)

Local read of five browser captures. No router was contacted. Passwords, Wi-Fi keys, serials, MAC addresses, WAN addresses, cookies, session material, and CSRF values are omitted.

Already known, and not treated as new: Telia F1 admin UI on Homeware 23.1.b, SRP login, modal `.lp` pages as a class, `GET` `upgradefwstatus` returning config-modal HTML when idle, and `GET` `getbanksize` returning JSON `banksize` 134217728.

These five files are one nested session. Each later file starts with the previous file’s entries. Every request is `http` to the LAN admin host. No other host appears. None of the files contain `upgradefwstatus`, `getbanksize`, `banksize`, or the substring `bank`. The HTML repeats the known build `23.1.b.0448-7241017-20260223134332` as a cache key, and the advanced page title is **Telia F1** with card text **Version 23.1.b**. No `GCNT`, `EWA1330`, or `Homeware` string is in the bodies.

## 1_a48a.har

40 entries, 02:07:48Z–02:08:17Z. Login, then the advanced gateway page.

Distinct requests:

| Method | URL | action | Status | Body |
| --- | --- | --- | --- | --- |
| GET | `/` | | 200 | HTML. 5784-byte login page, then 2287-byte simplified shell |
| GET | `/login.lp` | query `auto_update`, `getSessionStatus` | 200 | JSON `current_role` empty |
| POST | `/authenticate` | | 200 | JSON. Two SRP steps (fields `I`/`A`, then `M`) |
| GET | `/gateway.lp` | `scheduleReboot` | 200 | HTML login page while logged out (5784). JSON after login (184): `popupHeader` Reboot Schedule, `rebootTime` `0001-01-01T23:58:00Z` |
| GET | `/gateway.lp` | | 200 | HTML 17267. Title Telia F1 |
| POST | `/gateway.lp` | `URL` | 200 | HTML 17267. `urlVal` is the LAN `gateway.lp` URL |
| POST | `/ajax/wirelesscard.lua` | query `auto_update` | 200 | JSON. Two radios, 2.4 GHz and 5 GHz, `listatus` light green |
| GET | `/favicon.ico` | | 404 | HTML 548 |
| GET | `/css/gw.css`, `/css/responsive.css` | | 200 | CSS |
| GET | `/js/main-min.js`, `/js/jquery-eval-patch.js`, `/js/srp-min.js`, `/js/login.js`, `/js/asmcrypto-min.js`, `/js/chart-min.js`, `/js/004_wireless.js`, `/js/gateway.js` | | 200 | JavaScript |
| GET | `/img/logo.png`, `/img/gateway.png`, `/img/connection-established.png`, `/img/network_sans-32.png` | | 200 | PNG |
| GET | `/font/fontawesome//fontawesome-webfont.woff` | | 200 | font |

Login copy says the standard username is `User` and names the box a MediaAccess Gateway. Simplified shell copyright line is Technicolor 2026. Login and advanced pages say Vantiva 2026. Simplified shell links `modals/basicview-accesscode-modal.lp` and `/password.lp`. Those two are not fetched.

**New versus the known set:** `POST /ajax/wirelesscard.lua`, and `POST /gateway.lp` with `action=URL`. Logged-out `action=scheduleReboot` returns the login HTML, not the 184-byte JSON. SRP and the authenticated `scheduleReboot` JSON are the known admin UI. The [04:56:48Z UI grab](../findings/f1-grab-045648-review.md) also recorded the same wireless-card payload on authenticated `GET …?auto_update=true` (127 bytes); this HAR shows POST only.

Advanced `gateway.lp` HTML links these modal paths. They are not requested in this file: `system-info-modal.lp`, `broadband-modal.lp`, `internet-modal.lp`, `wireless-ap-modal-newEM.lp`, `ethernet-modal.lp`, `device-modal.lp`, `firewall-modal.lp`, `wanservices-modal.lp`, `diagnostics-connection-modal.lp`, `diagnostics-network-modal.lp`, `dmz-modal.lp`, `l2tp-ipsec-server-modal.lp`, `parental-modal.lp`, `tod-modal.lp`, `contentsharing-modal.lp`.

## 2_8c3b.har

63 entries, through 02:08:39Z. Contains file 1, then two modals.

**New requests:**

| Method | URL | action | Status | Body |
| --- | --- | --- | --- | --- |
| GET | `/modals/dmz-modal.lp` | | 200 | HTML 1995 |
| GET | `/modals/l2tp-ipsec-server-modal.lp` | | 200 | HTML 3061 |
| GET | `/js/dmz-modal-min.js` | | 200 | JavaScript 528 |
| GET | `/img/spinner.gif` | | 200 | GIF |
| GET | `/gateway.lp` | query `auto_update`, `getSessionStatus` | 200 | JSON `current_role` `admin` |

`dmz-modal.lp` is the **Bridge ETH port 4** panel, not a host-DMZ form. `DMZ_enabled` is `0`. Copy says enabling it restarts the MediaAccess Gateway.

`l2tp-ipsec-server-modal.lp` is **VPN Server**. `vpnserver_enable` is `0`. `proxyarp` is `1`. A pre-shared key field and local/remote address fields are present; those values are omitted.

## 3_6566.har

81 entries, through 02:09:01Z. Contains file 2. The tail is another full `gateway.lp` load, `action=scheduleReboot`, and `POST /ajax/wirelesscard.lua`. **No new endpoint.**

## 4_6448.har

84 entries, through 02:09:11Z. Contains file 3.

**New requests:**

| Method | URL | action | Status | Body |
| --- | --- | --- | --- | --- |
| GET | `/modals/parental-modal.lp` | | 200 | HTML 4379 |
| GET | `/modals/parental-modal.lp` | `smartwifi` | 200 | JSON `current_state` `1`, `current_phase` empty |

The parental HTML links `/modals/parental-modal.lp` and `/modals/tod-modal.lp`. `tod-modal.lp` is still not fetched. Site blocking control `sitesEnabled` is `0`. Visible copy says the Smart Wi-Fi service is active.

## 5_fe07.har

107 entries, through 02:09:26Z. Contains file 4. Extra session polls and another `action=smartwifi` repeat are not new endpoints.

**New requests:**

| Method | URL | action | Status | Body |
| --- | --- | --- | --- | --- |
| GET | `/modals/contentsharing-modal.lp` | | 200 | HTML 8873 |
| POST | `/modals/contentsharing-modal.lp` | `SAVE` | 200 | HTML 9161. Page text includes “Changes saved successfully” |
| POST | `/modals/contentsharing-modal.lp` | `AJAX-GET` | 200 | JSON body, `Content-Type` `text/html`, 80 bytes |

`AJAX-GET` posts `requested_params=connecteddevices`. The JSON field `connecteddevices` says there are no connected devices.

Sharing labels on the modal: Samba name **Vantiva**, workgroup **WORKGROUP**, description **Vantiva Gateway**, DLNA name **Telia F1**, profiler status **Idle**, USB 3.1 enabled (`usb3Enabled` `1`). The save sets `samba` and `sambaFilesharing` to `1`, `storageInterface` `0`, `diskProtection` `0`, `dlnaEnabled` `0`. The password field is omitted. The dashboard HTML captured before this save still said Samba filesharing disabled and DLNA disabled.

## Still absent (in files 1–5 above)

No request for `upgradefwstatus` or `getbanksize`. No bank name, bank size, or firmware-upgrade endpoint. `logviewer` and `system-config` do not appear. The modal paths listed under file 1, other than dmz, L2TP, parental, and content sharing, were only linked, not loaded.

## wanetc.har (standalone, 12 Oct 2026)

**Not** nested with `1_a48a`–`5_fe07`. **64** entries, `06:41:51Z`–`06:43:34Z`. SHA-256 `deaecf9c837035a9b1a2c5c5a62c37181a242aa757169d6ec2e77673b9e6f677`. Full write-up: [f1-har-wanetc-2026-10-12.md](../findings/f1-har-wanetc-2026-10-12.md).

Despite the filename, there is **no** `broadband-modal.lp`, `ethernet-modal.lp`, or `internet-modal.lp`. The new material is **WAN Services** interaction:

| Method | URL | `action` | Notes |
| --- | --- | --- | --- |
| GET | `/modals/wanservices-modal.lp` | | 13,146 bytes (same hash as UI grab) |
| GET | `/modals/dyndns-wanservices-modal.lp` | | Tab only; no DynDNS POST |
| POST | `/modals/wanservices-modal.lp` | `TABLE-NEW`, `TABLE-ADD`, `TABLE-DELETE` | IPv4 `portforwarding` and IPv6 `fwrules_v6` tables |
| POST | `/modals/wanservices-modal.lp` | `SAVE` | Two saves with “Changes saved successfully”; UPnP/NAT-PMP toggled on then off (field values omitted) |

Also repeats `POST /gateway.lp` `action=URL`, `POST /ajax/wirelesscard.lua`, and session polls. All **200**. No secrets reproduced in the finding.
