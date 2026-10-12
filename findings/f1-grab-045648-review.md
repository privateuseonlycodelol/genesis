# F1 04:56:48 grab — what is actually new

Date: 2026-10-12. Offline read of `~/Downloads/f1-grab-2026-10-12T04-56-48-913Z.zip` (SHA-256 `607fc0cca3eb0039857a84df5df7cc33fed21dffa02421abbae5092745bd756d`, 123 members, `unzip -t` passed). Compared with the 03:38:53, 04:00:01, and 04:21:31 archives. No router request was sent. Bodies that contain Wi-Fi keys, CSRF tokens, addresses, or SSIDs were not copied into this note.

**Lineage:** [03:38:53 evidence map](f1-grab-033853-review.md) · [04:00:01 script repair](f1-grab-040001-review.md) · [HAR vs seeds](f1-har-coverage-2026-10-12.md) · [API map (GET JSON addendum)](f1-api-map.md) · [grabber doc](../docs/f1-artifact-grabber.md) · Later ~05:57 / `notloggedin.zip` duplicate — [no new evidence](f1-grab-notloggedin-2026-10-12.md)

## Decision

Yes. This is the first finished grab that stores the live Wi-Fi card JSON, the guest-LAN modal, the IPv6 DHCP modal, and the NTP host string, and its PNG bytes are intact. It does not add JavaScript, a firmware image, a QR success, or a POST trace. The 04:00 archive remains the clean script reference; this one is the better HTML-and-JSON package. Treat the zip as secret: it has live CSRF metas and nonempty password fields in the AP, PSK, DynDNS, and L2TP modals.

## Evidence found

**VERIFIED — package shape.** Generated `2026-10-12T04:56:48.765Z`. 114 HTTP 200 bodies, 154 HTTP 404s, one HTTP 500. Queue empty. Reports are the current set (`OUTCOMES.md`, `ACTIONS.md`, `FORMS.md`, `PATH-LITERALS.md`) plus an empty traffic tap (0 events). `REDACTED` occurs zero times in bodies; 13 CSRF name attributes are present, so these are verbatim responses. Every hit-hash cell in `INDEX.md` is blank. `TRAFFIC.jsonl` is empty.

**VERIFIED — Wi-Fi card GET returns data.** `GET /ajax/wirelesscard.lua` is still 0 bytes. `GET /ajax/wirelesscard.lua?auto_update=true` is 127 bytes, `Content-Type: application/json`, chased from `/js/004_wireless.js`. The body is a two-element array. Each object has `listatus`, `ssid`, and `radio`. Both `listatus` values are `light green`. The radios are `2.4 GHz` and `5 GHz`. SSID lengths are 7 and 11; the names are not recorded here. SHA-256 `b0896786a7169a96964dc8eeb5f952512eaccaf1103366914dfb6b1dd78549a9`. This member is absent from the 04:21 archive. The grabber left the outcome as `http-200` with no JSON keys because `summarizeOutcome()` only records keys for JSON objects, and this body is an array.

**VERIFIED — guest LAN is a different modal.** `GET /modals/ethernet-modal.lp?intf=guest` (HAR import, 5535 bytes) is not the bare LAN modal (6220 bytes) after CSRF and digit normalization. The guest page’s active tab is `guest`. Pool fields are `dhcpStartAddressguest`, `dhcpEndAddressguest`, and `leaseTimeguest`. The LAN page uses the `lan` names and also has static-lease controls (`sleases`, add-lease) that the guest page does not. Switcher classes are `switcher` and `switcher switcherOn` on guest, and two `switcherOn` on LAN. Disabled-attribute counts are 5 and 2. Addresses are not recorded here. Absent from the 04:21 archive.

**VERIFIED — NTP hosts.** `GET /modals/time-management-modal.lp?getNTP=true&auto_update=true` is 42 bytes, content type `application/json`. The body is the JSON string `ntp-cust1.telia.com, ntp-cust2.telia.com`, including the surrounding quotes. SHA-256 `cb282a4523d78eeb93dfd5238fc77fc0b8b19883750a98ce009bb7e1cb773787`. Absent from the 04:21 archive. The grabber stored no JSON keys because the value is a string, not an object.

**VERIFIED — IPv6 DHCP modal is new in this set.** `/modals/internet-dhcpv6-routed.lp` is 3366 bytes, chased from `/modals/internet-ex-modal.lp`. It is absent from the 03:38, 04:00, and 04:21 archives. Field name present: `uci_wan_auto`. It is not byte-identical to `internet-ex-modal.lp` (3461 bytes); the ex modal carries a POST form whose action is `modals/internet-ex-modal.lp`. `/modals/internet-dhcp-routed.lp` is present again (6660 bytes). Against the 03:38 copy, CSRF-and-digit normalization leaves a single-character difference in a packet counter (`6` versus `3` before the `Pkd` label).

**VERIFIED — action responses that differ from the page.** Normalized the same way as grabber 1.7.3 `normalizeForFingerprint` (CSRF values removed; digit runs of length ≥2 collapsed in HTML):

| Request | Bytes | Against bare page | Against `action=gf1nosuchaction` |
| --- | ---: | --- | --- |
| `/gateway.lp?action=scheduleReboot` | 184 | different | different |
| `/modals/parental-modal.lp?action=smartwifi` | 40 | different | different |
| `/modals/system-config-modal.lp?action=getbanksize` | 44 | different | different |
| `/modals/system-config-modal.lp?action=upgradefwstatus` | 3944 | different | same |
| `/gateway.lp?action=` and `?auto_update=` and `?auto_update=true` | 17267 | same bytes | same |

`scheduleReboot` JSON keys: `systemTime` = `2026-10-12T06:49:19Z`, `rebootTime` = `0001-01-01T23:58:00Z`, `popupHeader` = `Reboot Schedule`, `alertMsg` length 62. SHA-256 `2e529d7ed896492d5eca37ffc243277dac638339789e0788fe69e8cd616ee172`. Year 0001 is the stored reboot date. `smartwifi` is `{"current_state":"1","current_phase":""}`, SHA-256 `6018711f4fdd8bde2b461f4049bdada448b36728c6c3441e135e7ca944a3019e`. `getbanksize` is `{"success":"true","banksize":"134217728"}` (the string `true`, which is why the grabber did not note `success=true`), SHA-256 `9e96c830d9644552e74abc8797b4fa6914f15f62e2d581d85a212f0ed9b2dd3c`. That bank size is 128 MiB and matches the earlier live control.

`upgradefwstatus` matches the invalid-action control once CSRF text is removed. Both differ from the bare configuration modal by deletion of the six characters `active`. The radio modal’s client treats smartwifi phase `"1"` and `"2"` differently; this sample’s phase is empty, so it does not land on the phase-`"1"` branch (`files/js__wireless-radio-modal-newEM.js`).

`GET /login.lp?auto_update=true&getSessionStatus=true` and the gateway poll are the same 24 bytes: `{"current_role":"admin"}`, SHA-256 `ac77f908c17884c7352cf857a1304f0a28dedb9124cd5a0d60f5adc559cb9bed`.

**VERIFIED — binaries and static duplicates.** PNG members start with a real PNG signature. `gateway.png` is 2040×1788, 8-bit RGB, 208301 bytes. The 04:21 copies of the shared PNGs start with `EF BF BD` (UTF-8 replacement of the `89` signature byte) and are larger. Cache-bust copies (`?_=…` and the `23.1.b.0448-…` query on `gw.css`, `login.js`, and `main-min.js`) are byte-identical to the bare files. The font member is a `wOFF` payload, 43572 bytes, from the double-slash path `/font/fontawesome//fontawesome-webfont.woff?v=3.2.1`.

**VERIFIED — scripts and firmware label.** Every canonical script that also exists in the 04:00 archive is byte-identical to it, including the six files that were corrupted in the 03:38 grab. The only script absent from all three earlier archives is `/js/ipv6devices-modal-min.js` (894 bytes), chased from the IPv6 devices modal. It only shows or hides table columns from `featureFlag` and rewrites a priority cell between `ON` and `OFF`. System Info still shows firmware `23.1.b.0448-7241017-20260223134332`. `asmcrypto-min.js` still points at `asmcrypto.js.map`; that map is not in the zip.

**VERIFIED — QR is still the bare 500.** `/modals/wireless-qrcode-modal.lp` at `2026-10-12T04:48:26.213Z` is HTTP 500, 572 bytes, body class `http-500`, method `seed-known-modal`, no query string. The saved excerpt is the generic nginx 500 page. The AP modal still has two `data-remote` links to that route with keys `band6gOnly`, `broadcastiface`, `iface`, `isCompatibility`, `ispremium`, and `splitState`. No query-bearing QR body was saved.

**VERIFIED — this log window.** The log table has 214 `Oct 12 HH:MM:SS` stamps from 06:33:16 through 06:47:42, newest first. Lua sites: `sessionmgr.lua:264` (30), `session.lua:354` (3), `wireless_qr.lua:48` (3), `web.lua:249` (1). The QR rows at 06:42:54 name `/www/lua/wireless_qr.lua:48`, `attempt to index local 'password' (a nil value)`, function `format`, and `/usr/lib/lua/web/web.lua:249` function `process`. The 500 above is timestamped 04:48:26Z. If the log clock is UTC+2 wall time, 06:47:42 is 04:47:42Z, about 44 seconds before that 500, and the 06:42:54 QR trace is an earlier failure. `session.lua:354` says `new(): new session for default user` on `GET /`, next to `redirectIfNotAuthorized()` on the same request shape. The pinned `tch-nginx-gui` `session.lua` logs that sentence from `M.new` at line 352, using the fallback string when `default_user` is missing or nameless. Same message and function, two-line offset, so this is the same call shape and not proof the on-device file matches that blob. Creating that session is the line immediately followed, in this window, by an unauthorized `GET /`.

**DERIVED — device clock label.** `systemTime` `2026-10-12T06:49:19Z` sits just after the log’s last stamp 06:47:42 and about seven minutes before the zip’s local file time 06:56. That lines up with the grab’s 04:48Z–04:56Z miss window if those `Z` fields are local wall time rather than UTC. The suffix alone does not prove the timezone.

## What changed

The 04:21 archive is larger (228 hits, 831 still queued) and already contained `scheduleReboot`, `smartwifi`, and `getbanksize`, plus a wide `?action=` matrix on unrelated modals that came back as the modal HTML. It did not contain the Wi-Fi card array, the NTP string, the guest modal, `internet-dhcpv6-routed.lp`, or valid PNGs. Its shared PNG members are text-corrupted. This 04:56 run finished the queue and kept the responses that differ from the page.

The 154 misses are padded nginx 404 pages (548 bytes, title `404 Not Found`), almost all `guess-js-to-modal` / `guess-modal-to-js` / `guess-modal-stem-min`. They do not add routes. `password-reset.lp`, `overview.lp`, `system.lp`, `robots.txt`, and the well-known files are in that 404 set. `submenu=yes` on the SSID modals only moves the `active` class. `contentsharing-modal.lp?auto_update=true` only drops `active`.

## Next attack on the problem

The QR handler is still untested with the six query keys the AP page actually emits. Capture that one GET and a log slice that overlaps it, so `wireless_qr.lua:48` can be tied to a response. A matching `wireless_qr.lua` would decide whether a nil password is missing query context or a missing configuration object.

Second, compare one authenticated POST of `/ajax/wirelesscard.lua?auto_update=true` with this GET array. The GET already returns `listatus`, `ssid`, and `radio`. The open question is whether the POST adds fields the dashboard does not get from GET.
