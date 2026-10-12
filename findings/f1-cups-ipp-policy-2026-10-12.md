# CUPS :631 policy, helpers, and vendor IPP behavior — 2026-10-12

## Scope

Continues the read-only CUPS lane on the owned F1 (`192.168.2.1`). No credentials, no job creation, no deliberate queue creation. Authenticated log harvest was **not** performed after an unauthenticated control returned **HTTP 503** (rate/lockout protection).

Prior matrix: [f1-cups-ipp-readonly-matrix-2026-10-12.md](f1-cups-ipp-readonly-matrix-2026-10-12.md). Upstream reference: [cups-http-ipp-source-boundary.md](cups-http-ipp-source-boundary.md). Entry index: [docs/f1-cups-631.md](../docs/f1-cups-631.md).

## Effective configuration (derived, not extracted)

| Observation | Inference | Confidence |
|---|---|---|
| TCP **631** open on LAN; `Server: CUPS/2.2 IPP/2.1` | `Listen` includes a non-loopback interface (not localhost-only template) | **DERIVED** |
| All tested **GET/HEAD** paths (`/`, `/admin/`, `/printers/`, `/admin/conf/cupsd.conf`, `/version.txt`, `/admin/log/error_log`, …) → **403**, identical **343-byte** HTML | `<Location />` (and siblings) use **deny-by-default** without an `Allow from` matching the client; matches CUPS docs on “Forbidden” for remote web UI | **DERIVED** |
| Body text `Forbidden - CUPS v2.2.10` | **WebInterface** likely **off** or otherwise not serving pages; version string is **body-reported** | **DERIVED** |
| **`application/ipp` POST** reaches handlers without `WWW-Authenticate` on read probes | Default IPP **policy tail** (`<Limit All> Order deny,allow`) or vendor-equivalent allows anonymous **read** ops; separate from HTTP location ACL | **DERIVED** |
| No `cupsd.conf` from firmware/rootfs yet | RBI/strings pass had **no** `cupsd.conf` text; offline 23.1.b rootfs still missing | **UNKNOWN** |

## ipptool cross-check (Apple CUPS 2.3.4 client → device)

Driver: `scripts/cups_ipp_followup.py` (fixed single-URI `ipptool` invocation). Evidence: `artifacts/management/cups-ipp-followup-20261012T060507Z/`.

| Test | IPP result | Notes |
|---|---|---|
| `get-jobs.test` | **PASS**, `successful-ok` | Confirms empty pending-job list anonymously |
| `get-completed-jobs.test` | **PASS**, `successful-ok` | Completed-job enumeration also allowed |
| `get-printers.test` | **FAIL**, `client-error-not-found` | Expected with zero queues; still proves handler reachability |
| `get-devices.test` | **FAIL**, `server-error-internal` | `cups-deviced failed to execute` (helper/runtime failure, not HTTP 401) |
| `get-ppds.test` | **FAIL**, `server-error-internal` | `cups-driverd` path fails similarly when invoked with correct ipptool attributes |

**VERIFIED:** anonymous **job-list reads** are not an encoder artifact. **VERIFIED:** admin discovery helpers are invoked (policy did not return auth denial) but **fail internally** on this firmware.

## Write / admin discriminators (still no mutation)

Driver: `scripts/cups_ipp_policy_probe.py`. Evidence: `artifacts/management/cups-ipp-policy-20261012T060538Z/`.

| Probe | Result | Takeaway |
|---|---|---|
| `CUPS-Create-Local-Printer` (`0x4028`) from LAN | IPP **`client-error-forbidden`**, `Only local users can create a local printer.` | Matches upstream localhost gate; **no queue created** |
| `Pause-Printer` on `/printers/nosuch` | `client-error-not-found` (printer missing) | Policy not reached; **no printer state change** |
| `CUPS-Add-Modify-Printer` (`0x4004`) with `/printers/zzgenesis999` | `client-error-not-found` (printer/class does not exist); follow-up `CUPS-Get-Printers` still **no destinations** | **No queue created**; behavior does **not** match upstream `add_printer()` create path |
| `CUPS-Set-Default` (`0x4005`) with missing queue | **`No destinations added.`** (same body hash as `CUPS-Get-Printers`) | **Vendor IPP dispatch does not match upstream 2.2.10** for this opcode |
| `CUPS-Get-Classes` with `/classes/nosuch` | `client-error-bad-request` (URI form message) | Stricter/different validation than upstream exception list for class listing |

**Not observed:** HTTP **401** on any tested `application/ipp` operation. **Not demonstrated:** administrative write success, PPD dump, device list, or config file disclosure.

## Version / CVE context (REPORTED + DERIVED)

- Body and header claim **CUPS 2.2.x**; **2.2.10** appears in the HTML forbidden page. **Binary identity unverified.**
- **CVE-2018-4300** (predictable web session cookies) is fixed in **2.2.10** per [OpenPrinting release notes](https://github.com/apple/cups/releases/tag/v2.2.10). Prerequisites: **web interface enabled** and reachable. Here the web UI is **403** for anonymous GET; impact **not demonstrated** on this unit.
- Later CUPS CVEs (2023–2025 chains) target different components/versions; **no repro attempted**.

## What this changes

1. **Impact ceiling (today):** unauthenticated **IPP read/metadata** on an **empty** print server—job lists, server queries, and helper **invocation attempts**—not Homeware admin, not firmware, not config files via HTTP.
2. **Policy model:** HTTP location ACL **denies pages**; IPP policy **allows reads** and attempts **driver/device helpers**; **remote local-queue creation** is blocked; **queue administration opcodes on this build do not mirror upstream** (treat version string as weak signal).
3. **Blocker for “obvious” offline config:** 23.1.b rootfs / `cupsd.conf` still unavailable; RBI reference image did not yield strings.

## Config ground truth (`cupsd.conf`) — how to obtain it

**Not available today** via CUPS HTTP (`GET /admin/conf/cupsd.conf` → same **403** as `/`) or Homeware `export_config` (encrypted backup envelope, not `/etc/cups/*`).

| Path | What you get | Status on this project |
| --- | --- | --- |
| **Root/shell on F1** | `cat /etc/cups/cupsd.conf` | **No shell** documented on 23.1.b |
| **23.1.b RBI → decrypt → squashfs** | `etc/cups/cupsd.conf` in extracted rootfs | **No 23.1.b RBI** captured; GCNT-X OSCK **unresolved** ([decomp-kickoff.md](decomp-kickoff.md), [gcnt-x-root-path.md](gcnt-x-root-path.md)) |
| **WAN capture during ISP upgrade** | RBI blob in pcap → offline extract | Plausible; mirror placement must be correct ([decomp-kickoff.md](decomp-kickoff.md)) |
| **Authenticated logviewer** `?process=cupsd` | Startup lines may mention `Listen` | **503** after burst; pace carefully ([f1-ui-leads-23.1b.md](f1-ui-leads-23.1b.md)) |

Until one of these succeeds, `Listen` / `<Location>` / `<Policy>` here remain **DERIVED** from live HTTP/IPP behavior, not verified file contents.

## Next experiments (ordered)

1. **Rootfs or package scrape** when 23.1.b filesystem is available—compare shipped `cupsd.conf` to derived model.
2. **After user adds a USB/network printer** on the LAN UI—repeat `Get-Jobs` / `Get-Printer-Attributes` for data leakage with real queues.
3. **If HTTP 503 clears**—authenticated `logviewer` filter `process=cupsd` for startup `Listen`/`WebInterface` lines (read-only).

## Reproduction

```sh
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
cd scripts && python3 cups_ipp_followup.py
cd scripts && python3 cups_ipp_policy_probe.py
```
