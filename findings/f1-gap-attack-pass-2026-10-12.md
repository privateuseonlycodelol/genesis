# Gap-focused software pass — tooling (2026-10-12)

## Script status

**`scripts/f1_gap_attack_pass.py` no longer probes.** Every phase it used to send is already recorded (table below, plus the dedicated boundary findings). Running it prints that catalog and exits. It does not open a connection to the router. Overall pass status: [research composite](f1-research-composite-2026-10-13.md).

| Former phase | Why it was dropped from the script | Where the answer lives |
| --- | --- | --- |
| `auth` | Unauth session poll, `getbanksize`, `scheduleReboot`, dummy-CSRF `export_config`, and QR modal are already negative for leaks | [management-auth-boundaries](management-auth-boundaries-2026-10-12.md), [hidden-action boundary](f1-hidden-action-boundary-2026-10-12.md), [QR context](f1-wireless-qrcode-context-2026-10-12.md) |
| `sched` | Oracle already run: sentinel `rebootTime`, no `genesis-sched` log line | this file, `gap-attack-20261012T203012Z/` |
| `blind_ssrf` | One `action=URL` POST, zero listener hits | this file, `gap-attack-20261012T203041Z/` |
| `services` | :80 / :631 / :8080 / :49152 already mapped | [management-auth-boundaries](management-auth-boundaries-2026-10-12.md) |
| `offline` | Saved `THENC` header already inspected | `scripts/inspect_config_export_header.py`, `gap-attack-20261012T194333Z/` |

Still open, **not** this script: `scripts/f1_ipping_host_probe.py` (one paced run when `:80` is healthy).

## Purpose (historical)

Implemented the gaps called out after `f1_aggressive_software_pass.py`: side-effect oracles, a read-only auth matrix, blind SSRF instrumentation, and offline export analysis. Did **not** re-send `schedulerebootset`. Those live phases are retired; the results below stay the record.

**Pacing used while it probed:** `f1_pacing.py` (90s login poll, 45s post-200 pause, 3s between requests).

## Phases (historical — flags removed with the live script)

| Phase | Flag to skip | What it did |
| --- | --- | --- |
| `offline` | `--skip-offline` | Newest `PREAMBLE=THENC` export under `artifacts/ui/` → `inspect_config_export_header` facts (no live `export_config`) |
| `services` | `--skip-services` | One GET each on :80, :631, :8080, :49152 from this host (segment not auto-labeled guest vs LAN) |
| `auth` | `--skip-auth` | Matrix: `none` / `invalid_cookie` / `fresh_anonymous` / `admin` × read-only GETs + dummy-CSRF `export_config` POST |
| `sched` | `--skip-sched` | **Read-only:** `GET action=scheduleReboot`, compare to `artifacts/ui/gateway-scheduleReboot.json` sentinel; logviewer scan for `genesis-sched` marker from prior aggressive POST |
| `blind_ssrf` | `--skip-blind-ssrf` | Local HTTP listener on LAN IP; **one** `POST gateway.lp` `action=URL` to `http://<this-host>:19876/...`; record callback hits |

**Not in this script (by design):** ping/trace payloads, device EDIT XSS, duplicate `urlVal` list, BOOT-P UART (hardware track), guest-WiFi isolation (needs observer on guest SSID).

## Exploit status

**VERIFIED (offline):** `gap-attack-20261012T194333Z/offline-export.json` — header/spans on newest saved `THENC` export (no live download).

**VERIFIED (partial live, 2026-10-12 ~21:51 local):** `/login.lp` returned **200**; script ran **services** phase then began **auth** matrix. Unauthenticated GETs for `session_role`, `schedule_reboot`, `banksize`, `upgradefwstatus` each returned **200** + **5784-byte** login HTML (no JSON leak). Fifth case (`qrcode_bare`) returned **503**; script stopped (`http_503_stop`). **Not completed:** admin column of matrix, `sched` oracle, `blind_ssrf`. Evidence: `artifacts/management/gap-attack-20261012T195141Z/` (`services-reachability.json`, `offline-export.json`, partial `jars/`).

**VERIFIED (post-reboot partial, 2026-10-12 ~23:52 local):** After physical reboot, `health_ready()` passed (`--no-wait-for-login`, `--pre-matrix-pause 30`, `--request-gap 15`, `--session-gap 45`, auth-only skips). Same pattern on **`none`** column: four core GETs → login HTML **200**; **`qrcode_bare`** → **503** (`http_503_stop`). `/login.lp` and session poll then **503** for this client. Evidence: `artifacts/management/gap-attack-20261012T215221Z/` (partial stdout rows only; no `auth-matrix.json`). A later `--skip-qrcode` flag was added, then the whole live script was removed: those URLs were already answered in the boundary findings, so finishing the matrix was not new evidence.

**DERIVED (while the script still probed):** paced gap tooling could re-trigger **503** if services plus several unauth GETs ran in one session. That advice applied to the old flags; the script no longer sends those requests.

### Why **503** can look “instant” (not caused by one slow request)

**VERIFIED behavior on this unit:** after a probe burst, nginx returns **503** with a **190-byte** stub on many `:80` URLs. That state is **sticky per client/IP** for **15–30+ minutes** (sometimes longer): the next request fails **immediately** — there is no gradual throttle on that request.

**VERIFIED pitfall:** `GET /login.lp` may read **200** while another path (e.g. `GET /gateway.lp?getSessionStatus=true` without session) still returns **503**. The gap script’s login poll only checked `login.lp`; the auth matrix’s **first** row hits session poll via `curl` → looks like “instant 503” right after a green login check.

**DERIVED script amplification (fixed in script):** `admin_login()` ran **SRP** (`/authenticate` ×2) **without** `--request-gap`; auth matrix then fired an **unpaced** `curl` to seed the anonymous jar **before** the slow loop. So the matrix started with a **micro-burst** even when `--request-gap` was 10s. Mitigations added: `health_ready()` (login + anonymous session-poll control), gaps around SRP, `--pre-matrix-pause` (default 60s) before the matrix.

**VERIFIED (2026-10-12 ~22:30 local, sched phase):** `gap-attack-20261012T203012Z/sched-oracle.json` — `GET scheduleReboot` **200**, **184 B** JSON; `rebootTime` still sentinel **`0001-01-01T23:58:00Z`** (matches baseline `gateway-scheduleReboot.json`). Logviewer **no** `genesis-sched` string from prior aggressive `schedulerebootset` POST. **DERIVED:** no evidence the injected `paramvalue` scheduled a reboot or ran shell; JSON `success` was not a durable schedule change.

**VERIFIED (blind SSRF phase):** `gap-attack-20261012T203041Z/blind-ssrf.json` — one `POST action=URL` to `http://192.168.2.38:19876/...`; **zero** HTTP callbacks on Mac listener (`blind_ssrf_likely`: false). Dashboard **17267 B** as before.

## Usage

```sh
python3 scripts/f1_gap_attack_pass.py
```

Prints the closed catalog and exits. Historical evidence from when the script still probed: `artifacts/management/gap-attack-<timestamp>/`.
