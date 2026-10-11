# F1 case, UART, and capture status — 23.1.b

**Device:** Telia F1, board GCNT-X (EWA1330), FW `23.1.b.0448-7241017-20260223134332`
**Recorded:** 2026-10-11

## Firmware

The live **23.1.b** image is not on disk. The only firmware file is the offline 19.x reference (`artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`, sha256 `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de`). Unwrap failed: 57 OSCK trials, all `bad_osck`. LCM returned `Apps was not found` for GCNT-X 23.1.b and 23.1. Do not flash that 19.x RBI onto this unit.

## Case and header

The case is open. [Top-side overview of AP-BCM114-0001](board-top.png). `findings/serial-header.jpg` shows the UART connector **CN1**: four pins, silkscreen `3.3V GND TX RX`. The 16-pin header below it is **TEST_CN20**, a separate test connector.

A CP2102-class 3.3 V USB-serial adapter (parts note: Electrokit 41016396, USB-C to USB-A, male-female Dupont) is for a **boot log only**. No boot log has been captured yet.

## Decision

A CP2102 boot log does **not** root 23.1.b. On this board a serial log can show partitions and bank names. It is not a shell. Community notes on EWA1330 (hack-technicolor #321) say some units have no interactive serial console after boot. Reading `eripv2` / OSCK still needs a root shell, and 23.1.b has no confirmed root. See `findings/gcnt-x-root-path.md`.

## What the WAN capture showed

| File | Result |
| --- | --- |
| `wan.pcapng` | Not a capture. 335-byte HTML 404. |
| `wan2-real.pcapng` | 8,729 frames, 303 s. Mirror did not carry a firmware download. |
| `wan2.pcapng` | Earlier pktmon dump; not the verdict file. Tagged-frame note is on `wan2-real`. |

`wan2-real` verdict (`findings/mirror-test.md`, `findings/wan2-tagged-frames.md`):

- F1 MAC `a0:b5:3c:c6:62:82` is source on 12 frames and destination on 0. Those frames are ARP who-has `100.77.192.1` tell `100.77.230.213`, plus DHCP Discover/Request, hostname `Telia F1-CP2242AD8AN`. No Offer, no Ack, no TCP.
- 97% of IP frames are `192.168.0.0/24` (switch `TL-SG108E` at `192.168.0.1`). No DNS to 1.1.1.1, no TLS, no HTTP, no `.rbi`, no `teliasmartrgw`.
- Ethertypes `0x6466`, `0x6464`, and `0xa1e0` are bare IPv4/IPv6 from a Windows Tailscale host (DNS, empty TCP SYNs to port 53, SSDP), misread as Ethernet. `0x8899` is the TP-Link switch talking to itself. Stripping a VLAN-sized tag does not reveal an inner WAN frame.

No Telia firmware URL was in the capture.
