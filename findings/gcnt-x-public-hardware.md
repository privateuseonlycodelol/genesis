# Public GCNT-X hardware facts

Read 12 October 2026 from public pages. No router was contacted. This is a **19.4.0856** serial log linked from [hack-technicolor #321](https://github.com/hack-technicolor/hack-technicolor/issues/321), not a capture from the live Telia F1 on `23.1.b.0448-7241017`.

**Later owned-unit comparison:** [the supplied 2026-10-12 capture](f1-boot-log-2026-10-12.md) now reports **4.19.235**, U-Boot 2019.07, UBI/verity/AES-XTS root, Toshiba `TC58NVG2S0H` driver identification and a `43684b0` radio-firmware path. It supersedes hardware/kernel unknowns for that new evidence source; the 4.1.52/60 MiB-bank map and unknown chip identification below remain scoped to this older public log. Neither driver text nor firmware pathname independently verifies physical chip markings.

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

The log also prints `eRIPv2 secrets passed correctly to Linux`, `OSCK Loaded!`, and `Client Private Key Loaded!`. Those are status strings. No key bytes are in the paste.

## What the same log adds for the sealed 19.4 RBI

The local file `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` is **19.4.0507-4581025**. This paste is **19.4.0856-4581009** (`SW Version : 19.4.0856-4581009-20221122120420-5bde4b5646ee7061e320c605e10e3aaa98af4706`). Same board and variant (`Board Mnemonic : GCNT-X`, `Variant ID : TL`, `Market ID : FFA0`). Not the same image, and not the live `23.1.b` unit.

**REPORTED** from the paste, and checked against the local RBI header:

- Kernel banner: `Linux version 4.1.52 (repowrt-builder@eb570e1caf5d) (gcc version 5.3.0 (Buildroot 2016.02) ) #0 SMP PREEMPT Fri Jan 28 10:29:17 2022`, then `CPU: AArch64 Processor [420f1000]`. This is a 64-bit 4.1.52 kernel. It is not the ARMv7 `4.1.52 … p2v8` string reported for other Technicolor boards.
- Command line includes `root=/dev/mtdblock1 rootfstype=squashfs rootfs_offset=0x01400000 board=GCNT-X platform.prozone_addr=0x17fe0000 .r2secr=0x17fdf000`, plus bootloader `bl_version=21.05.1395-0000000-20210205075431-c82c4f289bbd35e048aab42640d9d284a37e3ae9` and `bl_oid=601cfafcb8ce8a06f90081d9`. Later: `Prozone base: 0000000017fe0000`.
- Before Linux: `Boot Loader Version : 21.05.1395-…`, `Decompression LZ4 image OK!`, `Code Address: 0x00080000`. Early ROM banner ends `PASS`. `*** Press b to enter BOOT-P ***` is followed by `Booting : Bank 2`.
- `parse_btab: num_banks (6)` is printed, then the two named banks in the table above. The log does not define six full firmware banks.
- Root mounts `squashfs` readonly, then UBIFS volume `rootfs_data` as the overlay. Named early scripts: `/lib/mount_root/00_rtfd_all`, `10_remove_due_to_upgrade`, `18_ispconfig_save`, `20_rtfd_remove`, `30_parameter_conversion`, `80_rtfd_restore`, `82_ispconfig_restore`. Later: four `Hostapd starting` lines, `/bin/smd`, CMS `ssk` in Legacy98 mode. `Magic SysRq` is enabled on `ttyS0`. The capture never shows a shell prompt after `Please press Enter to activate this console.`

**DERIVED** from those addresses plus the local RBI TLV `flashaddress: 0x117c0000` and payload length 32,759,002:

- `0x117c0000` is the start of `bank_1` in this log. The sealed 19.4.0507 file is a bank image aimed at that offset, not a full NAND dump.
- Each named bank is `0x03c00000` (60 MiB). The sealed payload is about 31.2 MiB, so it does not fill a bank. On the booted bank, squashfs `rootfs` begins `0x01400000` into the bank. A ~31 MiB image written at the bank start would cover that pre-rootfs region and about 11 MiB of the rootfs window.
- `.r2secr=0x17fdf000` is the physical address where this bootloader parked the eRIP secret struct. `tools/secr`’s example dumps use addresses such as `0x1ffdf000` and only print key bytes after `insmod` of a matching `r2secr.*.ko`. This paste has the address and the stock `OSCK Loaded!` line. It does not have the `DumpHex` output. Stock community modules include 32-bit `r2secr.arm.4.1.38.ko` and **`r2secr.arm64.4.1.45.ko`** — not the **4.1.52** vermagic on this log. **2026-10-12:** repo build produced **`tools/secr/r2secr.arm64.4.1.52.ko`** (`scripts/build_r2secr_module.sh`, [r2secr-build-2026-10-12.md](r2secr-build-2026-10-12.md)); `tools/secr/` is gitignored.

**Still not in the paste:** OSCK or ECK bytes, a decrypted rootfs, PCI vendor/device IDs, and a public hit for git hashes `5bde4b5646ee7061e320c605e10e3aaa98af4706` or `c82c4f289bbd35e048aab42640d9d284a37e3ae9`. NAND `flashId=98dc9026` is only four bytes. That prefix is the one mainline’s unparsable-ID table uses for Toshiba `TC58NVG2S0F` (512 MB, 4K page); this driver printed `UNKNOWN NAND CHIP` and forced spare size from board config (`27B/512B`, `oobsize=216`). The catalog part is still not identified.

## Reported in issue 321, not in the paste

**REPORTED** by the NI-Pro comment of 4 September 2026, as quoted text inside the issue, not as a second log fetched here:

- Holding `a` at power-on prints `CFE-ROM WAS ABORTED` and `Please choose one of the following options:` with `c` (continue) and `s` (DDR safe mode).
- The same comment says the CFE shell is cut out, and quotes logviewer lines `[Restricted_Shell] User is connecting through tty...` and `[Lua] [Clash-access-control] User root has no serial access`.
- `23.1.b.0448-7241004 (.rbi not found)` and `23.1.b.0448-7241016 (.rbi not found)`.

An earlier comment asks for OpenWrt and posts PCB photos. That is a request, not a device target, DTS, or install report.

## Still not stated

NAND catalog part, Wi-Fi radio part, a GPL tarball or board file for EWA1330 / EWA1330TCS / GCNT-X, a public 23.1.b RBI URL, a TEST_CN20 pinout, and an OpenWrt board target. The Vantiva EWA1330TCS 19.4 file already noted in `findings/f1-api-map.md` is a module report, not a source tree. Detail of the searches that returned nothing is in `docs/gcnt-x-web-gaps.md`.

The flash ID is not a part number. The next hardware fact that this public log cannot supply is the NAND catalog part on AP-BCM114-0001.

**Owned unit (2026-10-12):** top-side PCB photo — no visible SPI NOR for clip read; NAND under shields per UART log. Connector inventory: [f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md).
