# REA + offline HAR/UI pass (2026-10-17)

**Scope:** Owned-unit Telia F1 **23.1.b** evidence already on disk. **No live router requests** in this pass.

## Artifact inventory (VERIFIED on Mac)

| Location | Contents |
| --- | --- |
| `artifacts/ui/192.168.2.1.browser.har` | 22 entries — early login + partial admin |
| `artifacts/hars/wanetc.har` | 64 entries — WAN Services (copy of Downloads `wanetc.har`) |
| `artifacts/hars/7.rea-sanitized.har` | 444 entries — from `~/Downloads/7.har` |
| `artifacts/hars/newone.rea-sanitized.har` | 254 entries — from `~/Downloads/newone.har` |
| `artifacts/ui/har7-js/` | 10 JS files extracted from `7.har` (subset of admin UI) |
| `artifacts/ui-grab-20261012T033853Z/` … `T040001Z/` | Tampermonkey grab trees (private index files) |
| `~/Downloads/1.har`–`8.har`, `7.har`, `wanetc.har`, `newone.har` | Additional browser exports (not all re-ingested) |

UI grabs and HARs remain **gitignored** under `artifacts/`; this note records paths only.

## REA work performed

| Tool | Target | Outcome |
| --- | --- | --- |
| `inspect_web_network_capture` | `wanetc.har`, `192.168.2.1.browser.har`, sanitized `7.har`, sanitized `newone.har` | **VERIFIED** decode (64 / 22 / 444 / 254 records) |
| `inspect_analysis_view` `api-surface` | `wanetc.har` | 20 method+path groups; confirms `POST /modals/wanservices-modal.lp` table ops + `POST /ajax/wirelesscard.lua?auto_update` |
| `inspect_analysis_view` `api-surface` | `7.rea-sanitized.har` | 54 groups total (50+4 paged); aligns with [`f1-har-coverage-2026-10-12.md`](f1-har-coverage-2026-10-12.md) |
| `analyze_javascript_application` | `artifacts/ui/har7-js` | 10 parsed JS files; partial graph (20k+ semantic unknowns) |
| `trace_application_feature` | seed `export_config` on har7-js graph | **No match** — not evidence of absence (subset lacks `system-config-min.js` export string) |
| `inspect_pcap_capture` | `artifacts/bootp/2026-10-13/wan.pcapng` | **BLOCKED** on macOS (REA needs Linux prlimit or Windows Job Objects) |

## Genesis scripts (same pass)

- `scripts/inspect_ui_har.py` on `192.168.2.1.browser.har` — login flow + SRP POSTs.
- `scripts/analyze_f1_har.py` on `7.har` — 444 entries, 47 wire paths, gap list (unchanged vs prior finding).
- Cross-HAR POST inventory — `newone` vs `7` (see below).

## New / tightened observations

1. **REA HAR ingest blocker (DERIVED):** Chrome exports can set `serverIPAddress` to `""`. REA `har-schema` rejects that (`invalid_format` ipv4). **VERIFIED** on `7.har` entry 266 (`diagnostics-ping-modal.lp`). Fix: `scripts/sanitize_har_for_rea.py` → writes `*.rea-sanitized.har` with `192.168.2.1` placeholder (1 entry fixed in `7.har` and `newone.har`).

2. **`newone.har` wireless card (VERIFIED):** Contains **`GET /ajax/wirelesscard.lua?auto_update=true`** (200, **127**-byte JSON) twice, plus one matching **POST** with the same query and size. Corroborates [04:56:48Z grab](f1-grab-045648-review.md); not a new API shape (bare `/ajax/wirelesscard.lua` without query still absent here).

3. **`newone.har` routes not in `7.har` (VERIFIED method+path set diff):** `GET /modals/tod-modal.lp`, `GET /js/tod-modal-min.js`, `POST /modals/l2tp-ipsec-server-modal.lp`, `POST /modals/parental-modal.lp`, `POST /modals/system-info-modal.lp` — diagnostics-heavy `newone` session vs content-sharing-heavy `7.har`.

4. **har7-js static trace:** `export_config` does not appear in the extracted `7.har` JS slice; export is driven from `system-config-min.js` (full grab), already documented under hidden `export_config` POST.

## What was not shown

- No new exploit, key, decrypt, or live UI behavior.
- No REA ingest of raw `7.har` / `newone.har` without sanitize step.
- No CDP live browser (`capture_browser_scenario` / `inspect_web_page`) — router not on LAN / login state unknown.
- No PCAP REA on this Mac for BOOT-P pcaps.

## Reproduction

```sh
python3 scripts/sanitize_har_for_rea.py ~/Downloads/7.har artifacts/hars/7.rea-sanitized.har
python3 scripts/analyze_f1_har.py ~/Downloads/7.har
python3 scripts/inspect_ui_har.py artifacts/ui/192.168.2.1.browser.har
```

REA: `inspect_web_network_capture` with `capture_path` pointing at sanitized HAR, `format: "har"`, `detail: "summary"`; then `inspect_analysis_view` with `kind: "api-surface"` on returned `parent_evidence_id`.

## Next feasible work (when unblocked)

- Live LAN: `observe_web_session` or paced single-modal probe after `/login.lp` → 200.
- Linux VM or Windows host: REA `inspect_pcap_capture` on `artifacts/bootp/2026-10-13/wan.pcapng`.
- ~~Full JS graph: `analyze_javascript_application` on a complete UI grab `files/` tree (not har7-js subset).~~ Done 2026-10-27, see addendum below.

## Addendum (2026-10-27) — full UI grab JS tree, offline only

**Scope:** `artifacts/ui-grab-20261012T040001Z/files/` (24 JS files) vs. the 10-file `har7-js` subset used on 2026-10-17. No live router requests.

**VERIFIED — `export_config` driver located (closes the 10-17 "no-match"):** `js__system-config-min.js` contains the click handler:

```js
$(".export-config").click(function(){
  $.fileDownload(target,{httpMethod:"POST",
    data:[{name:"action",value:"export_config"},{name:"CSRFtoken",value:$("meta[name=CSRFtoken]").attr("content")}], ...});
});
// target = $(".modal form").attr("action")
```

This is a plain POST to the modal's own form action (jQuery `fileDownload` plugin, iframe-based download) — no hidden endpoint, no alternate trigger, no client-side encryption/key material touched before the request leaves the browser. Consistent with (not contradicting) the already-VERIFIED live capture in [f1-hidden-action-boundary-2026-10-12.md](f1-hidden-action-boundary-2026-10-12.md) (`POST export_config` → 200, 181137-byte envelope). The 10-17 "no-match" was a tooling gap (subset lacked this file), not evidence the trigger doesn't exist — now resolved.

**VERIFIED negative result — 14 files new vs. the 10-17 subset** (`device-min.js`, `internet-dns-min.js`, `internet-routed-settings-min.js`, `login.js`, `logviewer-min.js`, `main-min.js`, `media-min.js`, `srp-min.js`, `system-config-min.js`, `tod-modal-min.js`, `wanservices-min.js`, `wireless-ap-modal-newEM.js`, `wireless-qrcode-modal-min.js`, `wireless-radio-modal-newEM.js`): keyword sweep (`debug*`, `backdoor`, `telnet`, `dropbear`, `pwcrypt`, `RIP_ID`, `OSCK`, `eval(`, `action=<name>`) found **no** hidden/undocumented action params, no `eval(`, no hardcoded secrets, no backdoor/debug strings. The handful of `action=` hits (`modeChange`, `split_ssid`, `smartwifi`) are already-known params from prior live probing, not new surface. This does not prove absence elsewhere (minified code, string concatenation, or server-side-only logic can hide intent from static grep), but it rules out this specific set of client files as a source of an undocumented route.

**What was not shown:** no new API surface, no key material, no server-side logic (this is 100% client JS); `srp-min.js` in this tree was not diffed byte-for-byte against the pinned `f1-grab_js_srp-min.js` baseline used in the password-encoding track — that diff is still open.

**Next:** diff this tree's `js__srp-min.js` against the pinned SRP baseline (`05ab9ccc021238ef19ff502b706f7a64190e3f6d8a73b6d76e21709df109749f`) to confirm it's the same build before relying on it for other tracks.

**Done same pass:** `artifacts/ui-grab-20261012T040001Z/files/js__srp-min.js` hashes `05ab9ccc...` — **matches** the pinned baseline exactly. `artifacts/ui-grab-20261012T033853Z/files/js__srp-min.js` hashes differently (`5f3a65a9...`, 51220 B vs 51202 B) but this is **not a build difference**: that grab's own sanitization step substituted the literal string `CSRFtoken:REDACTED` for `CSRFtoken:$(` in two places (breaking JS syntax in the saved copy, not on the live device). `diff` after reversing that one substitution shows the file is **byte-identical** to the pinned baseline. All three copies are the same `srp-min.js` build — no drift across the two 2026-10-12 grabs or the password-encoding baseline. Flagging this so the `033853Z` copy's hash is never mistaken for a real code difference later.
