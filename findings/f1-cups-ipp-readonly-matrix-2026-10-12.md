# CUPS :631 read-only IPP operation matrix — 2026-10-12

## Result

**VERIFIED:** on the owned F1 (`192.168.2.1`, firmware build `23.1.b` per prior UI evidence), unauthenticated clients can reach the IPP stack for a broad set of **read-only** operations while ordinary HTTP page fetches stay at **403**. No printer was configured (`No destinations added.` / empty job list). No job-creation, administrative write, or credential guessing was performed.

This extends [management-auth-boundaries-2026-10-12.md](management-auth-boundaries-2026-10-12.md) from a single `CUPS-Get-Printers` probe to a paced matrix. Upstream policy semantics for v2.2.10 remain in [cups-http-ipp-source-boundary.md](cups-http-ipp-source-boundary.md). Hub: [docs/f1-cups-631.md](../docs/f1-cups-631.md).

## Method

- Driver: `scripts/cups_ipp_readonly_matrix.py` (19 requests, **3 s** spacing, no cookies/credentials).
- Encoder cross-checked against the prior `get-printers.request.private` fixture (`scripts/test_cups_ipp_readonly_matrix.py`).
- Private raw headers/bodies: `artifacts/management/cups-ipp-matrix-20261012T055714Z/`.
- Supplemental attribute variants (four extra probes, same host) clarified validation errors only; not re-run in the main summary JSON.

## HTTP surface (browser vs IPP)

| Request | HTTP | Notes |
|---|---|---|
| GET `/`, `/admin/`, `/printers/`, `/admin/conf/cupsd.conf` | **403** | Identical **343-byte** HTML bodies; `CUPS v2.2.10` string in body (**body-reported**, not binary ID); no `WWW-Authenticate` |
| HEAD `/` | **403** | **308-byte** body (not header-only 200) — location/access gate dominates on this device |
| POST `/` with `Content-Type: text/plain` | **401** | `WWW-Authenticate` present — non-IPP POST is not anonymously accepted |
| POST `/` with `Content-Type: application/ipp` | **200** | IPP responses below |

**DERIVED:** the Homeware/UI session is irrelevant to these CUPS probes; the split is **HTTP page policy vs IPP `application/ipp` dispatch**, consistent with upstream `client.c` (IPP POST before disabled-web-interface rejection for non-IPP types).

## IPP read operation matrix (unauthenticated)

All rows: `POST http://192.168.2.1:631/`, `application/ipp`, IPP **1.1**. Classification: **handler reached** = HTTP 200 and `Content-Type: application/ipp` (IPP status may still be an error).

| Operation | IPP op | IPP status | Handler | Application message / outcome |
|---|---|---|---|---|
| CUPS-Get-Printers | `0x4002` | `client-error-not-found` (`0x0406`) | Yes | `No destinations added.` (matches prior pass) |
| CUPS-Get-Default | `0x4001` | `0x0406` | Yes | `No default printer.` |
| CUPS-Get-Classes | `0x4003` | `client-error-bad-request` (`0x0400`) | Yes | `Missing required attributes.` (no `printer-uri` in main matrix) |
| CUPS-Get-Devices | `0x400B` | `server-error-internal` (`0x0500`) | Yes | `cups-deviced failed to execute.` — **policy check passed**; backend helper failed |
| CUPS-Get-PPDs | `0x400F` | `0x0400` | Yes | `Missing required attributes.` |
| CUPS-Get-PPD | `0x400E` | `0x0400` | Yes | `Missing required attributes.` (with `ppd-name=everywhere` in main matrix) |
| Get-Printer-Attributes | `0x000B` | `0x0406` | Yes | Printer/class does not exist (URI `ipp://192.168.2.1:631/`) |
| **Get-Jobs** | `0x000A` | **`successful-ok` (`0x0000`)** | Yes | **Empty job list** (72-byte IPP body; no job attributes returned) |
| Get-Job-Attributes | `0x0009` | `0x0406` | Yes | `Job #1 does not exist.` |
| Get-Printer-Supported-Values | `0x0013` | `0x0406` | Yes | Printer/class does not exist |
| Get-Subscriptions | `0x000C` | `0x0400` | Yes | `Missing required attributes.` |
| Get-Subscription-Attributes | `0x000D` | `0x0400` | Yes | `Missing required attributes.` |
| Get-Notifications | `0x000E` | `0x0400` | Yes | `Missing required attributes.` |

**Not observed in this matrix:** HTTP **401** on any `application/ipp` read probe. Upstream template lists `CUPS-Get-Devices` under administrator `<Limit>` with `Require user @SYSTEM`; the live device still entered `get_devices()` and attempted `cups-deviced` (internal error, not auth refusal). ~~**UNKNOWN:** effective `cupsd.conf` / policy on the router; may differ from template or use a permissive default-policy tail (`<Limit All> Order deny,allow`).~~ **Superseded (2026-11-07):** the live `cupsd.conf` was obtained read-only. It has no `<Policy>` section, so cupsd auto-creates the `default` policy from upstream `conf.c`; that auto-created policy has the permissive all-operations tail named above and requires `@SYSTEM` for the state-changing printer operations, which explains both the unauthenticated reads and the forbidden `CUPS-Create-Local-Printer`. See [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md).

## Impact assessment (honest)

| Claim | Status |
|---|---|
| Session bypass of Homeware UI via CUPS | **Refined:** IPP read path bypasses **CUPS HTTP page** denial, not UI login |
| Printer enumeration | **Negative** with current config (no destinations) |
| Job queue disclosure | **Verified empty** via `Get-Jobs` + `successful-ok`; does not prove historical jobs or other users' jobs if queues were populated |
| Config file read (`/admin/conf/cupsd.conf`) | **Denied** at HTTP layer (403, same page as `/`) |
| Admin read/write, PPD dump, device discovery | **Not demonstrated**; `CUPS-Get-Devices` failed internally; PPD/subscription ops stalled on attribute validation |
| Known CVE / RCE chain | **Not tested**; CUPS **2.2.10** is a version **lead** only |

## What changed

- Browser **403** on `/` no longer supports inferring total denial of CUPS: **at least eight** distinct read operations reach IPP handlers without credentials, including **`Get-Jobs` success** and **`CUPS-Get-Devices` execution attempt**.
- **HEAD /** on this firmware returns **403**, not the header-only 200 described for `WebInterface off` alone in upstream source — implicates **location/authorization** configuration on the device.
- Non-IPP POST is **401**, bounding anonymous abuse to well-formed IPP (still significant surface).

## Follow-up (2026-10-12 later pass)

See [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md): ipptool **PASS** on `Get-Jobs` / completed jobs; `cups-deviced` / `cups-driverd` **internal errors**; remote `CUPS-Create-Local-Printer` **forbidden**; **vendor opcode behavior** diverges from upstream for `CUPS-Set-Default` (`0x4005`).

## Next discriminating experiments

1. **With a configured printer/queue** (user action on device): repeat `CUPS-Get-Printers`, `Get-Printer-Attributes`, and `Get-Jobs` to see whether attribute leakage exceeds empty-queue behavior.
2. **Obtain effective CUPS config** from firmware/rootfs (offline) rather than probing write/admin IPP ops on the live LAN.
3. **CVE correlation** for CUPS 2.2.x against *unauthenticated IPP read* prerequisites only; treat as hypothesis until a controlled repro exists.

## Reproduction

```sh
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
cd scripts && python3 -m unittest test_cups_ipp_readonly_matrix -v
cd scripts && python3 cups_ipp_readonly_matrix.py
cd scripts && python3 cups_ipp_followup.py      # ipptool + extended reads
cd scripts && python3 cups_ipp_policy_probe.py  # safe write/limit discriminators
```

Private evidence: `artifacts/management/cups-ipp-matrix-*`, `cups-ipp-followup-*`, `cups-ipp-policy-*`.

## Write-side policy probe and opcode-map correction (2026-11-07, VERIFIED)

Two corrections and one new result, from `scripts/cups_ipp_writeside_probe.py` (22 paced unauthenticated IPP POSTs against nonexistent printers/classes/job-ids at `192.168.1.1:631`; raw responses in `artifacts/cups-writeside-2026-11-07/`).

**Opcode-map correction (supersedes several labels in the tables above).** The matrix above used an incorrect CUPS private-opcode map. Against the authoritative public `cups/ipp.h` (values stable since CUPS 1.x): `0x4003` is **CUPS-Add-Modify-Printer**, not CUPS-Get-Classes; `0x4005` is **CUPS-Get-Classes**; `0x400A` is CUPS-Set-Default; `0x400E` is CUPS-Authenticate-Job, not CUPS-Get-PPD; `0x400F` is CUPS-Get-PPD, not CUPS-Get-PPDs; `0x000C`/`0x000D`/`0x000E` are **Hold-Job/Release-Job/Restart-Job**, not the subscription reads; `0x0013` is **Set-Printer-Attributes**, not Get-Printer-Supported-Values. Consequences:

1. The "read-only matrix" above **accidentally probed six write operations** — Add-Modify-Printer (0x4003), Set-Printer-Attributes (0x0013), Hold-Job (0x000C), Release-Job (0x000D), Restart-Job (0x000E) — plus CUPS-Get-PPD (0x400F). Their recorded responses stand as data; the labels were wrong.
2. The [policy finding's](f1-cups-ipp-policy-2026-10-12.md) "Vendor IPP dispatch does not match upstream 2.2.10 for `CUPS-Set-Default` (`0x4005`)" is **superseded**: `0x4005` is upstream CUPS-Get-Classes, whose empty-list response is exactly the "No destinations added." body observed (same handler family as CUPS-Get-Printers). There is no vendor divergence; the real CUPS-Set-Default (`0x400A`) probe below behaves upstream-consistently.

**Write-side results (correct opcodes, nonexistent targets only).** Distinguishing policy rejection from resource lookup by response (HTTP 401 HTML = auth wall; IPP `client-error-not-found*` = policy passed, resource missing):

| Operation (opcode) | Anonymous result | Interpretation |
| --- | --- | --- |
| CUPS-Add-Modify-Printer (0x4003), CUPS-Add-Modify-Class (0x4006) | **HTTP 401** (HTML) | auth wall — the only walled ops (plus CUPS-Create-Local-Printer forbidden per prior matrix) |
| Cancel-Job / Hold-Job / Release-Job (0x0008/C/D, job-id 999) | not-found | policy passed |
| Pause-Printer / Resume-Printer (0x0010/11) | not-found ("printer does not exist") | policy passed |
| Purge-Jobs (0x0012), Set-Printer-Attributes (0x0013), Validate-Job (0x0004), Create-Job (0x0005) | not-found | policy passed |
| CUPS-Delete-Printer (0x4004), CUPS-Delete-Class (0x4007) | not-found | policy passed |
| CUPS-Accept-Jobs / CUPS-Reject-Jobs (0x4008/9), CUPS-Set-Default (0x400A), CUPS-Move-Job (0x400D), CUPS-Authenticate-Job (0x400E), CUPS-Get-Document (0x4027) | not-found | policy passed |
| Cancel-Jobs (0x0033) | operation-not-supported (0x0501) | op newer than 2.2.10 — consistent |
| CUPS-Get-PPDs (0x400C — genuinely unprobed before) | **server-error-internal**, helper failed to execute | policy passed; `cups-driverd` broken like `cups-deviced` |

**Conclusions.** With no queue configured nothing changes state (post-probe `Get-Printers`/`Get-Classes` still `not-found`, `Get-Jobs` still the identical empty `successful-ok` body — verified). But the exhaustion-pass statement that the auto-created policy requires `@SYSTEM` for "state-changing printer and class operations" is **overbroad**: only Add-Modify-Printer/Class and Create-Local-Printer are walled; an unauthenticated LAN client's requests for Cancel-Job, Hold/Release-Job, Pause/Resume-Printer, Purge-Jobs, Set-Printer-Attributes, Delete-Printer, Delete-Class, Accept/Reject-Jobs, Set-Default, Move-Job, Create-Job, Validate-Job, and Authenticate-Job all pass the policy gate and stop only at resource lookup. **DERIVED exposure (queue-dependent):** if a printer/queue is ever configured on this unit, an unauthenticated LAN peer can drive these state operations against it (cancel/purge jobs, pause, delete the printer) up to the job-ownership layer; that impact remains undemonstrated because no queue exists. Job-owning ops on *other users'* jobs may still hit the `@OWNER`/`@SYSTEM` check at the job layer — the not-found responses here precede it and cannot speak to it.

## Queue-dependent test — the write exposure is REFUTED for the tested ops (2026-11-07, VERIFIED)

A real temporary queue was created on the device from the router's own localhost (`CUPS-Create-Local-Printer` `0x4028` as root, printer-attrs group with `printer-name`/`device-uri`, plus the operation-group `printer-uri` that cupsd's generic pre-check requires — the local-users gate passes for 127.0.0.1). The anonymous LAN client was then re-run against the existing queue:

| Operation (anonymous LAN) | Queue exists | Verdict |
| --- | --- | --- |
| `Get-Printer-Attributes` | `successful-ok`, **6384 bytes of attributes** (state, device-uri, everything) | **Full anonymous attribute disclosure confirmed** |
| `Pause-Printer` | **HTTP 401** | auth wall |
| `Resume-Printer` | **HTTP 401** | auth wall |
| `Delete-Printer` (LAN and localhost, no credentials) | **HTTP 401** | auth wall |

**Correction (supersedes the DERIVED queue-dependent exposure above):** the earlier write-side "policy passed" verdicts were an artifact of probing *nonexistent* resources — with the resource present, the auto-created policy's `@SYSTEM` requirement blocks state-changing operations for unauthenticated clients (including from localhost without credentials). The realistic anonymous exposure on an existing queue is therefore **reads and attribute disclosure, not state changes**. The temporary queue was removed by restarting `cupsd` (temp queues are memory-only); post-restart `Get-Printer-Attributes` returns `not-found` and `printersharing.config.enabled` is unchanged.
