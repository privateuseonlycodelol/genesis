# User Wi-Fi SSID down (2026-11-06)

Read-only check from the Mac on `en10` (`192.168.1.100`) to `192.168.1.1`. Ping answered. SSH as root succeeded. Uptime at the check was 4595 seconds. Nothing was restarted, killed, or written. `airlauncher`, `aircdf`, DNS, telemetry, Tailscale, nginx, and overlay files were not touched.

## What is up

**VERIFIED:** both `hostapd` processes from the earlier check are still the same pids: 14927 (`hostapd -B /tmp/wl0_hapd.conf`) and 16174 (`hostapd -B /tmp/wl1_hapd.conf`). `wifi_md`, `wlan_mgr`, `eapd`, `acsd2`, `wps_pbcd`, `wbd_slave`, and `hspotap` are running. `wpa_supplicant` is not in the process list. `br-lan` is up and contains `eth0`–`eth3`, `wl0`, `wl0.1`, and `wl1`. `br-guest` has no ports.

`wl -i wl0 isup` and `wl -i wl1 isup` are `1`. Both `wl radio` masks are `0x0000`. UCI `wireless.*.mode` for the AP sections is `ap`. The filtered `uci show wireless` had no `disabled` keys. `hostapd_cli` reports `state=ENABLED` on both radios, SSID `Telia-C66283`, channel 36 and channel 1, and zero stations.

## What is down

**VERIFIED:** the user BSS is not up in the driver.

- `wl -i wl0 bss` and `wl -i wl1 bss` print `down`. `wl status` shows SSID `Telia-C66283` with BSSID `00:00:00:00:00:00` on both. Channels are 36/160 and 1.
- `wl0.1` is the exception: `wl bss` prints `up`, SSID `BH-C66283`, BSSID `8A:B5:3C:C6:52:84`. Its hostapd config has `ignore_broadcast_ssid=1`. The main SSID lines have `ignore_broadcast_ssid=0`.
- `hostapd_cli` still names main BSSIDs `a2:b5:3c:c6:52:83` and `a2:b5:3c:c6:52:8b`. Those do not match the zero BSSID in `wl status`.
- Over 3 seconds, the shared wl0/wl0.1 `txbcnfrm` counter rose from 48559 to 48588 (about 10 beacons/s, one beacon interval). `wl1` `txbcnfrm` stayed 7077, including a later sample. Only one BSS on the 5 GHz radio is up, so that counter is the hidden backhaul, not `Telia-C66283`.
- The Mac Wi-Fi scan (`en0`, power on, not associated) saw 55 networks and zero copies of `Telia-C66283`. A directed scan for that name and for `BH-C66283` also returned zero. The scanner did see other networks, so an empty result is not a dead Mac radio. CoreWLAN did not return BSSIDs, so a hidden channel-36 beacon at about -44 dBm was not tied to this box.
- `logread` had 713 lines and no `hostapd`, `wifi`, `wlan`, or `beacon` lines. `dmesg` is still adding `wl1: dhd_prot_ioctl: status ret value is -4 cmd=263` (759 then 761, two seconds apart). There were 33 `wl0:` lines.

**DERIVED:** `hostapd` is alive and reports ENABLED, and the user SSID is still not on the air. The 2.4 GHz driver is failing ioctls and has stopped beaconing. The 5 GHz main BSS is down in `wl`. The hidden backhaul BSS is the only one `wl` reports up.

## Brought back up, 23:08 CET

**VERIFIED.** `ubus call wireless reload` returned 0 and left both main BSS entries `down`, with the same `hostapd` pids. `wl -i wl0 bss up` and `wl -i wl1 bss up` then printed `up`. `wl status` showed `Telia-C66283` with BSSID `A2:B5:3C:C6:52:83` on `wl0` (channel 36/160) and `A2:B5:3C:C6:52:8B` on `wl1` (channel 6). Two seconds later `wl1` `txbcnfrm` moved from 7105 to 7118. `dnsproxy` stayed 8717. No Mac scan was run after this; the `airport` command is not on this Mac. A reboot can hit the same driver rejection again. The launcher was not restarted.

## Why it would not stay up

**VERIFIED, 23:13–23:16 CET.** `wl bss up` made both main BSS entries `up`, then both were `down` again inside about two seconds. `hostapd` logged `AP-ENABLED` and stayed `ENABLED`. The driver event was `E_LINK` down, reason `0004`, on `wl0` and `wl1` together. Freezing `acsd2`, `hostapd`, `wlan_mgr`, or `wifi_md` alone did not keep `wl1` up. Freezing `wbd_slave` (pid 16803) did: `wl1` stayed `up` for 8 seconds. `wb_cli -s info` returned `Agent not joined to Controller`. `wbd_master` was not running. `map_block_bh_at_boot_up` was already `0`.

`wbd_slave` was left stopped (`ps` state `T`). After another `wl bss up`, both BSS entries were still `up` 8 seconds later, with BSSIDs `A2:B5:3C:C6:52:83` and `A2:B5:3C:C6:52:8B`. A reboot starts `wbd_slave` again. The mesh agent was not reconfigured.

## Mesh list changed, 23:22 CET

**VERIFIED.** `nvram` `wbd_ifnames` was `wl1 wl0 wl0.1`. It is now `wl0.1`, and `non_map_ifnames` is `wl0 wl1`. `nvram commit` was run. The slave was restarted (pid 19814). Twenty seconds later both customer BSS entries were `up` with the same BSSIDs. `/etc/init.d/genesis-persist` (`START=99`) sets those nvram values on boot and brings a down customer BSS back up. It was run once. `dnsproxy` stayed 8717. A reboot was not performed, so the boot path itself is not yet observed. The mesh slave is still running and still reports that it has not joined a controller. It no longer has the customer radios in its interface list.

## What was not done

No `wl bss up`, no `wifi` reload, no hostapd restart. The init scripts present are `bcm-wlan-drivers.sh`, `wifi.sh`, `wifi_md.sh`, and `wlan_mgr`. A start was not the obvious recovery: the Wi-Fi processes are still running, and `hostapd_cli` already says ENABLED. Killing them was out of scope.

Earlier the same day, process checks described the radios as up. That was process and `iwinfo` state at those passes. This check supersedes it for the air state. See [f1-idle-services-stopped-2026-11-06.md](f1-idle-services-stopped-2026-11-06.md).

## Later recheck (2026-11-07 14:48 CET)

**VERIFIED, read-only:** `iwinfo` reported `Telia-C66283` on `wl0` channel 36 / 5180 MHz and `wl1` channel 11 / 2462 MHz. `hostapd_cli all_sta` counted one associated station on `wl0`, none on `wl1`; both hostapd interfaces reported ENABLED. This supersedes the 2026-11-06 observation that the user SSID was not visible at that time. No Wi-Fi settings or processes were changed.
