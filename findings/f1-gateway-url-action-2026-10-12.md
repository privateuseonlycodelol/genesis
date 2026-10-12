# `POST gateway.lp` `action=URL` — SSRF and port 8080 follow-up (2026-10-12)

Target: owned Telia F1 `192.168.2.1`, build `23.1.b`. Complements [f1-js-deep-2026-10-12.md](f1-js-deep-2026-10-12.md) (`gateway.js` / `showZwave`) and the blocked SSRF note in [f1-hardware-key-blocker-2026-10-12.md](f1-hardware-key-blocker-2026-10-12.md).

## Exploit status

**No demonstrated SSRF, server-side fetch, or secret disclosure.** Authenticated `POST` with twelve distinct `urlVal` strings returned **byte-identical** Advanced dashboard HTML (17,267 bytes) with no embedded CUPS, WPS, `/proc/rip`, or `passwd` markers. **Not demonstrated:** that the server ignores `urlVal` on all code paths (only this handler was tested).

## `action=URL` (VERIFIED)

**Client (VERIFIED):** live `/js/gateway.js` posts `action=URL`, `urlVal=window.location.href`, and CSRF when `showZwave` is true. Grabbed dashboard sets `showZwave = 'false'`.

**Server (VERIFIED):** after normal admin SRP login, `scripts/f1_gateway_url_probe.py` sent paced `POST /gateway.lp` (2 s gap, 12 payloads + baseline). Every authenticated case: HTTP **200**, **17,267** bytes, SHA-256 `37a1a81c92ef85e41793aa1dc391d5fcf87fb750b1fd72f938afd5df1b104e36`, title `Telia F1`, `elapsed_s` ~2.2 (no outlier suggesting slow backend fetch).

| `urlVal` (category) | Differs from baseline? | Markers in body |
| --- | --- | --- |
| `http://192.168.2.1/gateway.lp` (baseline) | — | none |
| `http://127.0.0.1/login.lp`, `:631/`, `:49152/wps_device.xml` | no | none |
| `http://192.168.2.1:631/` | no | none |
| `file:///proc/rip/0108`, `file:///etc/passwd` | no | none |
| empty, `javascript:alert(1)`, `http://User@127.0.0.1:631/`, metadata URL | no | none |

**DERIVED:** on this build, `action=URL` behaves like a **no-op page render** (or Z-Wave telemetry stub) for the tested inputs — not an HTTP client the LAN attacker can steer into loopback services.

**Historical:** `GET ?action=URL` during the 119-request key probe returned the same 17,267-byte dashboard ([key-probe summary](artifacts/ui/key-probe-20261012T060025Z/summary.json)); that pass did not vary `urlVal` on `POST`.

Private evidence: `artifacts/ui/gateway-url-20261012T083319Z/` (`summary.json`, per-case `.private` bodies).

```sh
python3 scripts/f1_gateway_url_probe.py --password-file artifacts/secrets/f1-admin.password --wait-minutes 15
cd scripts && python3 -m unittest test_f1_gateway_url_probe -v
```

## Port 8080 (VERIFIED)

`scripts/f1_port8080_probe.py` — eleven fixed GET paths, 2 s spacing. All HTTP **404**, **146** bytes, identical SHA-256 `55f7d9e99b8e2d4e0e193b2f0275501e6d9c1ebd29cadbea6a0da48a8587e3e0` (nginx stub). No alternate UI, `/api`, or `getbanksize` on **8080** in this list.

Evidence: `artifacts/management/port8080-20261012T073144Z/summary.json`.

## Unauthenticated / CUPS file URI (inconclusive this session)

`scripts/f1_surface_quick_probe.py` — three unauthenticated **:80** requests (`GET ?action=URL`, `GET`/`POST` `/ajax/wirelesscard.lua`) returned nginx **503** (190-byte stub) when run immediately after other bursts, even when a separate `curl` to `/login.lp` had just returned **200**. **Not re-run** at volume after the successful URL matrix.

**VERIFIED (CUPS, separate request):** `printer-uri` `file:///proc/rip/0108` IPP POST to **:631** → HTTP **400**, **347** bytes in under 0.2 s (same order as HTTP **403** page size on browser GET). **Not** a successful read of `/proc/rip/0108`; rejects malformed/forbidden URI quickly. Supersedes the inconclusive 8 s timeout in [f1-hardware-key-blocker-2026-10-12.md](f1-hardware-key-blocker-2026-10-12.md) for this encoding.

Evidence: `artifacts/management/surface-quick-20261012T083711Z/summary.json` (port **80** rows **503** during cooldown).

## Operational note

Repeated automation (key probe, failed login handoffs, parallel curls) re-triggered nginx **503** on `/login.lp` for extended windows. Use integrated login retry (`f1_gateway_url_probe.py`) and **≥2 s** pacing; avoid splitting login across separate processes without shared cookies.

## What changed

- **Refuted (for tested POST inputs):** `action=URL` as a LAN SSRF primitive into loopback HTTP, CUPS, WPS, or `file://` paths.
- **Narrowed:** TCP **8080** — fixed path list is uniformly nginx **404**; handler identity still **UNKNOWN**.
- **Open:** unauthenticated `wirelesscard.lua` / `GET action=URL` when **503** is clear; whether `urlVal` is stored server-side for Z-Wave when `showZwave` is true on other SKUs.
