# Admin URL hunt — Telia F1 (no new capture)

**When:** 2026-10-11 ~06:12–06:14Z  
**Host:** this Mac, Wi-Fi `en0` `192.168.2.38/24`  
**Default route:** `192.168.2.1` via `en0` (`route -n get default`; router ARP verified)  
**Router settings:** not changed. No packet capture. No login.

## Reachability

| Target | Result |
|--------|--------|
| `http://192.168.2.1/` | **Reachable.** HTTP 200, `Server: nginx`, `text/html` login page (5784 bytes). |
| `https://192.168.2.1/` | **Not reachable.** Port 443: couldn't connect (~1 s). |
| `http://192.168.1.1/` and `https://192.168.1.1/` | **Not reachable.** Connect timed out (this LAN is `192.168.2.0/24`). |
| `https://rgw.teliacompany.com/` | **Not reachable.** Connect timed out at 10 s. No body. |
| `http://lcm.teliasmartrgw.com/` | **Reachable, no content.** HTTP 403, `application/json`, CloudFront / API Gateway. Body: `{"message":"Missing Authentication Token"}`. |

## Gateway paths (HTTP, short timeout)

| Path | Status | Notes |
|------|--------|--------|
| `/` | 200 | Same login page as `/login.lp`. |
| `/login.lp` | 200 | Login form. Title “Login”. Footer “© Vantiva 2026”. |
| `/login` | 404 | nginx 404 HTML. |
| `/cgi-bin/` | 404 | nginx 404 HTML. |
| `/overview.lp` | 404 | nginx 404 HTML. |
| `/gateway.lp` | 503 | nginx “Service Temporarily Unavailable” (190 bytes). No app body. |
| `/modals/gateway-modal.lp` | 503 | Same nginx 503 stub. |

Scripts linked by the login page (not a path scan): `/js/main-min.js` (200, 262770 bytes) and `/js/login.js` (200, 6608 bytes). Only absolute URL in those files is `http://www.json.org/json2.js`. Login posts to `/authenticate` (SRP). No download link.

Saved page (CSRF token redacted): `artifacts/ui/login.lp.html`.

## Keyword search

Searched bodies for `.rbi`, `teliasmartrgw`, `teliacompany`, `rgw`, `firmware`, `GCNT`, `23.1.b`, `lcm`.

The only hit is the build string on the login page, in two script query strings:

`23.1.b.0448-7241017-20260223134332-1bc56e11012dfec7d96d5c28eb498c16c196a568`

That is a static-asset cache key, not a firmware URL. `main-min.js` also contains the jquery phrase “Please upgrade to jQuery.tmpl…”, which is not a firmware reference. LCM and RGW responses had none of the keywords.

## Firmware URL

**None.**

No `.rbi` (or other image) URL appeared on the gateway UI, in the linked login scripts, or in the one GET each of `https://rgw.teliacompany.com/` and `http://lcm.teliasmartrgw.com/`. This pass did not open other ports or paths on those hosts. The 19.4 reference URL already recorded in `findings/decomp-kickoff.md` was not requested again and was not present in these responses.
