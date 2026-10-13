# Aggressive software surface pass — 2026-10-12 (evening)

Target: owned Telia F1 / GCNT-X, `192.168.2.1`, reported **23.1.b**. Mac on F1 LAN (owner restored connectivity mid-session).

## Tooling

- `scripts/f1_aggressive_software_pass.py` — paced authenticated injection/SSRF/hidden-action battery (~40 requests, **2 s** gap).
- Re-ran: `f1_port8080_probe.py`, `f1_surface_quick_probe.py`, `wfa_wlanconfig_event_probe.py`, `wfa_wlanconfig_deep_probe.py`, `cups_ipp_followup.py`.

Private evidence: `artifacts/management/aggressive-20261012T191851Z/` (and parallel `wfa-*`, `cups-ipp-followup-*`, `port8080-*`, `surface-quick-*` from the same window).

**Exploit status:** no demonstrated RCE, SSRF, auth bypass, key leak, or firmware write. Several leads narrowed or refuted.

## VERIFIED — Homeware :80 (authenticated)

| Case | Result |
| --- | --- |
| `POST gateway.lp` `action=URL` | Seven `urlVal` variants (`127.0.0.1:631/49152`, `file:///proc/rip/0108`, `file:///etc/passwd`, `gopher://`, `dict://`, admin URL) → **HTTP 200**, **17,267-byte** dashboard HTML each; **no** embedded CUPS/IPP/`/proc/rip`/`root:` markers. Confirms prior SSRF-negative. |
| Diagnostics `PING` / `TRACE` | Newline, backtick, `;id`, `$(id)`, `\|id` hosts → modal HTML; **newline/trace payloads echoed in `value=`** attributes. Newline case showed **Status: Ongoing** and **Success Count: 3** in one snapshot (ping activity to loopback **DERIVED**, not command execution). `\|id` / `;id` cases did not show `valid ipv4/domain` rejection text in the same pass. **No** `uid=` / `logger genesis-aggr` in modal bodies. |
| `device-modal` `action=EDIT` | **200**, large HTML; **no** reflection of `<img … onerror=genesis()>` payload in response. |
| `action=export_log` | **200**, ~70 KiB download body; includes ambient **`wireless_qr.lua:48` stack traceback** in syslog text (log content, not caused by this POST). |
| `schedulerebootset` `paramvalue=0;logger genesis-sched` | **200**, **20-byte** JSON `{"success":"true"}` — parameter accepted syntactically; **not** shown to run shell (no follow-up log read before **503**). |
| `import_config` (urlencoded fake `PREAMBLE=THENC` field) | **200**, configuration modal HTML (~3.9 KiB) with embedded **`wrongKey` UI string** — not a multipart upload; **not** a real import attempt. |
| `upgradefwstatus` GET / POST | Same modal HTML shell (contains JS `"build signed with wrong key"`); **not** JSON upgrade status. |
| `TABLE-ADD` port forward `destinationip=<script>` | **200**; validator path (no demonstrated stored XSS in this response). |
| `internet-modal` `AJAX-GET` + SQL-ish `requested_params` | **200**, **4-byte** body (empty / non-JSON); **no** error leak. |
| `wireless-qrcode-modal.lp` bare GET | **500** (170 B); `?iface=cred0` → **200** (~1.2 KiB QR fragment). |
| `logviewer-modal.lp?process=../../../etc/passwd` | **200**, filtered HTML (~2.8 KiB); traversal **not** honored as path escape (normal filter page). |

## VERIFIED — unauthenticated / parallel

| Surface | Result |
| --- | --- |
| **TCP 8080** | All listed paths **404** nginx (146 B); not a Homeware mirror. |
| **Unauth** `gateway.lp?action=URL`, `wirelesscard.lua` | **200** login HTML (~5.8 KiB). |
| **CUPS :631** | `Get-Jobs` / completed jobs **OK**; `CUPS-Create-Local-Printer` → **client-error-forbidden**; no queue creation. `file://` probe from `f1_surface_quick_probe` → **HTTPError** (fast fail). |
| **WFA :49152** | Unauth `SUBSCRIBE` + `CALLBACK` **200**; immediate **NOTIFY** captured (deep probe). `SetSelectedRegistrar` still **501**; shell **M2 PutMessage** → **400** SOAP fault (same as prior pass). |

## Operational

**VERIFIED:** after ~**80+** paced LAN requests across aggressive + WFA + CUPS probes, **`GET /login.lp` returned nginx 503** (190 B). Prior key-probe burst showed the same pattern. **Wait for HTTP 200** before more live automation (`findings/f1-ui-leads-23.1b.md`).

**Mitigation (same date, follow-up):** `scripts/f1_pacing.py` — poll `/login.lp` at most **once per 90s**, optional **45s** post-200 pause, **3s** gap between authenticated requests (`f1_ipping_control`, `f1_aggressive_software_pass`). Run **one** focused script per cooldown; do not stack aggressive + WFA + CUPS in one session.

## What was not shown

- No `/proc/rip/0108`, decrypted config, or RBI upload.
- No confirmed command execution via diagnostics, `schedulerebootset`, or device rename HTML sink.
- No multipart `import_config` / `upgradefw` file POST (would need browser-style upload + acceptance of brick risk).
- Newline ping **may** reach `ipping_helper` with split semantics — **blocked follow-up** (`f1_ipping_host_probe.py`) by **503**; prior dedicated host pass documented rejection/marker-negative (`f1-ipping-host-2026-10-12.md`). Reconcile when UI recovers.

## Next (software, when login is 200)

Gap checks that used to live in `f1_gap_attack_pass.py` are **closed** (auth boundaries, sched oracle, blind SSRF, service reachability, saved-export header). That script no longer probes. See [f1-gap-attack-pass-2026-10-12.md](f1-gap-attack-pass-2026-10-12.md). Full queue: [research composite](f1-research-composite-2026-10-13.md).

1. **Single** `f1_ipping_host_probe.py` (+ optional `--pollution`) after cooldown — discriminates newline vs duplicate-field parser.
2. **Multipart** `import_config` / minimal `.bin` on lab clone only if owner accepts transient import failure risk.
3. **Stored XSS**: device rename via UI + second admin session DOM check (server fragment for `EDIT` was not reflective).
4. **Decompile path** unchanged: needs **23.1.b rootfs** or **`RIP_ID_RANDOM_KEY_B`** — UI surface does not substitute.
