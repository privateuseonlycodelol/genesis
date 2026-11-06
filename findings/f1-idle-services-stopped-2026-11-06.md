# Idle services stopped (2026-11-06)

Live SSH to root on the owner's F1. No reboot was performed, so "stays off after reboot" below is what the boot path reads, not a reboot that was watched. No flash. DNS, firewall, DHCP, and WAN were not edited. `cwmpd`, `wlan_mgr`, `wbd_slave`, nginx, `acsd2`, `wifi_md`, dnsmasq, the DoH proxy, dropbear, and hostapd were not stopped.

## What was stopped

| Process | Before | Init | RSS |
| --- | --- | --- | --- |
| `datausage_notif` | pid 12593, ppid 1, `/usr/bin/lua /usr/bin/datausage_notifier` | `/etc/init.d/datausage_notifier` (`START=50`, procd respawn) | 2576 kB |
| `datausaged` | pid 13087, ppid 1, `/usr/bin/lua /usr/bin/datausaged` | `/etc/init.d/datausaged` (`START=55`, procd respawn) | 2700 kB |
| `cloud-comm` | pid 19416, ppid 19225 (`airlauncher-daemon`), exe `/airties-edge/usr/sbin/cloud-comm` | none | 7332 kB |

`ps w` confirmed those three commands. After the stops, `pidof` for `datausaged`, `datausage_notifier`, and `cloud-comm` was empty. `python3 scripts/f1_usage_snapshot.py` (21:28) lists `cloud-comm` and `datausage` under `notRunning`.

## Why they were still resident

`datausage.wan.enabled` and `datausage.wwan.enabled` were already `0` and were left at `0`. The init scripts do not look at those. They start when `datausage.global.enabled` or `datausage_notifier.global.enabled` is `1`. Both options are unset, and `uci_get` defaults a missing value to `1`. `mesh_broker.AT_common.cloud_comm` was already `0` and was left at `0`. That flag had dropped `cloud-comm`'s TLS sessions earlier; the process itself is started by the Airties launcher from `data.xml`, not by that UCI key.

## How they stay off

**Usage meter.** `/etc/init.d/datausage_notifier stop` and `disable`, then the same for `datausaged`. OpenWrt `enabled` now returns non-zero. The ROM symlinks `/etc/rc.d/S50datausage_notifier` and `S55datausaged` are hidden by overlay whiteouts:

`/overlay/bank_1/etc/rc.d/S50datausage_notifier` and `S55datausaged` are char devices `0,0`.

A normal reboot does not run those scripts. A factory reset that wipes the overlay removes the whiteouts, the ROM links come back, and the unset `global.enabled` default starts both daemons again.

**cloud-comm.** There is no init script. `airlauncher-daemon` (started with `--dormant`) respawns it while the launcher config says enabled. Killing only the child came back within a few seconds (old pid 19416, new pid 12006). The launcher list is in `/airties-edge/etc/cdf/data.xml`, which is the LCM ubifs `/dev/ubi0_21` (`/opt/lcm.technicolor.com/upper/airties-edge/...`), not the signed bootfs and not an overlay whiteout. The `cloud-comm` application `<enable>` value was changed from `true` to `false` and nothing else in that file. `aircdf-daemon` was killed once; its existing `airties.run` watcher started it again and it re-read the file. The live CDF value is `launcher/applications/application[@index=2]/enable = false`.

The new launcher stays dormant until mesh broker is told the controller started. That is the same notification `/etc/init.d/airties_smart_wifi` sends:

```sh
ubus -s /var/run/lcm_ipc_lxc_ee/ubus.sock send airties.controller '{ "status": "started" }'
```

After that, the launcher log shows `executing:` for multiap-controller, air-steer-ng, map-dpp-configurator, air-map-datasync, airconnt, airpcapt, airnetreq, air-dpi, and air-domosd. It does not mention `cloud-comm`. Those other Airties processes were running again. `cloud-comm` was not.

That ubus send also made `mesh_broker` exit and return as a new pid (19338, then 17182). Its init script was not called. `wlan_mgr` (15564), both hostapd processes (21811, 21843), and `wbd_slave` (21853) kept their pids.

On a later boot, `aircdf-daemon` is started with `--parser.path_ro` pointed at this file, and the launcher starts applications whose `enable` is true. `cloud-comm` stays out of that list while the tag is false. A factory reset that only wipes `/overlay/bank_1` does not put this LCM file back. This pass did not test whether a full factory reset also erases `ubi0_21`.

## Checks after the stops

- `nslookup example.com 127.0.0.1` returned IPv4 and IPv6 addresses.
- `iwinfo` showed `wl0` and `wl1` in Master mode. `wlan_mgr` and both `hostapd` processes were still running.
- SSH still authenticated.
- Left running: `cwmpd`, `wlan_mgr`, `wbd_slave`, `mesh_broker` (new pid, see above), nginx, `acsd2`, `wifi_md`, dnsmasq, `/usr/bin/lua /usr/sbin/doh-proxy.lua`, dropbear, hostapd. The Lua forwarder named here was the one running at this pass. Later the same day it was replaced by dnsproxy; see [f1-doh-and-tracking-2026-11-06.md](f1-doh-and-tracking-2026-11-06.md).

## Turn them back on

Usage meter:

```sh
/etc/init.d/datausage_notifier enable
/etc/init.d/datausaged enable
/etc/init.d/datausage_notifier start
/etc/init.d/datausaged start
```

`cloud-comm`:

1. In `/airties-edge/etc/cdf/data.xml`, set the `cloud-comm` application's `<enable>` back to `true`.
2. Reboot. Boot is the path that was shown to load this file and then start every enabled launcher app.

A live CDF set of `launcher/applications/application[@index=2]/enable` was not tried. The controller `started` ubus event used above also recycled `mesh_broker`, so it is a poor way to toggle this one app.

## Not shown

No reboot. No proof that a factory reset clears the LCM copy of `data.xml`. `datausage.global.enabled` was not created; the interface `enabled` values were already `0` and do not gate these init scripts.
