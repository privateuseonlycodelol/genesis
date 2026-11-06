# F1 usage snapshot — 2026-11-06

**VERIFIED** read-only SSH from this Mac to `root@192.168.1.1` at 20:59 local (`scripts/f1_usage_snapshot.py`). No UCI write, no config change. Password was not printed. Numbers are in gitignored `artifacts/ui/router-usage-latest.json`.

The kept sample is the second SSH. The first, at 20:56, put the process walk inside the CPU window and reported 51.7% CPU. That figure is the collector, not the idle box. The 20:59 read measures CPU on a quiet one-second `/proc/stat` gap **before** the process walk.

| Item | 20:59 read |
| --- | --- |
| Uptime | 843 s (14m 3s) |
| Load | 0.21 / 0.43 / 0.45 |
| CPU | 6.0% over 1 s |
| RAM | 374.8 / 483.3 MiB used (108.5 MiB available) |
| Kernel slab | 103.2 MiB (`MemInfo` Slab) |
| Process RSS | 317.4 MiB (sum of VmRSS) |
| Overlay free | 84.7 MiB |
| WAN eth4 | 344,105,913 B in / 31,766,252 B out |
| LAN br-lan | 30,904,652 B in / 344,282,355 B out |

**DERIVED:** uptime was 1h 13m in the 20:42 report and 843 s at 20:59, so the box rebooted between those reads. The byte counters are since that boot. Average rate on the dashboard is counter ÷ uptime.

Process CPU is `top`'s second sample. Above 0%: `acsd2`, `wifi_md`, `dropbear`, `dhd_watchdog_th` (each 1%). Largest RSS: `lua` 16.7 MiB, `wbd_slave` 7.7, `cwmpd` 7.5, `wlan_mgr` 7.3, `cloud-comm` 7.2.

**Idle resident** (cmdline or comm match, CPU under 1%): `cwmpd`, `cloud-comm`, several `airties` processes (largest 4.1 MiB), `datausaged`, `datausage_notif`. **Not in the process list:** mosquitto, obuspa, miniupnp, F-Secure, sense.

Slab and the VmRSS sum are different counters. They overlap, so they are not two slices of the 374.8 MiB used.

Refresh: `python3 scripts/f1_usage_snapshot.py`. A failed SSH keeps the last good numbers and sets `error`.
