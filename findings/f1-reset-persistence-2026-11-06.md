# Reset parking lot, the large Lua process, and Telia management — 2026-11-06

Live bank 1. No factory reset and no flash. The install SSH did not send `reboot`. The router then came up on its own: at 21:49 CET, `uptime` was 6 minutes. No reboot-reason file was present. The USB ethernet on this Mac was down across that boot; Wi-Fi at `192.168.1.150` reached it afterward.

## The large Lua process

**VERIFIED.** The process that was about 17 MiB RSS is `lua /usr/bin/transformer` (pid 12928, VmRSS 17092 kB). That is the Homeware configuration service. It was left running. The other Lua programs (`ledfw`, `wansensing`, `hostmanager`, `cwmpevents`, and the rest) are a few megabytes each.

## What a reset actually keeps

**VERIFIED from the bank-1 copies of the scripts, and from the live `uci` value.**

`env.var.rtfds` is `0`. The reset button handler is therefore plain `rtfd`, not `rtfd --soft`.

- `20_rtfd_remove` deletes only the bank named by the symlink `/overlay/remove_due_to_rtfd`.
- `80_rtfd_restore` runs on every boot. If `/overlay/rtfd_persistent_files` and `/overlay/rtfd_persistent_filelist.conf` both exist, it copies each parked file (by basename) into `bank_<booted>` and then deletes the parking lot.
- `rtfd` with no flag only writes that symlink. It does not fill the parking lot. A lot that is already there is what comes back.
- `rtfd --soft` fills the lot from `/etc/rtfd_persistent_filelist.conf` at shutdown. The button does not use this while `rtfds` is `0`.
- `rtfd --all` deletes everything under `/overlay`, including the parking lot. Nothing installed here survives that.

## What was installed

**VERIFIED, same SSH, before the link dropped.**

The vendor file list at `/etc/rtfd_persistent_filelist.conf` was kept. These paths were appended: `shadow`, `passwd`, `shells`, the LAN dropbear config, `dhcp`, `genesis-persist`, the DoH init script, `dnsproxy.yaml`, the URL file, the dnsproxy binary, the bootstrap watcher, the `S99` link, and `firewall.user`. The URL itself was not printed and is not in this repo.

`/etc/init.d/genesis-persist` (`START=99`) is enabled. On start it stops and disables `cwmpd` and the two usage scripts, removes the LCM `S20pub_rgw_messages` link, kills the MQTT binaries if they are up, starts `doh-proxy` if dnsproxy is down, and re-seeds the parking lot. That re-seed matters because `80_rtfd_restore` deletes the lot after copying it.

The seed reported 25 files in `/overlay/rtfd_persistent_files`. `pidof cwmpd` was empty. `pidof dnsproxy` and both `hostapd` processes were still present.

## After the unplanned reboot

**VERIFIED, 21:49 CET, uptime 6 minutes.** SSH root answered. The parking lot was present again: the file list and 25 files. `80_rtfd_restore` had already turned `/etc/rc.d/S99genesis-persist` into a regular 1253-byte copy of the init script (timestamp 1970-01-01), which is what `cp` does with the parked symlink, and that copy had re-seeded the lot.

`cwmpd` was absent and its `rc.d` links were gone. Both usage processes were absent and their `rc.d` links were gone. `cloud-comm` was absent. `dnsproxy` was running, and `nslookup example.com 127.0.0.1` returned addresses. procd instance `doh-proxy` instance2 was `/usr/sbin/doh-bootstrap-watch`, pid 6623. Both `hostapd` processes were present.

`pub_rgw_daemon` (pid 18139) and `pub_rgw_messages` (pid 18146) were running. `S20pub_rgw_messages` was still the LCM symlink from 19:34. The copy of `genesis-persist` that was parked still calls the vendor `stop`, which does nothing when the pid file is missing. The rewrite that deletes `S20` never connected.

## What was not finished

- **No reset.** The parking lot has not been shown to restore SSH after a wiped bank. This boot did not delete the bank. It only showed that the lot is copied and then re-seeded.

## Undo

`/etc/init.d/genesis-persist disable` and delete that init script, then remove the appended lines from `/etc/rtfd_persistent_filelist.conf` and delete `/overlay/rtfd_persistent_files` plus `/overlay/rtfd_persistent_filelist.conf`. Bring CWMP back with `/etc/init.d/cwmpd enable` and `start`.
