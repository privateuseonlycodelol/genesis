# Owned GCNT-X top-side PCB — visual survey (2026-10-12)

**Source:** owner photo of open case (not in git; compare to [board-top.jpg](board-top.jpg) in repo). **No** electrical test, flash read, or JTAG scan in this pass.

## VERIFIED silkscreen / connectors (top side)

| Marking | Notes |
| --- | --- |
| `AP-BCM114-00001 REV 1.0` | Matches BCM114 family naming in repo; revision **1.0** on this unit. |
| `CN1` | `3.3V GND TX RX` — UART site documented in [f1-uart-23.1b.md](f1-uart-23.1b.md); through-holes, no populated header. |
| `TEST_CN20` | Separate **test** footprint (16-pin class); pinout **UNKNOWN** — candidate JTAG/manufacturing bus per boot-log JTAG strings, not verified. |
| `JP1` | 4-pin header footprint near **USB**; function **UNKNOWN** — do not short without schematic. |
| `IoT_Connector` / `CN33` | Peripheral header on board edge; likely module/socket for IoT radio — not exercised. |
| Antenna silk | `4G-ANT0`–`3` and `ANT0`–`3` at coax pigtails. |
| Ports (bottom edge) | USB 3.0, four **LAN** (yellow), one **WAN** (red), DC power, power button, two tactile buttons (reset/WPS class). |

## VERIFIED — parallel NAND (owner chip marking, 2026-10-14)

| Field | Value |
| --- | --- |
| Manufacturer | KIOXIA (formerly Toshiba Memory) |
| Part number | **TC58NVG2S0HTAI0** |
| Capacity | 4 Gbit (512 MiB) |
| Type | 8-bit parallel **SLC** NAND |
| Package | **TSOP-48** (48 pins) |
| Voltage | 3.3 V nominal |

Matches UART driver text `Toshiba TC58NVG2S0H 4G 3.3V 8-bit` and NAND ID prefix `0x98dc9026` in [f1-boot-log-2026-10-12.md](f1-boot-log-2026-10-12.md). The driver string truncates the catalog suffix (`…TAI0`).

## DERIVED (photo + UART log)

- **No exposed SOIC8/SOIC16 SPI NOR** visible on this top view; main storage is the **TSOP-48 parallel NAND** above (likely under heatsink/shield on this board) — **CH341A clip kits target SPI**, not that NAND, unless a separate SPI device is found on back side or under metal.
- **USB Ethernet on Mac** remains higher priority than buying JTAG/SPI gear before **TEST_CN20** identification and NAND vs SPI inventory.

## Owner note (2026-10-13, not bench-tested)

Wi‑Fi coax pigtails were briefly removed during case work. Reseat on silkscreen **`ANT0`–`ANT3`** only — **not** **`4G-ANT0`–`4G-ANT3`** (cellular). Straight press until the U.FL/IPEX connector clicks. Wrong port risks weak Wi‑Fi or wrong radio path; no RF measurement was performed after reseat.

## What was not shown

- Back of PCB, chip markings under heatsinks, RF can internals, `JP1` strap table, TEST_CN20 pin map, populated RGMII/PCIe test points.

## Next hardware documentation

- Back-side photo; close-up **TEST_CN20**; optional heatsink removal only with rework plan.
