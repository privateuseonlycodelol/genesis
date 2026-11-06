# Bank diff and LAN listeners — 2026-11-06

Offline read of the decrypted squashfs trees. No packets were sent and the live router was not changed.

Images: `artifacts/firmware/flash-2026-11-06/rootfs1.squashfs` (running bank, 5 February 2026), `rootfs2.squashfs` (23 February 2026), and the unwrapped 19.x image `artifacts/firmware/rbi-19x-inner.bin` (squashfs at `0x1400000`).

## Bank 1 against bank 2

**VERIFIED:** 7,664 paths in bank 1, 7,671 in bank 2. Bank 1 has no path that bank 2 lacks. Bank 2 adds seven paths: `etc/telia_app_config/fsecure`, two L2Init wansensing scripts, `usr/share/transformer` F-Secure map and commit hook, an LXC init script, and `sense_5.1.0-dr1_vantiva-telia-f1x_armv8_64.ipk` (5,052,805 bytes).

Thirteen files change size. The rest of the "changed" list is only the group-write bit. `usr/sbin/hostapd`, `dropbear`, `nginx`, `cupsd`, and `miniupnpd-igdv1` are the same size in both banks.

Content that actually differs:

- `etc/config/dropbear`: bank 2 appends `10.10.99.0/24` to the WAN allowlist. That prefix is already on the mgmt instance in bank 1.
- `etc/config/env`: bank 2 drops `rebootdebug`.
- `etc/config/wansensing` plus new `L2Init` scripts: bank 2 adds an L2Init state.
- `etc/init.d/dnsmasq`: bank 2 adds a `dnsrule` helper that emits `--dns-filter`, and it calls `odhcpc` instead of `udhcpc`.
- `usr/bin/wancheck`: bank 2 removes the 60-minute WAN-down reboot and the route/ifconfig logger.
- `www/docroot/home.lp` and `www/lua/variant_helper.lua`: bank 2 drops the demo-build banner flag.

None of those deltas is a new listener.

## What the signed image exposes

**VERIFIED:** the 23.1.b userspace binaries are 32-bit ARM (`interpreter /lib/ld-linux.so.3`), stripped. The kernel is aarch64. The 19.x `hostapd` is aarch64 and also stripped, so it does not recover symbols for the running daemon.

**VERIFIED (nginx):** `etc/nginx/nginx.conf` listens on 80 and 443. The `location ^~ /` block runs session auth before the page. Exceptions that skip that block: `location = /` (internal redirect to `home.lp`), `/intercept.lp`, `/no-internet-connection-intercept.lp`, and `127.0.0.1:55555` (`/ra`, `/reloadWebUsers`). Port 8080 is a tproxy intercept that only redirects. The nginx binary's version string is `nginx/1.19.6`. The ELF is ARM, not the `x86_64` triple in that string.

**VERIFIED (dropbear, signed config):** three instances in `etc/config/dropbear`. `lan` is `enable 0` on port 60022. `mgmt` is port 22, `wan` is port 60022. Both have `PasswordAuth off` and `RootPasswordAuth off`, with an IP allowlist. The LAN SSH root that works today is the overlay, not this file.

**VERIFIED (other listeners):** `cupsd` strings identify CUPS 2.2.10. `hostapd` contains `wps_device.xml` and the WPS UPnP init failure string, which is the port 49152 service already probed live. `miniupnpd-igdv1` is the UPnP daemon. All four are stripped. 23.1 has no `wfa-testsuite-daemon`. The 19.x image does, plus `wireless_wfa_test_exec.sh`.

## Shell sinks that are not a LAN entry

**VERIFIED (code):** `usr/lib/lua/ethoam/libubus.lua` registers ubus object `ethoam` method `command` and passes `msg.command` to `os.execute`. `etc/init.d/ethoam` is `S50ethoam`. On reload it concatenates UCI fields (`meg`, `mepId`, `vlan`, `ifname`, and the rest) into a shell string and sends that string through the same method. `execute_command.lua` is `os.execute` of its first argument. `usr/share/acl.d/ubusd_acl.json` grants `lxc_telia` a list of methods that does not include `ethoam`. No file under `www/` mentions ethoam. The web `proxy.set` call sites that were read use fixed transformer paths, not a path taken from the request.

`rpc.system.tcpdump` writes a shell script, and it copies the interface only after a match against `tcpdump -D`. `setClashPassword.lua` quotes its arguments and is not referenced by a web page.

## Exec call sites

**VERIFIED (disassembly, bank 1).** `objdump -d` on the 32-bit listeners. Every `popen` / `execl` / `execlp` site resolves to a fixed program, not a string taken from a request.

| Binary | Call | Command |
| --- | --- | --- |
| `hostapd` | `popen` | `ovs-vsctl list-br` and `ovs-vsctl port-to-br %s`, mode `r` |
| `hostapd` | `execlp` | `ovs-vsctl` with argv `add-port` or `del-port` |
| `hostapd` | `execv` | splits one string on spaces, then execs it. Sits with the startup `fopen` / `srandom` code. No `/bin/sh` string in this binary |
| `miniupnpd-igdv1` | `popen` | `/usr/bin/upnp_wgclp` |
| `miniupnpd-igdv1` | `execl` | `/usr/bin/lua` `check_portmap_conflict.lua`. The script `tonumber`s the port and compares the protocol to UCI. It does not build a shell command |
| `cupsd` | `execlp` | one site, the filter child. CUPS 2.2.10 |

`hostapd` contains `../src/wps/wps_upnp.c` and the `WFADevice` SSDP strings. That is the port 49152 service. Those paths do not call `popen`.

**VERIFIED (19.x comparison).** `wfa-testsuite-daemon` is in the 19.x squashfs and not in bank 1 or bank 2. Its string is `if [ -f /usr/sbin/wireless_wfa_test_exec.sh ]; then /usr/sbin/wireless_wfa_test_exec.sh %s %s %s %s; fi`, and it listens on a TCP port for commands. The 19.x `hostapd` `/bin/sh` string is the xtask fatal-error path (`xtask.c`), and that binary is aarch64 and stripped, so it does not recover symbols for the 23.1 WPS parser.

**Not shown:** an unauthenticated LAN request that reaches `ethoam command`, or a live packet that exercises these call sites. The router was not changed.

**Superseded 2026-11-06:** the WPS-parser sentence above. Offline reading of this bank-1 `hostapd` found no pre-auth memory-corruption bug. See [f1-hostapd-wps-parser-2026-11-06.md](f1-hostapd-wps-parser-2026-11-06.md).
