# USP / CWMP path to `IPPing.Host` — LAN attempt — 2026-10-12

Target: owned F1 at `192.168.2.1`, build label `23.1.b`. Follow-up to [PING host validation](f1-ipping-host-2026-10-12.md) (web form blocks metacharacters; **HYPOTHESIS** that TR-069/USP `Device.IP.Diagnostics.IPPing.Host` could skip `restartTest`).

## What we tried

Driver: `scripts/f1_usp_ipping_probe.py` (`scripts/test_f1_usp_ipping_probe.py` for closed-port SOAP skip).

1. **TCP connect** on LAN for CWMP/USP-style listeners: **7547**, **7557**, **7577**, **1883**, **8883**, **5683**, **61613**, **61614**, **443**, **8443**.
2. **Minimal CWMP SOAP** `GetRPCMethods` to `:7547` when the port is open (skipped here).
3. After **admin SRP login** (through nginx **503** cooldown): authenticated GET of `/usp`, `/cwmp`, `/tr069`, `/obuspa`, `/agent/usp`, `/mqtt`, `/modals/gateway-modal.lp` — no `IPPing` / `diagping` / `uci.ipping` strings in bodies.
4. **Logviewer** snapshot: confirm `obuspa_retriever` cron noise; no USP Set or `IPPing` traffic observed.

Private artifacts: `artifacts/ui/usp-ipping-20261012T072316Z/`.

## Results

| Check | Result |
| --- | --- |
| LAN **7547** (CWMP) | **VERIFIED closed** (connect refused) |
| MQTT / CoAP / STOMP ports above | **VERIFIED closed** |
| CWMP SOAP on 7547 | **Not sent** (port closed) |
| USP HTTP paths on **:80** | **VERIFIED** nginx **404** (146-byte stub); no DM strings |
| `/modals/gateway-modal.lp` (authenticated) | **VERIFIED** HTTP **404** on this unit (modal absent or route removed) |
| `obuspa_retriever.sh` in syslog | **VERIFIED** present (25 rows in one log window; e.g. `Oct 12 09:25:00`) |
| **USP Set** `IPPing.Host` + trigger `ipping_helper` | **Not exercised** — no LAN management listener or controller endpoint |

## Exploit status

| Vector | Status |
| --- | --- |
| USP **Set** `Device.IP.Diagnostics.IPPing.Host` (or UCI equivalent) from LAN | **BLOCKED** on this pass — no reachable CWMP/USP/MQTT/STOMP/CoAP listener; no way to impersonate ISP ACS from the lab LAN without additional access |
| Web diagnostics `action=PING` | Unchanged — [host validation](f1-ipping-host-2026-10-12.md) |

The unquoted-host **`io.popen`** chain in published `/usr/bin/ipping` remains a **HYPOTHESIS** for a **non-UI writer** only. This pass did **not** refute it; it did **not** test it on-device because no writer was reachable.

## Reproduction

```sh
python3 -m unittest scripts.test_f1_usp_ipping_probe -v
python3 scripts/f1_usp_ipping_probe.py --password-file artifacts/secrets/f1-admin.password --wait-obuspa 65
```

Pace UI work; stop on nginx **503** ([f1-ui-leads-23.1b.md](f1-ui-leads-23.1b.md)).

## What would be needed next

- **Reachable ACS/USP** (WAN-side TR-069, ISP MQTT/STOMP, or documented LAN MTP) with authorization to issue **Set** on diagnostics ping parameters, then loopback-only marker + `ipping_helper` log oracle ([f1-ipping-helper-2026-10-12.md](f1-ipping-helper-2026-10-12.md)).
- **23.1.b rootfs** or shell: confirm `obuspa_retriever.sh` / vendor USP data model maps `IPPing.Host` → `uci.ipping.@diagping.Host`.
- Do **not** repeat web-modal metacharacter sprays unless a new bypass is identified.
