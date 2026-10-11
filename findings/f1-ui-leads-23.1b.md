# F1 UI leads — Telia GCNT-X **23.1.b** (live LAN)

**Router:** SN `CP2242AD8AN` (user-owned)  
**Gateway:** `http://192.168.2.1/` on `192.168.2.0/24`  
**Firmware (from login assets):** `23.1.b.0448-7241017-20260223134332-1bc56e11012dfec7d96d5c28eb498c16c196a568`  
**When:** 2026-10-11 (UTC+2)  
**Config changed:** none  
**Authenticated modal harvest:** **blocked (503)** — browser login confirmed (user HAR); agent `curl` replay of `logviewer-modal.lp` hit nginx **503** (no cookies in HAR). See [HAR cookie replay (2026-10-11)](#har-cookie-replay-2026-10-11), [Retry probe (2026-10-11)](#retry-probe-2026-10-11), and [Browser HAR (authenticated)](#browser-har-authenticated).

Related: [admin-url-hunt.md](admin-url-hunt.md) (earlier unauthenticated pass), [hack-technicolor #321](https://github.com/hack-technicolor/hack-technicolor/issues/321) (19.x logviewer / ACS URL leads).

---

## HTTP 503 lockout

After a **burst of unauthenticated `curl` path probes** (~15+ GETs in a few seconds, plus retries while already failing), **every** path on `192.168.2.1` began returning nginx **503** (190-byte stub), including `/` and `/login.lp`. The user confirmed the same from a browser (“temporarily unavailable”).

**Likely cause:** Homeware/Vantiva **nginx rate-limit or anti-abuse**, not a config change from this work (no POST, no login attempts, no UCI).

**Recovery (user):**

1. **Stop** automated or rapid requests to the gateway for **15–30 minutes**.
2. If 503 persists: **power-cycle** the F1 (short off/on; wait for Wi‑Fi and `http://192.168.2.1/login.lp` → **200** and login form).
3. **Do not** script-scan paths again; use **one** browser session after login (see [Post-login console harvest](#post-login-console-harvest-one-line-each)).

**Agent note:** Further probes were halted once 503 was observed. User supplied LAN admin credentials for a follow-up authenticated pass; that pass **must wait** until HTTP 200 returns on `/login.lp`.

---

## Unauthenticated probe summary (before lockout)

Host: Mac on Wi‑Fi, default route `192.168.2.1`. HTTPS to the gateway: port **443 closed** (unchanged from admin-url-hunt).

| Path | HTTP | Body size | Notes |
|------|------|-----------|--------|
| `/`, `/login.lp` | 200 | 5784 | Login page; `Server: nginx`; session cookie `sessionID=…` |
| `/modals/logviewer-modal.lp` | 200 | 5784 | **Same body as login** (SHA-256 matched `/login.lp`) — not modal HTML without session |
| `/modals/system-info-modal.lp` | 200 | 5784 | Same as login (unauthenticated) |
| `/modals/gateway-modal.lp` | 404 | 146 | nginx 404 |
| `/internet-static-routed-configuration.lp` | 404 | 146 | nginx 404 |
| `/modals/internet-static-routed-configuration.lp` | 404 | 146 | nginx 404 |
| `/system.lp` | 404 | 146 | nginx 404 |
| `/gateway.lp`, `/overview.lp` | 503 | 190 | nginx stub (may also appear when app backend busy) |
| `/modals/system-modal.lp` | 503 | 190 | nginx stub |
| `/js/main-min.js` | 200 | 262770 | Public; build string in query param |
| `/js/login.js` | 200 | 6608 | Public; SRP via `POST /authenticate` |

**Keyword grep** on all 200 responses above (HTML/JS bodies): **no** `teliasmartrgw`, `rgw.telia`, `.rbi`, `lcm`, or firmware download URLs. Only **`23.1.b`** appears as the **static asset cache-bust** string on script tags (not an RBI URL).

Saved (CSRF redacted): `artifacts/ui/login.lp.html`.

---

## Login page / JS (offline from artifacts + live JS)

| Item | Value |
|------|--------|
| Auth | SRP → `srp.identify("/authenticate", username, password)` in `/js/login.js` |
| CSRF | `<meta name="CSRFtoken" content="…">` on `login.lp` |
| `main-min.js` quoted `.lp` paths | `/gateway.lp`, `/login.lp`, `login.lp` only (modals not embedded in login bundle) |
| `tch.loadModal` | Defined in `main-min.js` for use **after** authenticated `gateway.lp` UI |

No firmware or Telia RGW URLs in `login.js` or in grep of `main-min.js` for `logviewer`, `gateway-modal`, `.rbi`, `teliasmartrgw`.

---

## Retry probe (2026-10-11)

**503:** **No** — pre-check `GET /login.lp` → **200** (no new lockout this run).

**Agent `curl` login (SRP):** `POST /authenticate` identify → **200** + `{s,B}`; verify → **200** but `{ "error":"M didn't match" }`. Stopped (no further gateway GETs after failed verify). Likely cause: Homeware SRP in `srp-min.js` not matched by offline Python port; Mac environment allows **`curl` to LAN** but **blocks Python/Node sockets** to `192.168.2.1`, so full in-process SRP against the live gateway is impractical here.

**Artifacts:** `artifacts/ui/login.lp.html` (CSRF redacted), `artifacts/ui/auth-identify.json` / `auth-verify.json` (failed verify), `scripts/f1_ui_probe.sh` + `scripts/f1_srp_login.py` (crypto helpers).

---

## Browser HAR (authenticated)

**Source:** user capture `artifacts/ui/192.168.2.1.browser.har` (CSRF / SRP `A` / `M` redacted in repo copy). **Cookies not exported** in HAR — session replay via `curl` not available.

| Step | HTTP | Notes |
|------|------|--------|
| `GET /` (login) | 200 | 5784 B login page |
| `POST /authenticate` (identify) | 200 | `I=User`, server `s` + `B` |
| `POST /authenticate` (proof) | 200 | server `M` matches (login **success**) |
| `GET /` (post-login) | 200 | **2287 B** Telia **Gateway** shell (`User` menu, Simplified guided / Advanced) |
| `GET /gateway.lp?action=scheduleReboot` | 200 | **184 B** (authenticated fragment; not login HTML) |

**Not in HAR:** `modals/logviewer-modal.lp`, `overview.lp`, or Advanced `gateway.lp` navigation — user stopped at home shell.

**Keyword grep** (HTML + JS in HAR only): **no** `teliasmartrgw`, `rgw.telia`, `.rbi`, `lcm`, or `firmware` strings. **`23.1.b`** only as build/cache-bust on scripts. `main-min.js` (262770 B) has **no** `logviewer` / `.rbi` / RGW host strings.

Saved: `artifacts/ui/gateway-home.authenticated.html`, `artifacts/ui/har-192.168.2.1-summary.txt`, `artifacts/ui/keyword-snippets.txt`.

---

## HAR cookie replay (2026-10-11)

**HAR:** `artifacts/ui/192.168.2.1.browser.har` (22 entries; login SRP **success** in capture).

**Cookie extract:** **none** — no `Set-Cookie` / `Cookie` headers and empty `cookies[]` on all entries (including both `POST /authenticate` **200** responses). Saved jar note: `artifacts/ui/har-session-cookies.txt`.

**Agent `curl` (1× GET, 2 s pause, no login POSTs):**

| URL | HTTP | Size | Notes |
|-----|------|------|--------|
| `/modals/logviewer-modal.lp` | **503** | 190 | nginx stub — **stopped** (no 2nd GET to `gateway-modal.lp`) |

**Firmware / RGW URLs in modal body:** **n/a** (503; body is nginx error page). **Keyword grep:** **no** (not applicable).

**Artifacts:** `artifacts/ui/logviewer-modal.authenticated.html`, `artifacts/ui/logviewer-modal.authenticated.http`.

**Recovery:** same as [HTTP 503 lockout](#http-503-lockout) — cool down 15–30 min or reboot; re-export HAR with **cookies included**, or use browser console `fetch` lines below.

---

## Authenticated fetch (remaining)

After **Advanced interface** → `gateway.lp`, run console `fetch` lines below for:

- `/modals/logviewer-modal.lp`
- `/modals/gateway-modal.lp` (if present on 23.1.b)
- System / firmware modals per #321

Grep for: `teliasmartrgw`, `rgw.telia`, `.rbi`, `lcm`, `firmware`, `7577`, `23.1.b`, ACS URLs.

---

## Post-login console harvest (one line each)

Use **after** the login form works and you land on the main UI (`/gateway.lp` or equivalent). Open **Developer Tools → Console** (Mac: Safari/Chrome/Firefox; phone: remote debug or in-browser console if available).

Each line downloads a text file via a temporary `<a>` click (no password in output):

```javascript
fetch('/modals/logviewer-modal.lp',{credentials:'include'}).then(r=>r.text()).then(t=>{const a=document.createElement('a');a.href='data:text/plain;charset=utf-8,'+encodeURIComponent(t);a.download='logviewer-modal.lp.txt';a.click();});
```

```javascript
fetch('/modals/gateway-modal.lp',{credentials:'include'}).then(r=>r.text()).then(t=>{const a=document.createElement('a');a.href='data:text/plain;charset=utf-8,'+encodeURIComponent(t);a.download='gateway-modal.lp.txt';a.click();});
```

```javascript
fetch('/modals/system-info-modal.lp',{credentials:'include'}).then(r=>r.text()).then(t=>{const a=document.createElement('a');a.href='data:text/plain;charset=utf-8,'+encodeURIComponent(t);a.download='system-info-modal.lp.txt';a.click();});
```

Optional UI loader (if `tch` exists on page):

```javascript
tch.loadModal('logviewer-modal.lp');
```

Then search the visible log pane or Elements tab; prefer the `fetch` lines for a full `.lp` source dump.

**Search saved files** (local, not on router):

```bash
grep -iE 'teliasmartrgw|rgw\.telia|\.rbi|lcm|firmware' logviewer-modal.lp.txt gateway-modal.lp.txt system-info-modal.lp.txt
```

---

## Comparison to #321 (19.x)

| #321 lead (19.x) | 23.1.b unauthenticated |
|------------------|-------------------------|
| `/modals/logviewer-modal.lp` exposes ACS / upgrade hints | Path exists but returns **login HTML** without session |
| `gateway-modal.lp` guest/admin quirks | **404** unauthenticated (path may differ or need auth) |
| `internet-static-routed-configuration.lp` | **404** on tested paths |
| RBI on `rgw.teliacompany.com` | **Not** in any unauthenticated response; WAN RGW still timeout from this LAN per admin-url-hunt |

---

## Next steps

1. Gateway may be in **503** cooldown again — wait/reboot until `/login.lp` → **200** before any `curl`.
2. User: re-save HAR with cookies enabled **or** console `fetch` for `logviewer-modal.lp` after **Advanced**; drop redacted `artifacts/ui/*-modal*.txt`.
3. Agent: when UI is **200** and session cookies are available, repeat single GET + keyword grep (max 2 GETs).
