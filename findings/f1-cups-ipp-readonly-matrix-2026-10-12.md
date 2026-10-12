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

**Not observed in this matrix:** HTTP **401** on any `application/ipp` read probe. Upstream template lists `CUPS-Get-Devices` under administrator `<Limit>` with `Require user @SYSTEM`; the live device still entered `get_devices()` and attempted `cups-deviced` (internal error, not auth refusal). **UNKNOWN:** effective `cupsd.conf` / policy on the router; may differ from template or use a permissive default-policy tail (`<Limit All> Order deny,allow`).

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
