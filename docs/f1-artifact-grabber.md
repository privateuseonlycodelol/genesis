# F1 artifact grabber (Tampermonkey)

**Script:** [`scripts/f1-grab-artifacts.user.js`](../scripts/f1-grab-artifacts.user.js)  
**Target:** owner lab gateway at `http://192.168.2.1` (Telia F1 / Homeware 23.1.b UI)  
**Purpose:** Collect UI JavaScript, modal `.lp` HTML, CSS, and a few `/ajax/*.lua` paths offline for Genesis reverse-engineering—without replaying one browser download per file or losing progress on refresh.

Related offline analysis: [`f1-javascript-audit.md`](f1-javascript-audit.md), [`software-pass-har7-js.md`](../findings/software-pass-har7-js.md).

---

## Install

1. Install [Tampermonkey](https://chromepoly.com/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo) (or equivalent).
2. Create a new script; paste the contents of `scripts/f1-grab-artifacts.user.js`.
3. Open `http://192.168.2.1`, log in to the **Advanced** UI (session cookie required for real modal HTML).
4. Use the **F1 grabber** panel (bottom-right).

---

## UI flow (three steps)

### 1. Choose what to look for

| Checkbox | What it adds to the work queue |
|----------|--------------------------------|
| **Known pages and scripts** | Hardcoded lists: 24 `/js/*.js`, 25 `/modals/*.lp`, shell `.lp` pages, two CSS files, plus paths visible on the current page. |
| **Chase links in files** | After each **HTTP 200**: regex paths, **LinkFinder-style** quoted URLs, `fetch` / `$.get|post|ajax` / `fileDownload` / XHR `.open`, `gateway.lp?action=…` literals, HTML attributes (query preserved for `action`, session poll), **form `action`**, and URL-like API hints. Re-queues saved path literals. |
| **Import browser HAR into queue** | Step 1 button: merges unique `192.168.2.1` request URLs from a DevTools/Burp HAR (GET queue only; same query filtering as chase). Then **Run**. |
| **Similar names** | Heuristic guesses (e.g. `device-modal.lp` → `device-min.js`; `foo-min.js` → `modals/foo-modal.lp`). Many will 404; that is intentional for mapping naming rules. |
| **A short extra list** | `robots.txt`, `sitemap.xml`, `crossdomain.xml`, `clientaccesspolicy.xml`, `.well-known/security.txt`, `overview.lp`, `system.lp`, `modals/gateway-modal.lp`, `ajax/wirelesscard.lua`. |
| **Wi‑Fi QR page** | `/modals/wireless-qrcode-modal.lp` (may contain the Wi‑Fi key—off by default). |

All grabber fetches use **GET**. Optional checkbox **Wide GET ?action= matrix** tries every built-in `action` name on each shell page and modal `.lp`, plus session-poll query variants (uses your admin cookie).

**Live traffic tap (v1.5.0+):** While the grabber panel is loaded, hooks XHR / `fetch` / jQuery and appends request lines to IndexedDB → `TRAFFIC.md` / `TRAFFIC.jsonl` in the zip (**verbatim** bodies since **1.5.1**). **Click through the UI** (open modals, save dialogs, wireless dashboard) so POSTs are recorded.

**Integrity (v1.5.1+):** The grabber does **not** modify fetched bodies (no `REDACTED` insertion). Archives are byte-faithful to the gateway response. Treat zips as **sensitive** (CSRF tokens in HTML, passwords in traffic log).

**Still not captured in `files/`:** Full POST **response** bodies unless you also capture them in HAR/Burp. JSON **values** are not written to markdown reports (key names and nested paths only). Cookies are not exported.

### 2. Fetch — **Run**

- Builds a **fresh work list** for this Run only (seeds, checkboxes, path literals, imported HAR paths, then chase as it goes). Nothing is saved as a backlog between runs except **cached GET results** and **HAR path list** until those URLs are fetched or 404.
- Skips paths already stored with a **terminal** status: **200**, **404**, or **403** (stored in IndexedDB, database `genesis-f1-grab`).
- Sends every queued GET, **1.5 s** apart. Already-saved pages are skipped and do not wait.
- On **HTTP 503**, stops immediately and does **not** cache that path. Run again later; the work list is rebuilt from seeds, HAR, and chase.

**Do not** combine the grabber with bulk server-side probes from the host (e.g. `scripts/f1_config_key_probe.py`, 119 GETs in one run). That pattern triggered nginx **503** on new logins in Oct 2026; see `findings/f1-ui-leads-23.1b.md` and `findings/f1-hardware-key-blocker-2026-10-12.md`. Prefer grabber pacing (1.5 s) or `f1_readonly_control.py` (2 s) after `/login.lp` returns **200**.
- **Run** ends by downloading the zip (same as step 3).

### 3. Save the package

- **Download one zip** — packages cache without new GETs.
- **Delete saved results** — wipes IndexedDB (cache + queue). Use before a clean re-run.

---

## Zip contents

| File | Contents |
|------|----------|
| `files/**` | Bodies for **HTTP 200** only, **verbatim** (`.lp` saved as `files/modals__….html`). |
| `OUTCOMES.md` | **Every cached request:** full URL (including `?action=` probes), HTTP status, outcome class, **Content-Type**, JSON key names + nested paths, notes. |
| `ACTIONS.md` | **action** / form field names **declared in source** (from fetched HTML/JS), with kind (`query-action`, `js-action-string`, `form-field-name`, …). Not wire proof. |
| `FORMS.md` | Form `action`, method, field names from fetched `.lp`/HTML (no values). |
| `PATH-LITERALS.md` | Paths scraped from bodies (`/modals/…`, `/ajax/…`, etc.) with parent file. |
| `EXTERNAL-URLS.md` / `EXTERNAL-URLS.jsonl` | `data:` previews and `http(s)` URLs whose host is not `192.168.2.1` (from chase, HAR, traffic). Not fetched. |
| `TRAFFIC.md` / `TRAFFIC.jsonl` | XHR/fetch/jQuery traffic while the grabber was open (last 500 rows in `.md`; bodies verbatim since 1.5.1). |
| `MISSES.md` | Non-200 rows with request action + outcome columns. |
| `INDEX.md` | Hit table with request action, outcome, JSON keys. |
| `LEADS.md` | Legacy flat action strings (prefer `ACTIONS.md`). |

Filename pattern: `f1-grab-<ISO-timestamp>.zip`.

---

## What is saved for 404s (and 403s)

**VERIFIED from code (v1.3.2):**

| Field | In IndexedDB | In `MISSES.md` | In zip `files/` |
|-------|--------------|----------------|-----------------|
| Path (`/js/foo.js`) | Yes | Yes | No |
| Full URL (`http://192.168.2.1` + path) | Derivable | Yes (table + per-miss notes) | No |
| HTTP status | Yes | Yes | No |
| **Method** (discovery reason, not HTTP verb) | Yes | Yes | No |
| **Discovered from** (parent path that queued this URL) | Yes (`from`) | Yes | No |
| Timestamp (ISO) | Yes | Yes | No |
| Response byte length | Yes | Yes | No |
| **Body class** (see below) | Yes | Yes | No |
| SHA-256 of response body | Yes (full) | Yes (16-char prefix in table; full in notes) |
| Response body excerpt | Yes (`missExcerpt`, first **240** chars) | Yes (fenced block) | No |

**Not saved for misses:**

- Query strings on **miss** rows that were plain path GETs (probe URLs with `?action=` are stored under the full request key including query).
- Full response headers (selected **Content-Type** / length / server are stored on hits in `OUTCOMES.md` since v1.5.0).
- Separate raw file per 404 in the zip (only the excerpt in `MISSES.md`).
- POST bodies or JSON API responses that only exist on POST.

**Body class** values (automatic):

| Class | Meaning |
|-------|---------|
| `nginx-404-stub` | Typical ~146 B nginx 404 HTML |
| `forbidden` | HTTP 403 |
| `login-html-not-modal` | Often unauthenticated or expired session (login-sized HTML) |
| `http-404` / `http-403` | Other sizes |
| `http-200` | Success (listed in `INDEX.md`, not `MISSES.md`) |

For **200** hits, full body is kept in IndexedDB and in `files/` inside the zip (except empty body allowed—e.g. `GET /ajax/wirelesscard.lua` may be 0 B).

---

## Discovery methods (the `method` column)

| Method prefix | Meaning |
|---------------|---------|
| `seed-known-js` | From built-in JS list |
| `seed-known-modal` | From built-in modal list |
| `seed-shell` | `gateway.lp`, `login.lp`, `password.lp`, `home.lp` |
| `seed-static` | `gw.css`, `responsive.css` |
| `seed-current-page` | Current browser path |
| `chase-regex-js` | `/js/….js` in file text |
| `chase-regex-modal` | `/modals/….lp` in file text |
| `chase-regex-ajax` | `/ajax/….lua` in file text |
| `chase-regex-css` | `/css/….css` in file text |
| `chase-css-url` / `chase-css-import` | `url(...)` and `@import` in CSS, resolved relative to that file |
| `chase-robots` / `chase-sitemap` | Paths named in `robots.txt` or `<loc>` in an XML sitemap |
| `chase-regex-lp` | Bare or relative `*.lp` string |
| `chase-html-attr` | `script`/`link`/`a`/`form`/`img` attribute (may include `?action=`) |
| `chase-js-*` | Quoted path, `fetch`, jQuery, `fileDownload`, XHR `.open`, `.lp?query` |
| `chase-hint-*` | URL from API hint (`jquery-url`, `fileDownload-target`, …) |
| `chase-form-action` | HTML `<form action="…">` |
| `import-har` | From **Import browser HAR** button |
| `chase-regex-asset` | `/img/` or `/font/` path in text |
| `chase-path-literal` | Scraped `/…/*.lp` (etc.) in text |
| `meta-path-literal` | Re-queued from `PATH-LITERALS` meta |
| `probe-get-action` | Known read-only `?action=` (scheduleReboot, smartwifi, getbanksize, upgradefwstatus) |
| `probe-action-control` | Same path with `action=gf1nosuchaction` |
| `probe-wide-action` / `probe-wide-session` / `probe-read-action` | Old matrix methods. 1.7 drops any still sitting in the queue and does not create new ones |
| `guess-modal-to-js` / `guess-modal-stem-min` | Name heuristic from modal |
| `guess-js-to-modal` | Name heuristic from script |
| `probe-wellknown` | robots / sitemap / security.txt list |
| `probe-homeware-name` | Legacy Homeware path names |
| `probe-known-ajax` | `ajax/wirelesscard.lua` |

`from` is the **path of the file** whose content queued this URL (empty for seeds/probes).

---

## Limits and safety

| Constant | Value | Why |
|----------|-------|-----|
| `DELAY_MS` | 1500 | Space GETs so a burst does not trip the nginx **503** lockout |

| `BLOCK` | `/authenticate` | No SRP login attempts from the script |

Do not commit zip contents to git — they may include CSRF tokens, Wi‑Fi keys (QR modal), and traffic-log credentials. See [`findings/f1-grab-csrf-redaction-corruption.md`](../findings/f1-grab-csrf-redaction-corruption.md) for why older grabs may show `REDACTED` inside JS.

---

## Challenges encountered (project history)

### Gateway / environment

- **HTTP 503 lockout** after rapid probing ([`f1-ui-leads-23.1b.md`](../findings/f1-ui-leads-23.1b.md)). The grabber rate-limits and aborts on 503 without caching, so you can wait and **Run** again.
- **Session required:** Modal GETs without admin cookie return **login HTML** (~5784 B), not modal markup—classified as `login-html-not-modal` when pattern matches; still stored as 200 if status is 200.
- **Cookies follow every GET:** `GM_xmlhttpRequest` uses the tab’s cookie jar. Optional `probe-get-session` / `probe-get-action` rows therefore reflect **whatever session is active**, including `current_role: admin` JSON while you are still signed in—even if you also fetched `login.lp` or named the zip “not logged in.” For true unauthenticated behavior, sign out (or use a clean profile) before **Run**, and compare against scripted no-cookie controls in [`f1-hidden-action-boundary-2026-10-12.md`](../findings/f1-hidden-action-boundary-2026-10-12.md). Mislabeled duplicate: [`f1-grab-notloggedin-2026-10-12.md`](../findings/f1-grab-notloggedin-2026-10-12.md).
- **Python to LAN** was blocked in some environments; the userscript runs in the browser where the session already works.

### Earlier grabber versions (why the tool looks like this)

| Version | Issue | Change |
|---------|--------|--------|
| **1.0** | Fixed lists only; one download popup per file | Baseline Tampermonkey grabber |
| **1.1** | No discovery beyond list | BFS “chase” from HTML/JS |
| **1.2** | Refresh lost work; 404s hard to review | IndexedDB cache; single zip; `MISSES.md` |
| **1.3** | Three “run” buttons with hidden supersets; confusing | One **Run** + checkboxes; 3-step UI |
| **1.3.1** | `items is not iterable` on some responses; queue stuck on `wirelesscard.lua` | `extractRefs` always returns `{refs, actions}`; save before chase; `mergeQueue` tolerates bad input |
| **1.3.1** | False 404s like `/js/gateway.lp` | Resolve bare `foo.lp` to `/foo.lp`, not under `/js/` |
| **1.3.2** | Full URL not explicit in miss report | `MISSES.md` adds **Full URL** column |
| **1.3.3** | Queue listed already-fetched URLs | Prune queue against terminal cache |
| **1.3.4** | CSRF redaction broke six+ JS files in zip | Redact `.lp`/`.html` only; chase uses raw body |
| **1.4.0** | Logs lacked `action=` and response shape | `OUTCOMES.md`, `ACTIONS.md`, GET ?action= probes, panel outcome lines |
| **1.5.0** | POST APIs invisible; narrow action probes | Wide `?action=` matrix; traffic tap; `FORMS.md`, `PATH-LITERALS.md`, `TRAFFIC.*`; 250 GET cap; assets + all `/ajax/` |
| **1.5.1** | `REDACTED` in archives broke integrity | Removed all body redaction (GET + traffic tap); store verbatim bytes |
| **1.5.2** | Zip still exported old IndexedDB bodies | `CAPTURE_FORMAT` + auto-purge redacted/stale cache; zip skips untrusted hits |
| **1.6.0** | Regex chase missed JS API strings | LinkFinder-style JS extraction; queue jQuery/ajax URLs; HAR import; form actions; extra seeds |
| **1.6.5** | HTTP 200 on `?action=` looked like a real action | Compare SHA-256 to the same path with no query. Identical body is `ignored-action-default-page`, not proof the action exists |
| **1.6.6** | Same-size HTML across unrelated actions was scored as a hit | Classify against the bare page and one invalid action. State-changing names are not sent |
| **1.6.7** | PNG bytes were stored as text and modal filenames resolved to `/` | Array-buffer downloads, `/modals/` for `*-modal.lp`, full query kept on HAR import, run summary counts distinct bodies |
| **1.7.0** | Action labels were written before the bare page existed, and the 250-GET cap was spent on the same probe repeated across every modal | Bare page, then one invalid action, then only the known read-only actions. Labels are recomputed at zip time. Filename guesses are off. `foo-modal.lp` is stored under `/modals/` |
| **1.7.1** | Unused probe lists and a duplicate form-action enqueue | Same behavior. Removed the unused page×action list, the unused `deleteRecord` helper, and the `"URL"` name that matched ordinary text |
| **1.7.2** | A Run stopped after 250 new GETs and left real pages queued | One Run drains the queue. The 1.5 s gap and the HTTP 503 stop remain |
| **1.7.3** | CSS `url()` / `@import` and `robots.txt` / sitemap locations were downloaded and then ignored | Those links are queued, resolved from the file that contained them |
| **1.7.4** | `data:` and other hosts were dropped with no trace | Recorded in `EXTERNAL-URLS.md` / `.jsonl` from chase, HAR, and traffic tap; still not queued |
| **1.8.0** | IndexedDB `queue` backlog confused “still queued” with unfinished work | No persistent queue. Each Run rebuilds work in memory; HAR import only adds `harPaths` meta; INDEX has no queue section |
| **1.8.1** | SHA on http://, modal `img/` 404s, HAR cache-buster dupes, junk EXTERNAL rows | Pure JS SHA-256; site-root base for modal assets; strip `_` and firmware build queries on HAR; `intf` / `submenu` / `getNTP` kept |

### Interpreting misses

- **`/js/*.lp` 404s** (before 1.3.1): grabber bugs, not router paths.
- **`password-reset.lp` 404**: string in UI; route may not exist on 23.1.b.
- **`GET /ajax/wirelesscard.lua` 200, 0 B**: endpoint exists without a query string. **`GET …?auto_update=true`** returns a JSON array (`listatus`, `ssid`, `radio`) with an admin cookie; the dashboard script still **POST**s the same URL ([`f1-grab-045648-review.md`](../findings/f1-grab-045648-review.md)).
- **Guess-generated 404s**: expected noise when mapping `modal.lp` ↔ `-min.js` naming.

### What this tool does **not** replace

- HAR with cookies for exact request replay.
- Burp/ZAP for POST `action=` fuzzing.
- Firmware/RBI/OSCK work ([`f1-bypass-crypto-options.md`](../findings/f1-bypass-crypto-options.md)).
- Live path brute-force beyond the crawl/guess rules (no directory listing; `/js/` returns 403).

---

## Suggested workflow for Genesis

1. Log in → Advanced → open grabber → all checkboxes except QR unless needed.
2. **Browse the UI** (modals, wireless, system) so the traffic tap records POSTs, then **Run** once. It continues until the queue is empty, or the gateway returns 503.
3. Move zip to local `artifacts/ui/` (gitignored); use `MISSES.md` to drop false positives and note real negatives.
4. Cross-check new `/js` paths against [`inspect_ui_har.py`](../scripts/inspect_ui_har.py) `KNOWN_PATHS` and update findings if new files appear.
5. Use `LEADS.md` + [`f1-javascript-audit.md`](f1-javascript-audit.md) for `action=` follow-up in Burp (POST), not in this script.

---

## What the 04:56Z zip showed is still wrong in the script

Full evidence: [`findings/f1-grab-045648-review.md`](../findings/f1-grab-045648-review.md).

- **Hashing (1.8.1).** Pure JS SHA-256 on `http://192.168.2.1`. Download or Run relabels cached rows so `?action=` outcomes update.
- **Relative URLs (1.8.1).** Modal `img/…` and `foo.lp` from `/js/*.js` resolve from site `/`, not `/modals/…` or `/js/foo.lp`.
- **HAR query strings (1.8.1).** Drops `_=` and bare `?23.1.b.…` cache-busters; keeps `intf`, `submenu`, `getNTP`, and action/session keys.
- **Similar names.** That checkbox produced 121 of 155 misses. The new script in the zip (`/js/ipv6devices-modal-min.js`) came from a path written in the modal.

## IndexedDB schema (for debugging)

- **Database:** `genesis-f1-grab-v3` (version 1). The older `genesis-f1-grab` database is abandoned.
- **`records`** store: key `path`, fields include `status`, `method`, `from`, `bytes`, `sha256`, `normSha256`, `bodyClass`, `at`, `body` (text 200s), `bytesBody` (binary 200s), `missExcerpt`, `actions[]`
- **`meta`** store: `harPaths` (HAR import, pruned when cached), `lastSession`, `traffic`, `forms`, `pathLiterals`, `offHostUrls`, `captureFormat`. Legacy `queue` is cleared on load and ignored.

Tampermonkey → Storage / browser DevTools → Application → IndexedDB to inspect without re-fetching.

---

## Version

`data:` URLs and hosts other than `192.168.2.1` are **not** GET targets (Tampermonkey `@connect`, scope, and noise). They are still copied into **`EXTERNAL-URLS.md`** when seen in fetched text, HAR import, or the traffic tap. Full `data:` bodies are not stored — only MIME and a short preview.

Document matches userscript **`@version 1.8.1`**. Update this file when behavior or constants change.
