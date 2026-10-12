# F1 HAR coverage vs grabber seeds — 2026-10-12

**Tool:** `scripts/analyze_f1_har.py`  
**Inputs:** local browser HAR files `1.har`–`8.har` (same host). `7.har` alone is 444 entries. The union is 1,128 entries.  
**Rule:** same host-path filter as the grabber (`isWanted`), plus `action` / session-poll query keys. Response text, cookies, and query values other than action names were not printed.

## What was run

**VERIFIED:** `7.har` has 444 entries, all one host. 438 requests match the grabber’s path filter: **334 GET, 104 POST**. **47** distinct paths were actually requested. Bodies contain **51** path literals; **9** of those were never requested in the HAR.

**VERIFIED:** union of `1.har`–`8.har` has the **same 47 paths** and the **same 9 unrequested literals**. Extra files repeat the session. They do not add routes.

## Does the live grabber find more than this HAR?

**Yes, for pages the HAR never opened.** **24** current seed paths are absent from every one of these HARs, including `device-modal.lp`, `internet-modal.lp`, `broadband-modal.lp`, `wireless-ap-modal-newEM.lp`, `wireless-radio-modal-newEM.lp`, `wireless-wps-modal-newEM.lp`, `logviewer-modal.lp`, and the matching `/js/*` files. The grabber fetches those from its seed list without waiting for the HAR. A log line `seed-known-js` / `seed-known-modal` is that refill, not a newly discovered route.

**The HAR has six paths outside the seed lists.** One matters: `POST /ajax/wirelesscard.lua` → 200. The other five are images and a font. A bare `GET /ajax/wirelesscard.lua` is not that POST.

**VERIFIED later (04:56:48Z UI grab, offline):** `GET /ajax/wirelesscard.lua?auto_update=true` with an admin session returns JSON (two radios: `listatus`, `ssid`, `radio`). Bare `GET` without the query is still 0 bytes. See [`f1-grab-045648-review.md`](f1-grab-045648-review.md). POST versus that GET was not compared in the grab.

**Action names on the wire (1–8 union):** `scheduleReboot` (16 in `7.har`, 48 across 1–8) and `smartwifi` (3 / 11). No `TABLE-*` or wanservices `SAVE` in that union.

**Separate file `wanetc.har` (not in 1–8):** first repo capture of `POST /modals/wanservices-modal.lp` with `TABLE-NEW` / `TABLE-ADD` / `TABLE-DELETE` / `SAVE` on `portforwarding` and `fwrules_v6`. See [f1-har-wanetc-2026-10-12.md](f1-har-wanetc-2026-10-12.md). Still no broadband/ethernet/internet modals in that HAR.

## Gap pages

| Path | In HAR 1–8 | In body text of 7.har |
| --- | --- | --- |
| `basicview-wifissid-modal.lp` and 5 GHz twin | GET 200 | yes |
| `basicview-wifipsk-modal.lp` and 5 GHz twin | GET 200 | yes |
| `basicview-wifiguest-modal.lp` and 5 GHz twin | GET 200 | yes |
| `internet-ex-modal.lp` | not requested | **0** occurrences |
| `ipv6devices-modal.lp` | not requested | **0** occurrences |
| `wireless-qrcode-modal.lp` | not requested | **0** occurrences |

**VERIFIED:** the six guided Wi‑Fi modals are already successful GETs in the HAR. Importing the HAR does not discover them; the grabber only needs to fetch them if its cache is empty.

**VERIFIED:** `internet-ex`, `ipv6devices`, and `wireless-qrcode` do not occur anywhere in `7.har`. They are not queued by HAR import because they are not in the file. `wireless-ap-modal-newEM.lp` is a literal (**123** mentions) but was **not requested**. The QR route is linked from that modal in other captures, so it cannot show up until that modal body is fetched and chased. The earlier recorded QR **500** is from a grabber GET, not from these HARs.

**Update:** the [04:56:48Z finished grab](f1-grab-045648-review.md) later saved `internet-ex-modal.lp`, `ipv6devices-modal.lp`, and `internet-dhcpv6-routed.lp` via seed/chase; QR remains a bare-path **500** there too.

**Literals the HAR never requested:** `home.lp`, `password-reset.lp`, `modals/tod-modal.lp`, `modals/wireless-ap-modal-newEM.lp`, `js/media-min.js`, `css/font-awesome-ie7.css`, `img/loading.gif`, and two extra font files. `password-reset.lp` is a string only here; an earlier grab recorded it as 404.

## Query actions are not real just because HTTP is 200

**VERIFIED on `7.har`:** `GET /gateway.lp?action=scheduleReboot` is **184 bytes** and its SHA-256 **differs** from bare `GET /gateway.lp`. One earlier `scheduleReboot` response is **5784 bytes** and also differs. `GET /modals/parental-modal.lp?action=smartwifi` is **40 bytes** and differs from the bare modal. In this HAR those actions are distinct responses, not copies of the page.

A live grab that shows many actions (`scheduleReboot`, `smartwifi`, `upgradefwstatus`, `getbanksize`, `system_reboot`, `system_reset`) all returning the **same ~5980 byte HTML** is the other case: the server ignored the action and returned the default page. Grabber **1.6.5** hashes each query response against the same path with no query. An identical hash is labeled `ignored-action-default-page` and is not chased as a new page. A different hash is labeled `differs-from-bare-page`. HTTP 200 alone is not treated as proof the action exists.


## What this does not show

No new live GET was made. POST response bodies were not replayed. A path missing from the HAR is not a 404.
