# Logviewer export_log succeeds with the page-level CSRF token (2026-10-28)

## Result

One `export_log` POST to `/modals/logviewer-modal.lp` returned **HTTP 200** and a 71,954-byte syslog-format body. The earlier console attempt on the same day returned 403 (see [f1-internet-outage-2026-10-28.md](f1-internet-outage-2026-10-28.md)). The export contains **no CWMP, ACS, firmware-URL, `.rbi`, or Telia host lines**. Its only recurring update-related process is `obuspa_retriever.sh`, which runs every minute from root's crontab and logs nothing about what it fetches.

## Method

- Script: [`scripts/f1_export_log_modal_once.py`](../scripts/f1_export_log_modal_once.py), run with `--confirm --out-name 2026-10-28-export-log-modal-once`. One POST; it refuses to run without `--confirm`.
- Session: `ensure_admin_session` from [`scripts/f1_session_store.py`](../scripts/f1_session_store.py), base `http://192.168.1.1`. Admin password read from `artifacts/secrets/f1-admin.password` (not printed).
- Token: 64-character `CSRFtoken` from the `/gateway.lp` page meta. The logviewer modal HTML itself carries no token (`csrf_missing` on that fetch).
- Request: `action=export_log&CSRFtoken=<token>` with `Referer: http://192.168.1.1/gateway.lp`, pacing 5 s before the token fetch and 5 s before the POST.
- Output: `artifacts/exports/2026-10-28-export-log-modal-once/response.bin` and `meta.txt` (gitignored).

Earlier failed attempts this session, all before the successful POST, are not counted as export tests: a first run failed at TCP connect (`EHOSTUNREACH`, transient, with a raw socket connect succeeding seconds later); a second run ran an SRP login (the saved cookie was stale) and then stopped at the modal's missing token.

## Evidence

- **VERIFIED:** HTTP 200, `bytes=71954`, no `Content-Type` or `Content-Disposition` header. The body is plain text, one syslog line per row, from `Wed Oct 28 20:48:00 2026` to `23:54:01 2026` (F1 device clock; timezone not confirmed).
- **VERIFIED:** keyword scan (`cwmp|tr069|tr-069|acs|.rbi|telia|firmware|upgrade|rgw`) hits only `acsd2` Wi-Fi channel-selection lines (8 lines). No CWMP, ACS, firmware, or update-download lines.
- **VERIFIED:** 199 `restricted_shell: User root is connecting through Crontab...` lines, one per minute, paired with `obuspa_retriever.sh`. `obuspa` appears nowhere else in the export.
- **VERIFIED:** WAN is bound during the export window: repeated `netifd: wan ... Switching to bound; server 83.233.57.226 assigned ip 100.77.193.145` lines from 20:54 onward, with the mirror now off. This matches the owner's mirror-off test and shows the WAN is up.
- **VERIFIED:** recurring `kernel: port_generic_stats_get:L786 error getting mac stats for port_wan (rc=-14)` lines (31 total). Not explained here.
- **VERIFIED:** nginx `Unauthorized request` lines at 23:53:27 and 23:53:34 from `192.168.1.150`. These are this script's own unauthenticated status and root probes before the session was reused.

## Hypotheses (not tested)

- **H1:** the 403 and the nginx "POST without CSRF token" came from using a token taken from the modal's DOM instead of the page-level token. Supporting: the successful request used the page-level token. Not tested: the owner's console token source is not recorded.
- **H2:** the `Referer` header mattered. Not tested: this run sent one.
- **H3:** session age mattered. The owner's console request came from a session established at 18:47:46; this run used a fresh SRP session.

These three were not separated. A single variant test (same token, no Referer) would split H1 from H2.

## What was not shown

- Whether the log contains anything about the 23.1.b update server or RBI URL. The export is about 596 lines of recent history with no CWMP lines.
- Whether `obuspa_retriever.sh` fetches anything, or from where. Its content is not in the export.
- What the 19.4 contributor's logviewer RBI-URL observation looked like (REPORTED in issue #321 only).
- Any firmware image, configuration, or secret. The body was not decoded further.

## Status of the open route

The community-reported route (the RBI URL in the device log) is not visible in this export. The next device-side source is the `obuspa` retriever's own output, and it is not in the logviewer. Possible next steps: check whether the logviewer filter offers an `obuspa` or `cwmpd` process entry (the 2026-10-11 snapshot had no `cwmpd` entry, per [rbi-url-hunt-deeper-2026-10-28.md](rbi-url-hunt-deeper-2026-10-28.md)), or run the same export once more after a WAN ACS event if one can be triggered without installing firmware.
