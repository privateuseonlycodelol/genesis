# Owned GCNT-X top-side PCB — visual survey (2026-10-12)

**Source:** owner photos of open case (not in git; compare to [board-top.jpg](board-top.jpg) in repo). **2026-10-14:** close-up of populated NAND **U3**. **No** electrical test, flash read, or JTAG scan in this pass.

## VERIFIED silkscreen / connectors (top side)

| Marking | Notes |
| --- | --- |
| `AP-BCM114-00001 REV 1.0` | Matches BCM114 family naming in repo; revision **1.0** on this unit. |
| `CN1` | `3.3V GND TX RX` — UART site documented in [f1-uart-23.1b.md](f1-uart-23.1b.md); through-holes, no populated header. |
| `TEST_CN20` | Separate **test** footprint (16-pin class); pinout **UNKNOWN** — candidate JTAG/manufacturing bus per boot-log JTAG strings, not verified. |
| `JP1` | 4-pin header footprint near **USB**; function **UNKNOWN** — do not short without schematic. |
| `IoT_Connector` / `CN33` | Peripheral header on board edge; likely module/socket for IoT radio — not exercised. |
| `Voice_Connector` / `CN34` | **Unpopulated** footprint above NAND **U3** (2026-10-14 close-up); telephony/voice bus candidate — not wired on this unit. |
| Antenna silk | `4G-ANT0`–`3` and `ANT0`–`3` at coax pigtails. |
| Ports (bottom edge) | USB 3.0, four **LAN** (yellow), one **WAN** (red), DC power, power button, two tactile buttons (reset/WPS class). |

## VERIFIED — parallel NAND (photo + marking, 2026-10-14)

| Field | Value |
| --- | --- |
| PCB designator | **U3** |
| Manufacturer | KIOXIA (formerly Toshiba Memory) |
| Part number | **TC58NVG2S0HTAI0** |
| Capacity | 4 Gbit (512 MiB) |
| Type | 8-bit parallel **SLC** NAND |
| Package | **TSOP-48** (48 pins) |
| Voltage | 3.3 V nominal |
| Top marking lines | `DA3095`; `TAIWAN 22349AE` (fab **Taiwan**, date code **2234** = ISO week 34 **2022**); `TC58NVG2S0HTAI0` |
| Nearby silk | `R6205`, `R6206`, `C23`; metal can labeled **PBZ9** adjacent under a smaller shield |

Matches UART driver text `Toshiba TC58NVG2S0H 4G 3.3V 8-bit` in [f1-boot-log-2026-10-12.md](f1-boot-log-2026-10-12.md). **DERIVED:** Kioxia datasheet ID read for this family is **`98h DCh 90h 26h 76h`**; the boot log’s `flashId=0x98dc9026` is the **first four** bytes (fifth `76h` not printed there).

**REPORTED (datasheet, not independently verified on bench):** 4096+256 B pages, 64 pages/block, 2048 blocks max, 8-bit ECC per 512 B — aligns with UART geometry and UBI **2002+6** PEBs (= **2008**, datasheet minimum valid blocks).

## DERIVED (photo + UART log)

- **No exposed SOIC8/SOIC16 SPI NOR** in the surveyed top views; main storage is **U3** (**TSOP-48** parallel NAND). The 2026-10-14 close-up shows **U3 exposed** beside a large square EMI shield (SoC-side), not under that shield — **CH341A clip kits target SPI**, not this NAND; chip-off or SoC-mediated read still needs BCM OOB/ECC layout.
- **USB Ethernet on Mac** remains higher priority than buying JTAG/SPI gear before **TEST_CN20** identification and NAND vs SPI inventory.

## Owner note (2026-10-13, not bench-tested)

Wi‑Fi coax pigtails were briefly removed during case work. Reseat on silkscreen **`ANT0`–`ANT3`** only — **not** **`4G-ANT0`–`4G-ANT3`** (cellular). Straight press until the U.FL/IPEX connector clicks. Wrong port risks weak Wi‑Fi or wrong radio path; no RF measurement was performed after reseat.

## What was not shown

- Back of PCB, chip markings under heatsinks, RF can internals, `JP1` strap table, TEST_CN20 pin map, populated RGMII/PCIe test points.

## Next hardware documentation

- Back-side photo; close-up **TEST_CN20**; optional heatsink removal only with rework plan.
