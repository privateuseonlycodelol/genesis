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

There is no separate JSON API. The `.lp` pages are the API. Each saved modal is a form whose `method` is `post` and whose `action` is its own path, plus `CSRFtoken`.

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
| `/modals/diagnostics-ping-modal.lp` | Ping form |
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

**Verified:** the configuration HTML does not contain `#file-upgradefw`, `#btn-system-bootp`, or the export/import controls. Those handlers are in the script only.

**Hypothesis:** the 23.1.b template dropped the upgrade and backup controls and left the shared script. Whether a hand-built POST would still be accepted was not tested.

`main-min.js` also GETs `/gateway.lp?action=scheduleReboot` to read a scheduled time. That URL was not called again.

## Not fetched on purpose

`/modals/wireless-qrcode-modal.lp` would show the Wi-Fi key. It was left alone.

## Firmware and keys in the UI

No page and no log row names an update server, a `.rbi` URL, `teliasmartrgw`, or `rgw`. The only `.rbi` mention is the upload extension list in `system-config-min.js`.

System Info does not name a SoC, a flash part, or a Wi-Fi chip.

## Public files (not executed)

Vantiva publishes an EWA1330TCS **19.4** open-source **report** (a PDF list of GPL module names), not a source tree and not a boot image: `https://www.vantiva.com/app/uploads/2024/04/EWA1330TCS_19.4_COSP-3469_external-1.pdf`.

hack-technicolor’s firmware table does not list a GCNT-X bank dump. Issue 321 and this repo’s `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` are sealed RBI images. Decryption was not run again. Ghidra was not used. There is no public GCNT-X executable to open.

## Compared with issue 321

The public note `docs/gcnt-x-public-hardware.md` already says: no SoC part, no flash part, no Wi-Fi chip, NAND in a TSOP48 package as a guess, CFE shell removed, 23.1.b not downgradable, serial input often dead.

This UI pass adds nothing on Linux hardware, boot, or OpenWrt. It confirms the running software string `23.1.b` and the hardware version string `GCNT-X`, and it shows the admin UI is ordinary forms plus a log table. The log’s `restricted_shell` lines match the issue’s “no serial root” reports. They are not a shell from this Mac.

## Next

Read the serial boot log on Tuesday. Read only. Do not flash.
