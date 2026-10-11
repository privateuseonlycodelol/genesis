# Tagged-frame unwrap — `wan2-real.pcapng`

**File:** `artifacts/captures/wan2-real.pcapng` (read-only)
**Size:** 926,664 bytes
**SHA256:** `ecd14d04048cea2a3a853e829e6f0095a91ad20f8cd837da2f467584af516ba9`
**Frames:** 8,729 over 303.126 s (2026-10-11 17:27:26–17:32:29 CEST)
**Capture:** Packet Monitor on Windows 10 Pro, ASUS, one interface, encapsulation Ethernet
**Analyzed:** 2026-10-11

## Verdict

The frames behind ethertypes `0x8899`, `0x6466`, `0x6464`, and `0xa1e0` do not hide a WAN firmware download. `0x8899` is the switch talking to itself. The other three values are bare IPv4 and IPv6 from a Windows Tailscale host (DNS, empty TCP SYNs to port 53, SSDP). No TLS, no HTTP GET, no `telia` / `rbi` / `teliasmartrgw`, and neither `100.77.230.213` nor F1 MAC `a0:b5:3c:c6:62:82` occurs in those frames.

## Unwrap test

Treating the first 14 bytes as an Ethernet header and stripping N bytes after it, then reading the next two bytes as an inner ethertype:

| N bytes stripped | Frames whose inner type is `0x0800`, `0x0806`, or `0x86dd` |
| ---: | ---: |
| 4 | 0 |
| 6 | 0 |
| 8 | 0 |
| 16 | 0 |
| 0, 2, 10, 12, 14, 18, 20, 24, 32 | 0 |

Shifting the whole frame so a real ethertype would land at offset 12 also fails. Offsets 9 and 25 hit `0x0800` in 22 and 6 frames. That is scattered payload noise, not one tag length.

## What the bytes are

Packet Monitor stored IP-layer packets in an Ethernet pcapng. tshark reads the first 14 bytes as destination MAC, source MAC, and ethertype. On a real IPv4 header those two ethertype bytes are the first two octets of the source address. On IPv6 they fall inside the source address.

| Apparent ethertype | Frames | Actual contents |
| --- | ---: | --- |
| `0x6466` | 4,946 | IPv4 from `100.102.162.13` (`100.102` = `0x6466`) |
| `0xa1e0` | 1,788 | IPv6 from `fd7a:115c:a1e0::/48` (Tailscale ULA; `a1e0` is bytes 12–13) |
| `0x8899` | 1,764 | Realtek switch frames, TP-Link `ec:75:0c:46:d5:4c` → broadcast |
| `0x0800` | 189 | Already Ethernet. DHCP only |
| `0x6464` | 36 | IPv4 from `100.100.100.100` (Tailscale DNS) |
| `0x0806` | 6 | Already Ethernet. F1 ARP |

`4,946 + 1,788 + 1,764 + 189 + 36 + 6 = 8,729`.

Every bare IPv4 frame has a valid header checksum (4,982/4,982) and `total length` equal to the captured length. Every bare IPv6 frame has `40 + payload length` equal to the captured length (1,788/1,788). There is no extra tag before or after the IP packet.

## Recovered counts

Re-parsed the 6,770 bare-IP frames (`0x6466`, `0x6464`, `0xa1e0`) as raw IP:

| Protocol | Frames |
| --- | ---: |
| IPv4 | 4,982 |
| IPv6 | 1,788 |
| TCP | 2,624 |
| UDP | 4,102 |
| DNS | 4,006 |
| TLS | 0 |
| HTTP | 0 |

TCP is one flow: `100.102.162.13 → 192.168.1.4:53`, SYN only, payload length 0. No SYN-ACK, no ClientHello.

UDP is DNS (port 53), SSDP (port 1900, 88 frames), and mDNS (port 5353, 8 frames). ICMPv6 neighbor discovery is 44 frames (`fd7a:115c:a1e0::ac01:a20d` ↔ `fd7a:115c:a1e0::53`).

DNS is 3,970 queries and 36 responses. The only answers are NXDOMAIN (`rcode` 3) for `wpad.tailc8804.ts.net` from `100.100.100.100`. Query destinations: `100.100.100.100` (1,352), `192.168.1.4` (878), and IPv6 `fd7a:115c:a1e0::53`.

SSDP is `M-SEARCH` from `100.102.162.13` to `239.255.255.250:1900`. User-agents: `Chromium/151.0.7922.138 Windows`, `Chromium/128.0.6613.138 Windows`, `Chromium/126.0.6478.183 Windows` (24 each). The `Host` header is only `239.255.255.250:1900`. tshark’s HTTP dissector does not claim these.

### DNS query names

| Queries | Name |
| ---: | --- |
| 556 | `settings-win.data.microsoft.com` |
| 396 | `clientstream.launchdarkly.com` |
| 360 | `api.epicgames.dev` |
| 244 | `log.tailscale.com` |
| 180 | `datarouter.ol.epicgames.com` |
| 162 | `api.steampowered.com` |
| 144 | `polka.typekit.com` |
| 144 | `msedge.api.cdp.microsoft.com` |
| 144 | `gew4-spclient.spotify.com` |
| 144 | `assets.adobedtm.com` |
| 112 | `cmp1-sto1.steamserver.net` |
| 108 | `steamconnecttest.com` |
| 108 | `config.edge.skype.com` |
| 108 | `catalog.gamepass.com` |
| 80 | `aepxlg.adobe.com` |
| 76 | `cmp2-sto2.steamserver.net` |
| 76 | `cmp1-fra1.steamserver.net` |
| 72 | `optimizationguide-pa.googleapis.com` |
| 72 | `g.api.mega.co.nz` |
| 72 | `events.launchdarkly.com` |
| 72 | `cs.dds.microsoft.com` |
| 72 | `cmp1-sto2.steamserver.net` |
| 72 | `cam-analytics.nzxt.com` |
| 36 | `wpad.tailc8804.ts.net` |
| 36 | `o1383653.ingest.us.sentry.io` |
| 36 | `ext2-par1.steamserver.net` |
| 36 | `ecs.office.com` |
| 36 | `dsadata.intel.com` |
| 36 | `dns.msftncsi.com` |
| 36 | `disabled.invalid` |
| 36 | `datarouter-prod.ak.epicgames.com` |
| 36 | `cmp2-ams1.steamserver.net` |
| 36 | `cmp1-fra2.steamserver.net` |
| 18 | `ext1-par1.steamserver.net` |
| 18 | `cmp1-ord1.steamserver.net` |
| 8 | `_spotify-social-listening._tcp.local` |

No query name contains `telia`, `rbi`, `smartrgw`, `firmware`, `vantiva`, or `technicolor`.

## String search (recovered frames only)

Case-insensitive ASCII search of the 6,770 bare-IP frames (469,856 bytes):

| Needle | Hits |
| --- | ---: |
| `telia` | 0 |
| `rbi` / `.rbi` | 0 |
| `teliasmartrgw` / `smartrgw` | 0 |
| `firmware` | 0 |
| `http://` / `https://` / `GET /` | 0 |
| `100.77.230.213` (text and `64 4d e6 d5`) | 0 |
| F1 MAC `a0:b5:3c:c6:62:82` | 0 |

`Host:` occurs 88 times, all of them the SSDP host above. `user-agent` occurs 72 times, all Chromium SSDP.

## `0x8899` switch frames

1,764 frames, every one 60 bytes, `ec:75:0c:46:d5:4c` → `ff:ff:ff:ff:ff:ff`, ethertype `0x8899`. Two payloads, 855 and 909 copies. They differ by one byte (`ff 01` vs `ff 02`) after the switch MAC is repeated. The four bytes after `0x8899` are `25 00 00 00`, then the same TP-Link MAC. Nothing after that is an inner ethertype.

## F1 on the frames that were already Ethernet

These were not part of the unwrap. They are the only place the F1 shows up:

| Frames | What |
| ---: | --- |
| 6 | ARP who-has `100.77.192.1` tell `100.77.230.213`, source MAC `a0:b5:3c:c6:62:82`, destination broadcast |
| 6 | DHCP Discover/Request, hostname `Telia F1-CP2242AD8AN`, `0.0.0.0` → `255.255.255.255` |
| 183 | SG108E DHCP, hostname `TL-SG108E`, `192.168.0.1` → broadcast |

F1 as Ethernet destination: 0. The address `100.77.230.213` is only inside those ARP/DHCP frames, not inside the bare IP.
