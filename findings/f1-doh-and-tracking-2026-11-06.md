# F1 DNS-over-HTTPS and phone-home — 2026-11-06

Live bank 1, overlay upperdir `/overlay/bank_1`. No flash, no bootfs write, no factory reset. Userspace ELF is 32-bit ARM (`EM_ARM`, `/lib/ld-linux.so.3`, glibc 2.32). The kernel is aarch64. dnsmasq is **2.85** with `no-cryptohash` and no DoH. `/rom` and the overlay have no `https-dns-proxy`, stubby, dnscrypt-proxy, or cloudflared.

## Checked before the rilah switch

**VERIFIED, 2026-11-06 21:06 CET.** The Cloudflare forwarder from earlier that day was still intact. An aborted attempt had not half-changed the box.

- dnsmasq was running (`/usr/sbin/dnsmasq`, pids 19969 and 19979).
- `nslookup example.com 127.0.0.1` on the router returned A `104.20.23.154` and `172.66.147.243`, plus AAAA `2606:4700:10::6814:179a` and `2606:4700:10::ac42:93f3`. From the Mac, `dig example.com @192.168.1.1` returned the same two A records.
- The DoH process was `/usr/bin/lua /usr/sbin/doh-proxy.lua`. Its upstream hosts were Cloudflare `1.1.1.1` and `1.0.0.1`. It held one ESTABLISHED TCP session to `1.1.1.1:443`. dnsmasq was `noresolv=1`, `localuse=1`, `server=127.0.0.1#5053`. The `br-lan` IPv4 port-53 REDIRECT and the IPv6 FORWARD REJECT rules were present.

That path was answering, so it was left in place until the rilah forwarder had already answered a query on a spare port.

## DoH now in place

**VERIFIED, later the same evening.** dnsmasq still forwards only to `127.0.0.1#5053`. The process there is AdGuard dnsproxy **v0.86.0**, a static linux/arm EABI5 binary at `/usr/sbin/dnsproxy` (sha256 `c575a5d307bbc1f92834d1929542ebcfbcc23af8f7541fa5276642482b225c7c`, about 13–14 MiB RSS). The Lua Cloudflare script is now a stub that exits, and it is not running.

The upstream is DoH to hostname `dns.rilah.app`, with no port on that name. The URL is only in `/etc/doh-rilah.url` (mode `0600`, and the same mode on the overlay copy). It is not in this repo. `/etc/dnsproxy.yaml` points at that file as the single upstream and does not contain the URL. dnsproxy's logs go to `/dev/null`. Its command line is `/usr/sbin/dnsproxy --config-path=/etc/dnsproxy.yaml --output=/dev/null`.

Bootstrap for the upstream and the fallback is `9.9.9.9:53`, not the router's own resolver. At the check, `dig dns.rilah.app @9.9.9.9` returned A `78.68.184.190`, TTL 300, and no AAAA. That address is not configured on the router. Fallback, only when the primary is unavailable, is `https://dns.quad9.net/dns-query`. It is not load-balanced with the primary. `--http3` and `--edns` are off. Cache is on, including optimistic serve-stale (expired answers TTL 30s, kept up to 12h, 1 MiB). dnsmasq has no `add-subnet`. A reply captured from the Mac carried an OPT with EDNS version 0 and UDP payload 1280, and no client-subnet field.

LAN IPv4 port 53 arriving on `br-lan` is still REDIRECTed to local port 53. This kernel has no `ip6tables` nat table, so IPv6 port 53 forwarded from `br-lan` is still REJECTed (`icmp6-port-unreachable`). Queries to the router itself are INPUT and still reach dnsmasq. DHCP was not changed. `br-guest` was not added.

`/etc/init.d/doh-proxy` (`S18doh-proxy`) starts dnsproxy and `/usr/sbin/doh-bootstrap-watch` under procd. The binary, both scripts, the yaml, and the URL file are in overlay upperdir `/overlay/bank_1`, so a normal reboot starts them. A later firmware flash that wipes that bank removes them. This pass did not reboot.

### Bootstrap refresh

**DERIVED from the v0.86.0 DoH client, and VERIFIED that the watcher is installed.** dnsproxy resolves the upstream when it creates its HTTP client, and again after a failed exchange throws that client away. It does not re-query on the 300s TTL while the connection stays up. The watcher asks `9.9.9.9` for `dns.rilah.app` after 20 seconds and then about every 300 seconds. If the address set changes, it kills dnsproxy; procd starts it again and the new process resolves the new address. If `example.com` through `127.0.0.1` has failed for about a minute (three checks of 20 seconds, after an 80 second grace), it does that restart and then waits about five minutes before another failure restart. An unchanged address with a healthy connection is left up.

### After the switch

**VERIFIED.** `nslookup example.com 127.0.0.1` and `dig example.com @192.168.1.1` both returned A `104.20.23.154` and `172.66.147.243`. The Mac also got the two AAAA answers above. Three queries reused one TCP session, source port 49710, to `78.68.184.190:443`. Later lookups still showed a single established session to that address. The source port changed between bursts; the process pid stayed 18512. dnsproxy was not connected to `1.1.1.1:443`, `9.9.9.9:443`, or `149.112.112.112:443` during those checks.

`doubleclick.net`, `ad.doubleclick.net`, `www.google-analytics.com`, and `ads.yahoo.com` each came back NOERROR with an empty answer from both the router and `9.9.9.9`. That is not a Pi-hole `0.0.0.0` against a public address. Inconclusive.

This binary's DoH client forces HTTP/2 and does not open HTTP/3 unless `--http3` is set. It was not set. The TLS ALPN bytes were not captured. Serve-stale is configured and was not shown by taking the upstream down. This build allows up to two connections per host; the checks above saw one.

Repo copies, with no URL in them: `scripts/f1_dnsproxy.yaml`, `scripts/f1_doh_bootstrap_watch.sh`, `scripts/f1_doh_proxy.init`. The earlier Lua forwarder is not kept in the repo. On the router it is a stub that exits.

### What this does not cover

Clients that speak DNS-over-HTTPS or DNS-over-TLS themselves (port 443 or 853) are not forced through this proxy. IPv6 clients with a hardcoded resolver are rejected, not answered. Guest Wi-Fi was not intercepted.

### Undo

Stop the proxy and send dnsmasq back to the resolvers it used before the overlay. The rilah URL is not part of this.

```sh
/etc/init.d/doh-proxy stop
/etc/init.d/doh-proxy disable
uci -q del_list dhcp.dnsmasq.server='127.0.0.1#5053'
uci -q delete dhcp.dnsmasq.noresolv
uci -q delete dhcp.dnsmasq.localuse
uci commit dhcp
/etc/init.d/dnsmasq restart
rm -f /usr/sbin/dnsproxy /usr/sbin/doh-bootstrap-watch /usr/sbin/doh-proxy.lua \
      /etc/dnsproxy.yaml /etc/doh-rilah.url /etc/init.d/doh-proxy
```

Delete the `# genesis-doh-begin` … `# genesis-doh-end` block in `/etc/firewall.user`, then:

```sh
iptables -t nat -D PREROUTING -i br-lan -p udp --dport 53 -j REDIRECT --to-ports 53
iptables -t nat -D PREROUTING -i br-lan -p tcp --dport 53 -j REDIRECT --to-ports 53
ip6tables -D FORWARD -i br-lan -p udp --dport 53 -j REJECT
ip6tables -D FORWARD -i br-lan -p tcp --dport 53 -j REJECT
```

Before any of this DoH work, dnsmasq used the WAN resolvers in `/tmp/resolv.conf.d/resolv.conf.auto`: `82.209.169.71`, `82.209.169.72`, `2a00:1598:53:1::2`, `2a00:1598:53:4::2`. Removing `noresolv` returns it to that file.

## Phone-home inventory

| Component | What it contacts | Change |
| --- | --- | --- |
| Airties `cloud-comm` | UCI auth host `device-auth-teliaprod.telia.airtiescloud.eu`. Live TLS to CloudFront (`2600:9000::`) and AWS (`2a05:d018::`). Signed Domos URLs include `licence.domos.io`, `update.domos.io`, and an Azure websocket host. | **Disabled the cloud switch.** `mesh_broker.AT_common.cloud_comm` set from `1` to `0`, committed in the overlay, then `ubus call mesh_broker.config reload`. Eight seconds later `cloud-comm` had no ESTABLISHED socket. hostapd on wl0 and wl1 stayed up. The process is still running, idle. `AT_logging.cloud_comm=2` is a log level and was left. `air-dpi` and `air-domosd` still run and had no own TCP session in this check. |
| TR-157 bulk data | Init is enabled. Profile 1 was already off, with placeholder `http://abc.com`. No bulkdata process. | **`bulkdata.global.enabled` set to `0`.** Reversible with `uci set bulkdata.global.enabled='1'; uci commit bulkdata`. |
| `cwmpd` | `https://rgw.teliacompany.com:7575/ACS-server/ACS`, periodic inform on. | **Stopped later the same evening.** `pidof cwmpd` was empty after `/etc/init.d/cwmpd stop` and `disable`. Not checked after a reboot. See [reset parking lot](f1-reset-persistence-2026-11-06.md). |
| `pub_rgw_messages` | MQTTS `mqtt.teliasmartrgw.com:8883` (AWS `eu-north-1`). Init lives in the LCM upper, `/opt/lcm.technicolor.com/upper/etc/init.d/pub_rgw_messages`. | **Stopped, 22:28 CET.** The vendor `stop` does nothing without a pid file. The LCM `S20pub_rgw_messages` link was removed and both binaries were killed. They were still absent a few seconds later. `dnsproxy` and both `hostapd` processes stayed up, and `example.com` resolved. |
| Crash upload | `system.@coredump[0].action` and `system.@kernel_crash[0].action` are both `compress`. The URL `https://telia-core.tgwfd.org:5443/` is configured, and `core-handler` uploads only when the action is `upload`. `debug_monitor` is running on `/etc/telia_app_config`. | **Left.** The live action does not upload. |
| `obuspa_retriever.sh` | Cron every minute. The ROM script only caches the local USP data model. The overlay copy also writes a local syslog tag. No HTTP client in the script. `obuspa.daemon_config.enable` is `0`. | **Left.** Not an outbound tracker. |
| `wansensing.lua` | WAN state machine. The periodic "Check Debug Interface" line is local. | **Left.** Stopping it risks the WAN link. |
| `trafficmon-ubus` | Writes interface counters to the local syslog. | **Left.** |
| F-Secure / sense ipk | Present only in bank 2, which is not the running bank. No process. | Nothing to stop. |
| `dnsfilterd` | Would NFQUEUE port 53 only when parental mode is `dns` and enable is `1`. Live enable is `0`. | **Left.** It is not intercepting. |
| NTP | `ntp-cust1.telia.com`, `ntp-cust2.telia.com`. | **Left.** Time sync. |
| miniupnpd | LAN UPnP. | **Left.** Not telemetry. |

Airties cloud can be turned back on with:

```sh
uci set mesh_broker.AT_common.cloud_comm='1'
uci commit mesh_broker
ubus call mesh_broker.config reload
```

## Not shown

No client-side DoH bypass test, no reboot, no ALPN capture, and no deliberate upstream outage to prove serve-stale. No proof that `air-dpi` never opens a socket. SSH was still up at the end of the pass.
