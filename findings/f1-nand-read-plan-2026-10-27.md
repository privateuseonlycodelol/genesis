# Physical read of NAND U3 (TC58NVG2S0HTAI0): plan (2026-10-27)

## Purpose

Get a raw dump of the live 23.1.b flash. The only input that can test the L598 key against a real `rootfs2` (see [l598-key-xts-19x-rbi-2026-10-27.md](l598-key-xts-19x-rbi-2026-10-27.md) and [f1-rootfs-key-l598-2026-10-27.md](f1-rootfs-key-l598-2026-10-27.md)). The 19.x RBI test was a weak negative because that file is sealed.

**Status:** planning only. No hardware bought, no clip fitted, no device contacted in this pass.

## Chip identity and geometry

| Item | Value | Status | Source |
| --- | --- | --- | --- |
> **Status note (2026-10-27):** the ID, page, block, blocks and ECC rows below were checked against the KIOXIA TAI0 datasheet (2019-10-01C). The verified values are in the "Update 2026-10-27: datasheet read" section at the end. The "REPORTED" tags in this table are the pre-datasheet values and are kept for the record.

| Part | KIOXIA TC58NVG2S0HTAI0, 3.3 V, TSOP-48 | VERIFIED (owner marking) | [f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md) |
| ID bytes | `98 DC 90 26 76 16 08 00` | REPORTED (Linux `nand_ids.c` entry for "TC58NVG2S0H 4G 3.3V 8-bit") | [linux-mtd patch, 2016](https://lists.infradead.org/pipermail/linux-mtd/2016-October/069905.html) |
| Consistency with our logs | Log `flashId=98dc9026` (19.4.0856 public paste, [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md)) matches the first four ID bytes | DERIVED | same |
| Page | 4096 data + 256 spare bytes (`SZ_4K`, OOB 256) | REPORTED (kernel entry; a distributor also lists 4352 bytes/page) | [linux-mtd patch](https://lists.infradead.org/pipermail/linux-mtd/2016-October/069905.html); [Avnet](https://www.avnet.com/shop/apac/search/TC58NVG2S0HTAI0) |
| Pages per block / block size | 64 pages, 256 KiB data (+16 KiB spare) | REPORTED (Avnet listing; kernel `SZ_256K`) | same |
| Blocks | 2048 total, minimum 2008 good | REPORTED (Avnet listing; the LCSC listing is for the HTA00 variant) | [Avnet](https://www.avnet.com/shop/apac/search/TC58NVG2S0HTAI0) |
| ECC requirement | 8-bit per 512 bytes (`NAND_ECC_INFO(8, SZ_512)`) | REPORTED | [linux-mtd patch](https://lists.infradead.org/pipermail/linux-mtd/2016-October/069905.html) |
| Chip size | 512 MiB | DERIVED (2048 × 256 KiB) | — |
| Our controller's view | 4096-byte pages, `oobsize=216` (27 B per 512 B) | VERIFIED in the 19.4 public log, not this unit | [gcnt-x-public-hardware.md](gcnt-x-public-hardware.md) |

**Not verified:** the KIOXIA datasheet itself. The geometry above comes from a kernel table and distributor listings. Every value must be checked against the KIOXIA PDF before the dump is interpreted.

**Open questions that decide the read method:**
1. Does the chip's on-die ECC run in normal reads, and can it be turned off? If on, the parity bytes are not in the raw spare data.
2. Which spare bytes hold the bad-block marker, and at which offset? A distributor says byte 4096 of the first page of each block, unverified.
3. Does the Broadcom NAND controller randomize data or use its own OOB layout? The 216-byte OOB in our 19.4 log suggests a controller-specific layout, not raw factory spare.

## Programmer options

| Option | What it is | Status for this chip | Notes |
| --- | --- | --- | --- |
| Commercial parallel programmer with a TSOP-48 socket (TL866 Plus / XGecu T48 class) | Off-the-shelf reader and writer | **Unverified** for TC58NVG2S0H. The searches found no support-list entry | A DEF CON talk reports the TL866 Plus has a TSOP-48 socket and that a pass-through adapter is needed. Check the vendor's current chip list before buying, and confirm the TSOP-48 adapter is in the kit |
| DIY parallel reader (microcontroller or FPGA + TSOP-48 clip) | Custom raw reader | Not built | Hobbyist TSOP-48 raw readers exist per public forum posts. More work, but full control of raw read commands |
| The device itself | U-Boot `nand read` or Linux `nanddump` | **Not available.** No U-Boot prompt and no Linux shell (see [f1-firmware-acquisition-paths-2026-10-27.md](f1-firmware-acquisition-paths-2026-10-27.md)) | — |
| SPI clip (CH341A) | — | **Does not apply.** The chip is parallel NAND | Already noted in [f1-board-visual-2026-10-12.md](f1-board-visual-2026-10-12.md) |

**Recommendation:** only a programmer whose read-only mode is confirmed to support this chip ID. Ask the seller for the exact support entry in writing before buying. Fallback: a DIY reader.

## In-circuit vs chip-off

| | In-circuit (clip on U3, board unpowered) | Chip-off (desolder U3, read in socket) |
| --- | --- | --- |
| Reversibility | High. The chip stays in the board | Low. Lifting or damaging the TSOP pads is possible, and reballing or reflow is needed to restore |
| Main risks | Clip misalignment shorting neighbouring pins on 0.5 mm pitch. Back-feeding the board through the SoC's I/O if the rail is partly live. Contention if the SoC drives NAND lines | Hot-air damage to the chip and PCB pads. Heat-induced bad solder joints on reflow |
| Board state after | Unchanged | Board is not restored until the chip is re-soldered |
| Data quality | Same chip, same contents | Same chip, same contents |
| Prerequisite | Board fully unpowered, not just in standby. Confirm that no SoC pin drives NAND lines when unpowered | Owner's explicit approval for desoldering |

**Recommendation:** in-circuit first. It is reversible and needs no heat. Move to chip-off only if the clip reads fail after the checks below. Chip-off is a separate decision that needs your approval.

## Procedure (in-circuit, proposed)

Each step is read-only. Nothing writes, erases or programs the chip.

1. **Datasheet:** download the KIOXIA TC58NVG2S0H datasheet and record the ECC, spare and bad-block sections. Nothing starts until this is done.
2. **Pinout map (board unpowered):** photograph U3 with the clip in mind, mark pin 1, and check continuity from each NAND pin to the SoC with a multimeter (no pin-to-net map exists yet). Record which pins are CE#, R/B#, WE#, RE#, ALE, CLE, I/O0–7 and VCC/VSS.
3. **Pre-clip checks:** confirm no shorts between adjacent pins with a multimeter. Confirm no pin is tied to a rail that could back-feed the board.
4. **Clip fit:** TSOP-48 clip matched to the programmer. Inspect under magnification before power.
5. **ID read:** read the chip ID command only. Expected `98 DC 90 26 76 16 08 00`. A mismatch stops the plan.
6. **Raw read:** read every page with spare (4352 bytes per page on this geometry), using the verified read command, and the ECC mode confirmed in step 1. Stop on the first unexpected error.
7. **Repeatability:** dump at least twice. Compare SHA-256. A mismatch means an unstable contact or ECC issue, and the dump is not used.
8. **Hash and archive:** store the dump under `artifacts/nand/` (gitignored). Record its SHA-256 in a finding. Do not commit it.

## Analysis plan after the dump

1. Strip the spare area and rebuild the logical image, using the controller's OOB layout from the 19.4 log as a starting hypothesis, not a fact.
2. Find the UBI erase counter headers (`UBI#` magic) and the volume table. Locate `rootfs2` (`ubi0:6` in the device log).
3. Extract the `rootfs2` volume and feed its first sector to `scripts/xts_plain64_squashfs_scan.py`, with the L598 key read from the log line. A hit for `hsqs` at tweak 0 is a positive result for the key. A miss is a falsifying negative, if the volume starts where the layout says.
4. Read the signed `bootfs` FIT from the dump. It gives the verity root digest and the `/brcm_rootfs_encrypt` mapper template (the device's bootfs was not previously read).

## Controls

- The ID check (step 5) confirms the chip and programmer agree before any data is trusted.
- Repeat dumps (step 7) check stability.
- An independent check of the UBI volume layout: the volume table has to match the device's kernel command line (`ubiblock0_6`).
- The scanner's positive and negative controls already pass (see the L598 scan finding).

## Risks and gates

- **Needs your approval:** buying hardware; fitting a clip; any heat.
- **Stop conditions:** any short, any unexpected ID, any read error that repeats, or a board that gets warm while unpowered.
- **Not in scope:** writing to the chip, erasing it, or powering the board with the clip fitted.

## What is not shown

- Not shown: the datasheet values (distributor and kernel sources only).
- Not shown: any programmer supports this chip.
- Not shown: that the clip can read U3 without disturbing neighbouring nets.
- Not shown: the 23.1.b bank layout. The dump would show it.

## Update 2026-10-27: programmer list and datasheet status

**Programmer list (VERIFIED, mirror copy):** the XGecu T48 device list V12.67 (dated 6.15.2024, 34,996 devices) contains `TC58NVG2S0HTAI0 @TSOP48` and `TC58NVG2S0HTA00 @TSOP48` (line 16958 of the extracted text). The official `xgecu.com/T48_List.txt` did not connect from this network. The copy used is `pdf.direnc.net/upload/t48-universal-programmer-device-list.pdf` (SHA-256 of the PDF is in the local copy). The list gives no ID, adapter or pinout detail.

**Adapter (REPORTED, seller listing):** `F48_EX-2 V2.0 Adapter TSOP48-2` is sold for NAND flash on the T48 only. Retail listings sell it separately. Whether it is in the kit, and whether its pin mapping matches this chip, is unverified. Do not buy the TL866 Plus TSOP-48 NAND adapter for the T48, because the listing says it is for the TL866II Plus only.

**Datasheet (NOT obtained):** the official KIOXIA PDF for the exact part is `europe.kioxia.com/.../DST_TC58NVG2S0HTAI0-TDE_EN_31425.pdf` (2019-10-01C, the TAI0 suffix). The request returned an HTML page, not a PDF, and the browser pane was redirected to the KIOXIA landing page. Automated access to this document was refused by the tool's bot-check classifier, so the download was stopped and not retried. The 2025 TA00 revision is on `kioxia.com/content/dam/kioxia/newidr/productinfo/datasheet/202502/DST_TC58NVG2S0HTA00-TDE_EN_31488.pdf`, also not fetched.

**What is needed from you:** download the TAI0 PDF in your browser and save it as `artifacts/datasheets/DST_TC58NVG2S0HTAI0-TDE_EN_31425.pdf`. I will then extract the ECC, spare, bad-block, ID and read-command sections. Until then the geometry above stays REPORTED, and the in-circuit read is not cleared.

**Purchase:** not made. The T48 chip entry is confirmed in the mirror. Buying still waits on the datasheet check and the adapter pin mapping.

## Update 2026-10-27: datasheet read (VERIFIED from the KIOXIA PDF)

Source: `artifacts/datasheets/DST_TC58NVG2S0HTAI0-TDE_EN_31425.pdf`, revision **2019-10-01C**, 66 pages, SHA-256 `cd4f115f681ff2036d9b36e06220ab5ec8a388817a7989fe406fb06432557424`. Identical to the copy in the Wayback capture dated 2023-10-25 (`web.archive.org/web/20231025090417if_/…`), same hash. Text extract: `artifacts/datasheets/DST_TC58NVG2S0HTAI0-TDE_EN_31425.txt`.

| Item | Datasheet text | Status vs. earlier REPORTED values |
| --- | --- | --- |
| Organization | (4096 + 256) bytes × 64 pages × 2048 blocks | Confirmed |
| Page / block | 4352-byte page; block 256 KB + 16 KB | Confirmed |
| ID read | `90h 00h` → `98h DCh 90h 26h 76h` (5 bytes, Table 5) | Confirmed for 98 DC 90 26 76. The kernel entry's extra bytes `16 08 00` are not in this table, so they stay unverified |
| 4th ID byte `26h` | Page 4 KB (bits I/O2–I/O1 = `10`), x8 width. Block bits are ambiguous in the text extract | Page size confirmed. Block size 256 KB is confirmed from the body text, not from the ID bits |
| ECC | "8 bit ECC for each 512 Byte is required" (host controller). No on-die ECC is described | Confirmed as a host requirement. The text never says whether internal ECC exists |
| Bad block | "bad block mark is in whole pages … read one column of any page in each block. If the data of the column is 00h, define the block as a bad block." **The column number is not given.** | The distributor's "byte 4096" is not in the datasheet. Still unverified |
| Valid blocks | Min 2008, max 2048 | Confirmed |
| Package | TSOP I 48-P-1220-0.50 | Confirmed |

**Consequences for the plan:**
- The datasheet describes a raw 4352-byte page, with the ECC parity written by the host controller. A raw read of data plus spare should give the controller's ECC bytes. The 216-byte OOB in our 19.4 log is consistent with that.
- The bad-block column is still unknown. Find it by testing: read one spare byte per block over the first few blocks, and check which column is 00h in the blocks the Broadcom controller marks bad. Do not assume byte 4096.
- Remaining unknowns: the controller's OOB layout and any data randomizer. Neither is in the datasheet.

**Status:** the datasheet check is done. Still not done: the adapter pin mapping for the T48 F48_EX-2 (REPORTED only), the board pin map, and any purchase. No hardware has been bought and the board has not been touched.
