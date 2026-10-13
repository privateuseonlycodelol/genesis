# F1 case, UART, and capture status — 23.1.b

**Device:** Telia F1, board GCNT-X (EWA1330), FW `23.1.b.0448-7241017-20260223134332`
**Recorded:** 2026-10-11

**2026-10-12 superseding evidence:** an owner-supplied **86,162-byte** UART log is now inspected: [detailed boot finding](f1-boot-log-2026-10-12.md), [redacted line-indexed appendix](f1-boot-log-2026-10-12-evidence.md). It starts with BTRM markers and reaches SPL/TPL/U-Boot, **AArch64 Linux 4.19.235**, Bank 2, encrypted/verity-backed UBI root and userspace. BOOT-P/Enter invitations and JTAG-unlock warning are observed; no interactive shell, root or usable key recovery is established. The literal firmware build is absent from the log; association with the owner's 23.1.b unit comes from the supplied-file context and earlier UI evidence. Historical no-log statements below describe the earlier pass.

**2026-10-12 live-interaction update:** the owner then tested UART input using macOS Screen and a fresh growing capture. Lowercase `b` at the U-Boot invitation entered BOOT-P. Early attempts had **no Ethernet** (`no active_port set`); a later capture had **link up** but **BOOTP Reply timeout** without a server. Return, `id` + Return, and Ctrl+J at the Linux invitation did not produce shell/login/UID output. **2026-10-13:** Windows PC on router LAN — pktmon + Wireshark verified BOOTREQUESTs with boot file **`GCNT-X`** ([BOOT-P LAN](f1-bootp-lan-2026-10-13.md)). **2026-10-12 logviewer:** tty `restricted_shell` and Clash serial denial — [interaction finding](f1-uart-interaction-2026-10-12.md). Status hub: [research composite](f1-research-composite-2026-10-13.md).

## Firmware

The live **23.1.b** image is not on disk. The only firmware file is the offline 19.x reference (`artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`, sha256 `2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de`). Unwrap failed: **71** unique OSCK trials (latest [rbi-crypto-attempt3.md](rbi-crypto-attempt3.md)), all `bad_osck`. LCM returned `Apps was not found` for GCNT-X 23.1.b and 23.1. Do not flash that 19.x RBI onto this unit.

**Public boot log (not this unit):** GCNT-X **19.4.0856** UART capture ([pastebin biRghtLr](https://pastebin.com/raw/biRghtLr), quoted in [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md)) — MTD map, **aarch64 Linux 4.1.52**, `.r2secr=0x17fdf000`, `OSCK Loaded!` without key bytes. Does not decrypt the sealed RBI offline.

## Case and UART pads

The case is open. [Top-side overview of AP-BCM114-0001](board-top.jpg). Owner **2026-10-12** photo survey (REV **1.0**, `JP1`, `CN33`, `TEST_CN20`): [f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md). `findings/serial-header.jpg` shows the UART site **CN1**: four **through-holes** on the PCB (silkscreen `3.3V GND TX RX`), not a factory-installed pin header you can clip a Dupont lead onto. Make electrical contact by soldering wires or a short header into those holes; the CP2102 adapter’s Dupont pins mate on the **adapter** side of that harness. The 16-pin **TEST_CN20** site below is a separate test connector.

A CP2102-class 3.3 V USB-serial adapter (parts note: Electrokit 41016396, USB-C to USB-A, male-female Dupont for the adapter end) is for a **boot log only**. **At the 2026-10-11 pass, no owned-unit UART log was available.** Superseded by the supplied capture reviewed above; the public **19.4.0856** log remains a different device/build.

## Decision

### Capture helper — 2026-10-12

**REPORTED at helper-creation time:** owner connected TX/GND and saw boot output. No new unit log had then been supplied for inspection. The subsequently supplied file is now documented in [f1-boot-log-2026-10-12.md](f1-boot-log-2026-10-12.md).

**VERIFIED (supplied terminal output):** macOS Screen identifies itself as 4.00.03 and rejects `-Logfile` before starting the serial session. `scripts/f1-boot-capture.command` instead supplies `logfile` and `logfile flush 1` via a temporary configuration file, with `-L -fn`, default port `/dev/cu.usbserial-0001`, and 115200 baud. Run `bash scripts/f1-boot-capture.command`; optional first argument selects another port. Logs stay on the owner's Desktop, outside Git. Router TX connects to adapter RX, with shared GND and no 3.3V connection.

Validation at helper-creation time: Bash syntax, help, and nonexistent-port handling checked locally. **Superseded for capture/input status:** a later Screen 4.00.03 run from the visible macOS Terminal produced a growing owned-unit capture and captured Linux input text; see [live interaction finding](f1-uart-interaction-2026-10-12.md). A shell/root is still not shown.

A CP2102 boot log does **not** root 23.1.b. Community notes on EWA1330 (hack-technicolor #321) report some units without an interactive serial console, but this capture's Enter invitation still needs an input test. No root is confirmed. **Module correction:** `tools/secr/r2secr.arm64.4.1.52.ko` belongs to the public 19.4 reference; the new **4.19.235** capture yields `no_module_match`. `scripts/acquire_f1_config_key.sh` also has an old raw-MTD default, unvalidated for this UBI layout. Do not transfer those defaults to this unit; see [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md) and the detailed finding.

## What the WAN capture showed

| File | Result |
| --- | --- |
| `wan.pcapng` | Not a capture. 335-byte HTML 404. |
| `wan2-real.pcapng` | 8,729 frames, 303 s. Mirror did not carry a firmware download. |
| `wan2.pcapng` | Earlier pktmon dump; not the verdict file. Tagged-frame note is on `wan2-real`. |

`wan2-real` verdict (`findings/mirror-test.md`, `findings/wan2-tagged-frames.md`):

- F1 WAN MAC (redacted) is source on 12 frames and destination on 0. Those frames are ARP who-has on the CGNAT gateway (100.64.0.0/10, addresses redacted), plus DHCP Discover/Request, hostname `Telia F1` (serial suffix redacted). No Offer, no Ack, no TCP.
- 97% of IP frames are `192.168.0.0/24` (switch `TL-SG108E` at `192.168.0.1`). No DNS to 1.1.1.1, no TLS, no HTTP, no `.rbi`, no `teliasmartrgw`.
- Ethertypes `0x6466`, `0x6464`, and `0xa1e0` are bare IPv4/IPv6 from a Windows Tailscale host (DNS, empty TCP SYNs to port 53, SSDP), misread as Ethernet. `0x8899` is the TP-Link switch talking to itself. Stripping a VLAN-sized tag does not reveal an inner WAN frame.

No Telia firmware URL was in the capture.
