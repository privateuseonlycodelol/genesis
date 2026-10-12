# Public GCNT-X hardware facts

Read 12 October 2026 from public pages. No router was contacted. This is a **19.4.0856** serial log linked from [hack-technicolor #321](https://github.com/hack-technicolor/hack-technicolor/issues/321), not a capture from the live Telia F1 on `23.1.b.0448-7241017`.

Source log: https://pastebin.com/raw/biRghtLr (PuTTY header `2024.02.22 18:25:13`). Issue 321’s opening post lists that URL under firmware `19.4.0856`.

## Verified in that log

**REPORTED** (quoted from the fetched paste; not reproduced on this unit):

- `CPU : BCM68360_B1` on the same banner as `Board Mnemonic : GCNT-X`, `RAM : 512MB`, `Flash : 501MB NAND`.
- Later: `License chip name: 68360`.
- `SW Version : 19.4.0856-4581009-20221122120420-...` before `Starting the Linux kernel`.
- NAND geometry: `chipSize=512 MB, blockSize=256K` and `pageSize=4096B`, then `writesize=4096`.
- Identity stops at `BrcmNAND mfg 0 0 UNKNOWN NAND CHIP 512MB on CS0` and `flashId=98dc9026`. No catalog part number.
- `Creating 1 MTD partitions` then `0x0000167c0000-0x000018fc0000 : "rootfs"`, then `Creating 6 MTD partitions`:

| Name | Range printed in the log |
| --- | --- |
| `ubi` | `0x0000001c0000-0x0000117c0000` |
| `bank_1` | `0x0000117c0000-0x0000153c0000` |
| `bank_2` | `0x0000153c0000-0x000018fc0000` |
| `eripv2` | `0x000000100000-0x000000140000` |
| `rawstorage` | `0x000000140000-0x0000001c0000` |
| `opt` | `0x000018fc0000-0x00001f3c0000` |

- `*** Press b to enter BOOT-P ***`, then `Booting : Bank 2`, then `DeviceTree loaded`.
- `Please press Enter to activate this console.` The capture continues with kernel lines and does not show a shell prompt after that line.
- Wi-Fi context only: reserved memory for `dhd0` and `dhd1`, country maps for `wl0` (2.4 GHz) and `wl1` (5 GHz), `Release Version 5.02L.07p1`. No `BCMxxxxx` radio part and no PCI ID.
- Ethernet PHY, not Wi-Fi: `RTL8226 PHY initialize successfully` and `RTL8226B`.

**DERIVED** from those addresses, and checked against the same log:

- `rootfs` starts `0x01400000` into `bank_2` and ends at the same address as `bank_2`. The kernel command line prints `rootfs_offset=0x01400000` and `root=/dev/mtdblock1`. It is a view of the booted bank, not a seventh physical partition.
- Each bank span is `0x03c00000` (60 MiB). The log later prints `ubi0: attached mtd2 (name "ubi", size 278 MiB)`, which matches the `ubi` span rounded down to a whole mebibyte.
- The live 23.1.b UI reported `banksize` `134217728` (128 MiB) in `findings/software-pass-live-access.md`. That number does not match these 60 MiB banks. This map is not a 23.1.b partition map.

The log also prints `eRIPv2 secrets passed correctly to Linux` and `OSCK Loaded!`. Those are status strings. No key bytes are in this note.

## Reported in issue 321, not in the paste

**REPORTED** by the NI-Pro comment of 4 September 2026, as quoted text inside the issue, not as a second log fetched here:

- Holding `a` at power-on prints `CFE-ROM WAS ABORTED` and `Please choose one of the following options:` with `c` (continue) and `s` (DDR safe mode).
- The same comment says the CFE shell is cut out, and quotes logviewer lines `[Restricted_Shell] User is connecting through tty...` and `[Lua] [Clash-access-control] User root has no serial access`.
- `23.1.b.0448-7241004 (.rbi not found)` and `23.1.b.0448-7241016 (.rbi not found)`.

An earlier comment asks for OpenWrt and posts PCB photos. That is a request, not a device target, DTS, or install report.

## Still not stated

NAND catalog part, Wi-Fi radio part, a GPL tarball or board file for EWA1330 / EWA1330TCS / GCNT-X, a public 23.1.b RBI URL, a TEST_CN20 pinout, and an OpenWrt board target. The Vantiva EWA1330TCS 19.4 file already noted in `findings/f1-api-map.md` is a module report, not a source tree. Detail of the searches that returned nothing is in `docs/gcnt-x-web-gaps.md`.

The flash ID is not a part number. The next hardware fact that this public log cannot supply is the NAND catalog part on AP-BCM114-0001.
