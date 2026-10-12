# F1 `notloggedin.zip` — mislabeled duplicate (no new evidence)

Date: 2026-10-12. Offline read of `~/Downloads/notloggedin.zip` (SHA-256 `73a3b78f8e4be68f6e85407d5544a281cacfaf25a133d53bd0c8f38ad092ab12`, 125 members, `unzip -t` passed). Compared with `~/Downloads/f1-grab-2026-10-12T05-57-18-863Z.zip` (SHA-256 `9c38c33f3facafa1d02a01b5ffacc1a010e15c939411929f223370a4d0e04f55`). No router request was sent. Live credentials, CSRF tokens, Wi-Fi keys, guest passwords, VPN PSK, serial numbers, and client hostnames are not copied into this note.

**Lineage:** Twin archive `f1-grab-2026-10-12T05-57-18-863Z.zip` (offline diff) · [04:56:48 finished grab](f1-grab-045648-review.md) · [Unauthenticated boundary controls](f1-hidden-action-boundary-2026-10-12.md) · [Grabber doc](../docs/f1-artifact-grabber.md) · [API map GET JSON addendum](f1-api-map.md)

## Decision

**No new verified research outcome.** Despite the filename, this archive is an **authenticated admin** Tampermonkey export taken **~4 minutes after** the `05-57-18-863Z` zip (`INDEX.md` generated `2026-10-12T06:01:30.000Z` vs `2026-10-12T05:57:18.863Z`). It does **not** document what the gateway returns with **no session cookie**; that case is already covered in [`f1-hidden-action-boundary-2026-10-12.md`](f1-hidden-action-boundary-2026-10-12.md) and [`management-auth-boundaries-2026-10-12.md`](management-auth-boundaries-2026-10-12.md).

Treat the zip as **secret** (same sensitivity as other finished grabs).

## Evidence found

**VERIFIED — package shape.** 114 HTTP 200 bodies in `INDEX.md`, 138 misses, empty traffic tap (0 events). Grabber reports match the 1.8.x layout (`OUTCOMES.md`, `ACTIONS.md`, `FORMS.md`, `PATH-LITERALS.md`, `EXTERNAL-URLS.md`, `TRAFFIC.md`). `REDACTED` does not appear in saved bodies.

**VERIFIED — session is admin, not “logged out”.**

| Signal | Observation |
| --- | --- |
| `files/gateway.lp.html` | Full Advanced dashboard HTML (~17,267 B) with “Sign out” / “User” chrome, not the 5,784-byte login shell |
| `files/login.lp.html` | Login form HTML is still served while the grabber’s cookie is valid (expected Homeware behavior) |
| `GET …getSessionStatus=true` on `gateway.lp` and `login.lp` | Both bodies are 24 bytes, JSON key `current_role` with value `admin` (same SHA-256 as the 04:56:48 and 05:57:18 archives for this body) |
| CSRF meta on `gateway.lp` | Same token value as the `05-57-18-863Z` zip (per-archive session binding; value not recorded here) |

**VERIFIED — why the grabber still hit JSON probes.** `GM_xmlhttpRequest` GETs inherit the **browser cookie jar** for `192.168.2.1`. Optional `probe-get-action` / `probe-get-session` rows therefore reflect **whatever session the tab holds**, not “no cookie.” Filename and visiting `login.lp` do not clear that jar.

**VERIFIED — diff vs `05-57-18-863Z.zip`.**

| Category | Count | Notes |
| --- | ---: | --- |
| Members only in `notloggedin.zip` | 23 | Mostly `files/img__device-icons__*.png` and UI chrome chased from `device-modal.lp`; plus `files/modals__internet-dhcp-routed.lp.html` (already present in the [04:56:48 grab](f1-grab-045648-review.md)) |
| Members only in `05-57-18-863Z.zip` | 0 | — |
| Byte-identical between the two zips | 89 | Includes all canonical `/js/*.js` seeds and most modal HTML |
| Same path, different bytes | 13 | Ephemeral fields only: `scheduleReboot` `systemTime` (+13 s), configuration modal `system_time` labels, system-info uptime (+5 s) and memory (79% → 77%), IPv6 device lease timers, and regenerated markdown tables (`INDEX.md`, `MISSES.md`, …) |

**VERIFIED — no new routes or action semantics.** Confirmed GET JSON actions match prior archives: `scheduleReboot`, `smartwifi`, `getbanksize`; `upgradefwstatus` still `IGNORED_PARAMETER` (same normalized HTML as `gf1nosuchaction`). `GET /ajax/wirelesscard.lua?auto_update=true` remains the two-object Wi-Fi card array. `wireless-ap-modal-newEM.lp?action=modeChange` and `?action=split_ssid` differ from the bare modal by HTML layout only (split-SSID preview), not new JSON APIs.

**VERIFIED — `TRAFFIC.jsonl` empty.** No POST/XHR tap during this export; no new wire behavior for form saves.

## What changed

Nothing material. The archive **confirms** that UI-grab JSON probes are **session-scoped** and that a misleading export name does not override cookie state. It does **not** refute the separate **no-cookie** controls that returned login HTML for `getbanksize`, `scheduleReboot`, `export_config`, and the session poll.

## Next attack on the problem

For a true **unauthenticated** UI surface map, run the grabber after **Sign out** (or a fresh profile), export under an explicit name (e.g. `anonymous-cookie-only`), and compare `OUTCOMES.md` against [`f1-hidden-action-boundary-2026-10-12.md`](f1-hidden-action-boundary-2026-10-12.md). Higher value than another admin duplicate: finish QR `GET` with the six query keys from the AP modal, or one paired POST vs GET on `wirelesscard.lua`.
