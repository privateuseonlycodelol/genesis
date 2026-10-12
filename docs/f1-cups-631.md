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
3. [management-auth-boundaries-2026-10-12.md](../findings/management-auth-boundaries-2026-10-12.md) — initial boundary pass  
4. [cups-http-ipp-source-boundary.md](../findings/cups-http-ipp-source-boundary.md) — upstream CUPS 2.2.10/2.2.12 source vs live  

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

- Shipped **`/etc/cups/cupsd.conf`** requires **23.1.b rootfs** or **root shell** ([decomp-kickoff.md](../findings/decomp-kickoff.md), [gcnt-x-root-path.md](../findings/gcnt-x-root-path.md)).
