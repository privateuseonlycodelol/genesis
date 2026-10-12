# WAN mirror capture — `want.pcapng`

**File:** `artifacts/captures/want.pcapng`  
**Size:** 5,347,036 bytes (5.1 MB)  
**Packets:** 49,846 frames, 3,666,122 bytes on the wire  
**Span:** 2026-10-11 06:40:12–06:44:39 +0200 (266.7 s)  
**Capture note:** SG108E port mirror of the Telia F1 WAN. Not committed.

## Verdict

This is not F1 WAN traffic. It is LAN traffic from an ASUS PC, plus the switch.

39,232 of 39,480 IP frames come from `192.168.0.10` (`04:92:26:bd:cf:ea`, ASUSTek). That host sends Microsoft NCSI and Tailscale DNS queries, STUN binding requests, TCP SYNs, SSDP, and NAT-PMP. Nothing comes back: 0 DNS responses, 0 SYN-ACKs, no TLS ClientHello, no HTTP request to a real server.

The SG108E (`ec:75:0c:46:d5:4c`, TP-Link, DHCP name `TL-SG108E`) answers ARP for `192.168.0.1`, and that MAC is the Ethernet destination for the ASUS host. The switch is where this traffic stops.

The Telia F1 (WAN MAC redacted, Vantiva, DHCP name `Telia F1` with serial suffix redacted) appears only as 24 DHCP Discovers from `0.0.0.0` and 4 ARP requests. No public WAN address, no ISP DHCP offer, no download.

This Mac is on the F1 LAN (`192.168.2.0/24`, host address redacted). Its MAC is not the ASUS source. The SSDP user-agent is Chromium on Windows, so `192.168.0.10` is another PC on the switch, not this capture machine and not the router’s WAN session.

## Protocol hierarchy

| Layer | Frames |
| --- | ---: |
| frame / eth | 49,846 |
| IPv4 | 39,480 |
| TCP | 17,828 |
| UDP | 17,004 |
| ICMP | 4,592 |
| STUN (UDP/3478 binding requests) | 13,776 |
| SSDP | 956 |
| DNS | 704 |
| NAT-PMP (UDP/5351) | 324 |
| DHCP | 240 |
| portcontrol | 164 |
| IGMP | 56 |
| mDNS | 8 |
| ARP | 408 |
| Realtek `0x8899` (switch) | 1,512 |
| other non-IP (`0x6466`, `0xa1e0`, `0x6464`) | 8,446 |

Every TCP segment is a SYN with length 0: 17,768 to port 443 and 60 to port 80.

## Hosts

TLS SNI: none.

HTTP host: `239.255.255.250:1900` only (SSDP `M-SEARCH *`). User-agents on some of those searches: `Chromium/146.0.7680.179 Windows`, `Chromium/126.0.6478.183 Windows`.

DNS query names (no answers):

| Queries | Name |
| ---: | --- |
| 192 | `www.msftconnecttest.com` |
| 144 | `wpad.tailc8804.ts.net` |
| 128 | `controlplane.tailscale.com` |
| 96 | `www.msftncsi.com` |
| 96 | `log.tailscale.com` |
| 48 | `dns.msftncsi.com` |
| 8 | `_spotify-social-listening._tcp.local` |

Resolvers queried: `100.100.100.100` (480) and `1.1.1.1` (224). No response packets.

Other addresses, not firmware hosts:

- `192.168.0.1` — SG108E management; 216 DHCP Requests
- `10.100.100.90` — Nokia `50:e0:ef:32:84:80`; 8 IGMP reports to `224.0.0.1`
- STUN to 121 destination IPs, all binding requests, no names

## Firmware URLs

None.

No `.rbi` URL. No frame contains `.rbi`, `smartrgw`, `teliacompany`, or `firmware`. The only `telia` match is the DHCP hostname `Telia F1` (serial suffix redacted; 24 Discover packets). The only HTTP URI is SSDP `*`.
