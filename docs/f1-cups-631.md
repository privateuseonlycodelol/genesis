# CUPS / IPP on LAN port 631 (Telia F1 23.1.b)

**Status:** measured on owned `192.168.2.1`; **no demonstrated exploit** (no admin write, no config file read, empty print queues).

## What we know

| Layer | Behavior |
| --- | --- |
| TCP | **631** open on LAN (see [software-pass-live-access.md](../findings/software-pass-live-access.md)) |
| HTTP GET/HEAD | **403**, body cites **CUPS v2.2.10** (body-reported) |
| IPP `application/ipp` POST | Unauthenticated **read** ops reach the scheduler (e.g. **Get-Jobs** `successful-ok` on empty queue) |
| Homeware UI session | **Not** used for CUPS; separate trust boundary from port **80** |

## Canonical findings

1. [f1-cups-ipp-policy-2026-10-12.md](../findings/f1-cups-ipp-policy-2026-10-12.md) — policy model, ipptool, safe write probes, `cupsd.conf` ground-truth paths  
2. [f1-cups-ipp-readonly-matrix-2026-10-12.md](../findings/f1-cups-ipp-readonly-matrix-2026-10-12.md) — full read-operation matrix  
3. Policy resolution and public-issue applicability (2026-11-07): the live conf has no `<Policy>` block, so the upstream auto-created `default` policy applies — reads anonymous, state-changing printer operations require `@SYSTEM`; post-2.2.10 fixes mapped — see [f1-miniupnpd-cwmpd-2026-11-06.md](../findings/f1-miniupnpd-cwmpd-2026-11-06.md)  
4. [management-auth-boundaries-2026-10-12.md](../findings/management-auth-boundaries-2026-10-12.md) — initial boundary pass  
5. [cups-http-ipp-source-boundary.md](../findings/cups-http-ipp-source-boundary.md) — upstream CUPS 2.2.10/2.2.12 source vs live  
6. [f1-printersharing-webui-2026-10-29.md](../findings/f1-printersharing-webui-2026-10-29.md) — printersharing modal read-back: Enabled=1, no webui control served; the earlier POST used field names the form lacks  
7. [cups-udp631-browse-source-2026-10-29.md](../findings/cups-udp631-browse-source-2026-10-29.md) — UDP 631: pinned 2.2.10 `cupsd` has no browse listener (DERIVED); the open|filtered UDP reading is probably `cups-browsed`, version UNKNOWN

Homeware **:80** routes: [f1-api-map.md](../findings/f1-api-map.md) (**Parallel surfaces** table).

## Tools (paced, unauthenticated)

```sh
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"
cd scripts
python3 -m unittest test_cups_ipp_readonly_matrix -v
python3 cups_ipp_readonly_matrix.py
python3 cups_ipp_followup.py
python3 cups_ipp_policy_probe.py
```

Private evidence under `artifacts/management/cups-ipp-matrix-*`, `cups-ipp-followup-*`, `cups-ipp-policy-*`.

**Pacing:** use **≥3 s** between requests; burst probing can trigger nginx **503** ([f1-ui-leads-23.1b.md](../findings/f1-ui-leads-23.1b.md)).

## Open blockers

- Shipped **`/etc/cups/cupsd.conf`** is now on disk (1,052 bytes, same file on `/rom` and live). HTTP `/` and `/admin/` from `192.168.1.100` are still **403**. See [f1-quad-overlay-flash-2026-11-06.md](../findings/f1-quad-overlay-flash-2026-11-06.md) and [f1-cups-ipp-policy-2026-10-12.md](../findings/f1-cups-ipp-policy-2026-10-12.md).

## Update 2026-11-07 — write-side policy probe, opcode corrections

- The historical CUPS private-opcode map used by the earlier matrices was wrong in several places (`0x4003`=Add-Modify-Printer not Get-Classes, `0x4005`=Get-Classes not Set-Default, `0x400E`=Authenticate-Job not Get-PPD, `0x400F`=Get-PPD not Get-PPDs, `0x000C/D/E`=Hold/Release/Restart-Job). The "vendor Set-Default divergence" is dissolved — it was a probe mislabel.
- New paced probe (`scripts/cups_ipp_writeside_probe.py`, 22 ops, nonexistent targets): anonymous requests **pass the policy gate** for Cancel/Hold/Release-Job, Pause/Resume-Printer, Purge-Jobs, Set-Printer-Attributes, Create/Validate-Job, Delete-Printer, Delete-Class, Accept/Reject-Jobs, Set-Default, Move-Job, Authenticate-Job, Get-Document (all stop at not-found since no queue exists). Only CUPS-Add-Modify-Printer/Class return **HTTP 401**; CUPS-Create-Local-Printer stays forbidden. CUPS-Get-PPDs (0x400C) executes with a broken `cups-driverd` helper.
- DERIVED queue-dependent exposure: with a configured queue, an unauthenticated LAN peer can drive printer/job state ops up to the job-ownership layer. Not demonstrated (no queue on this unit). Full table: [matrix finding](../findings/f1-cups-ipp-readonly-matrix-2026-10-12.md).
