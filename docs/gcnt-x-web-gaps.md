# Public gaps for Telia F1 / GCNT-X / EWA1330

Read on 12 October 2026. Public pages only. No router was contacted. Genesis `findings/f1-api-map.md` and `findings/tried.md` were read first and are not repeated. Issue 321, checkspeling/Telia-GCNT-X-F1, and benwaterson/technicolor-exploit were already read; this pass quotes only a boot log those notes had left unquoted, plus pages outside those three repos.

The module-list PDF is not copied. No serial number, MAC address, WAN address, password, or Wi-Fi key is included.

## 1. Exact Broadcom part

`AP-BCM114-0001` is not stated on any page fetched in this pass, including the boot log below.

The Gazelle Le datasheet for EWA1330TCS does not print a BCM part number. It prints: “Equipped with a System on Chip (SoC) featuring a next-gen 1.5 GHz dual-core ARMv8 processor (8k DMIPS) and XRDP Runner for CPU offload, the EWA1330TCS surpasses any current gateway’s performance.” And: “Hardware CPU 1.5 GHz dual-core ARMv8 CPU (8k DMIPS) with XRDP Runner hardware acceleration Memory 512 MB Flash 512 MB RAM”. Source: https://fiber.rone.se/Manualer/Router_datasheet%20Wifi%206.pdf

A GCNT-X serial log does print a Broadcom CPU string. The issue 321 opening post lists “Serial console bootlog: https://pastebin.com/biRghtLr” under firmware 19.4.0856. A later comment says: “here is serial console bootlog from Drunkei: https://pastebin.com/biRghtLr”. Source: https://github.com/hack-technicolor/hack-technicolor/issues/321

That paste prints, in order:

“CPU : BCM68360_B1”

“RAM : 512MB”

“Flash : 501MB NAND”

“Board Mnemonic : GCNT-X”

and later “License chip name: 68360”.

The same log’s software line is “SW Version : 19.4.0856-4581009-20221122120420-5bde4b5646ee7061e320c605e10e3aaa98af4706”. It does not print `EWA1330` or `AP-BCM114-0001`. Source: https://pastebin.com/raw/biRghtLr

A U-Boot commit about the SoC name, not about this product, prints: “BCM68360 is a variant within the BCM6856 chip family.” That commit does not print GCNT-X, EWA1330, or AP-BCM114-0001. Source: https://github.com/nieknooijens/u-boot/commit/fdf8f29dc7e9076790e4874c9ce07e593d9e17c4

## 2. NAND or SPI flash part number and partition map

Catalog part number: not stated. The same GCNT-X log prints “DevId 98dc9026 may not be supported. Will use config info” and “BrcmNAND mfg 0 0 UNKNOWN NAND CHIP 512MB on CS0” and “Found NAND on CS0: ACC=c388001b, cfg=07052300, cfg_ext=00000053, flashId=98dc9026, tim1=6532845b, tim2=00091e94”. No SPI flash part is printed. The banner line is “Flash : 501MB NAND”. Source: https://pastebin.com/raw/biRghtLr

Partition map from that boot log, quoted as printed:

“Creating 1 MTD partitions on "technicolor-nand-tl":”

“0x0000167c0000-0x000018fc0000 : "rootfs"”

“Creating 6 MTD partitions on "technicolor-nand-tl":”

“0x0000001c0000-0x0000117c0000 : "ubi"”

“0x0000117c0000-0x0000153c0000 : "bank_1"”

“0x0000153c0000-0x000018fc0000 : "bank_2"”

“0x000000100000-0x000000140000 : "eripv2"”

“0x000000140000-0x0000001c0000 : "rawstorage"”

“0x000018fc0000-0x00001f3c0000 : "opt"”

Source: https://pastebin.com/raw/biRghtLr

The datasheet prints only “Flash 512 MB”. Source: https://fiber.rone.se/Manualer/Router_datasheet%20Wifi%206.pdf

This log is firmware 19.4.0856. A 23.1.b partition map is not stated.

## 3. Wi-Fi or radio part

not stated.

The datasheet prints “1 Wi-Fi 6 (IEEE 802.11ax) 2.4 GHz radio” and “1 Wi-Fi 6 (IEEE 802.11ax) 5 GHz radio” and “4x4 Wi-Fi 6 (IEEE 802.11ax) 2.4 GHz access point”. No chip part. Source: https://fiber.rone.se/Manualer/Router_datasheet%20Wifi%206.pdf

Wi-Fi Alliance certificate WFA111505 prints “Model Number EWA1330TCS” and “Wi-Fi Component Operating System Linux” and “Wi-Fi Component Firmware 19.4” and “RF Architecture Bands Supported Transmit (Tx) Receive (Rx) 2.4 GHz 4 4 5 GHz 4 4”. No chip part. Source: https://api.cert.wi-fi.org/api/certificate/download/public?variantId=101698

The GCNT-X boot log prints “creating mapping for reserved memory phys 0x000000001ca00000 virt 0xffffffc01ca00000 size 0x00e00000 for dhd0” and “creating mapping for reserved memory phys 0x000000001bc00000 virt 0xffffffc01bc00000 size 0x00e00000 for dhd1” and “Checking country codes in /etc/wlan/brcm_country_map_2G (wl0)” and “Checking country codes in /etc/wlan/brcm_country_map_5G (wl1)” and “===== Release Version 5.02L.07p1 (build timestamp 220202_0023) =====”. No radio part number and no PCI vendor/device ID. Source: https://pastebin.com/raw/biRghtLr

The same log does print an Ethernet PHY line, “[_phy_init-395]: RTL8226 PHY initialize successfully.” and “[Rtl8226b_phy_init-652]: Set RTL8226B to SERDES 0 mode”. That is not a Wi-Fi part. Source: https://pastebin.com/raw/biRghtLr

## 4. Public GPL source archive

No tarball for EWA1330, EWA1330TCS, or GCNT-X, at 19.4 or 23.1.b, was found. A device tree or board file inside such a tarball is therefore not stated.

Vantiva’s public file for this product is a module report. It prints “This document aims to describe the Open Source Software which are embedded in product EWA1330TCS” and “Product EWA1330TCS Version v19.4 Open Source Modules 452” and “Proprietary to Technicolor Group – Connected Home – Do not re-distribute”. The module table is not copied here. Source: https://www.vantiva.com/app/uploads/2024/10/EWA1330TCS_19.4_external-1.pdf

The Homeware product page prints “Vantiva’s Homeware™ software solution leverages openWRT to deliver a scalable software stack for home gateways.” It does not link a source archive. Source: https://www.vantiva.com/connected-home/broadband/vantiva-homeware/

Upstream U-Boot has a reference-board device tree. It prints `model = "Broadcom bcm68360bg";` and `compatible = "broadcom,bcm68360bg", "brcm,bcm68360";`. It does not print GCNT-X, EWA1330, EWA1330TCS, or AP-BCM114-0001. Source: https://qemu.googlesource.com/u-boot/+/b6c50e5831f6ce3800d4b3cf3c7aa35dde8c48d9/arch/arm/dts/bcm968360bg.dts

## 5. Public 23.1.b firmware image or official download URL

not stated.

A Telia Finland moderator prints “Uusi päivittyvä firmware on 23.1.b-448-7241004.” The same thread prints “Reititin hakee automaattisesti tarjolla olevat päivitykset.” No download URL or filename is printed. Source: https://yhteiso.telia.fi/kiinteae-netti-8/telia-f1x-reitittimen-uusin-firmware-37349

Another Telia Finland thread prints “Software Version 23.1.b” as a version the writer’s router had reached. No file URL. Source: https://yhteiso.telia.fi/kiinteae-netti-8/telia-f1x-reititin-ja-kodin-tietoturvavahti-38013

Issue 321’s firmware URLs are 19.4 and 19.5 names, including “https://rgw.teliacompany.com:7577/cpe-r/p/tZLIYj9o/EWA1331_EWA1330_gcnt_x_19.5.1062_4581010_unified.rbi”. Those are sealed 19.x RBI links and do not count. Source: https://github.com/hack-technicolor/hack-technicolor/issues/321

The hack-technicolor firmware repository page lists “## FGA2233 / GCNT-R” and “## OWA0131 / GCNT-N”. The fetched page does not contain GCNT-X, EWA1330, or 23.1.b. Source: https://hack-technicolor.readthedocs.io/en/stable/Repository/

Vantiva’s regulatory hits for this family are the 19.4 open-source report and EU declarations. The EWA1331 declaration prints “Product Name: EWA1331” and “Product Type: Ethernet Gateway”. It does not print a firmware URL. Source: https://www.vantiva.com/app/uploads/2025/08/EWA1331_DoC_CE-20250807-en_v4.0_public.pdf

## 6. UART or CFE capture that prints the flash chip name or a console prompt

Flash chip name: the capture prints “UNKNOWN NAND CHIP”, quoted in section 2. A catalog name is not stated.

Console prompt, from the same GCNT-X log: “*** Press b to enter BOOT-P ***” and “Please press Enter to activate this console.” Source: https://pastebin.com/raw/biRghtLr

The log header is “=~=~=~=~=~=~=~=~=~=~=~= PuTTY log 2024.02.22 18:25:13 =~=~=~=~=~=~=~=~=~=~=~=” and the banner includes “Technicolor Gateway” and “Board Mnemonic : GCNT-X”. Source: https://pastebin.com/raw/biRghtLr

Other paste links from issue 321, `N1HbxPj1`, `3c0PRK0K`, `waR76GaR`, `0X1Yg6rF`, and `09Wd3PRH`, returned HTTP 404 on 12 October 2026.

## 7. TEST_CN20 pinout

not stated.

A search for `TEST_CN20` and `TEST CN20` did not return a page that prints that designator. The GCNT-X boot log does not print it. Source of the log: https://pastebin.com/raw/biRghtLr

## 8. OpenWrt board target, device tree, or install report that names this board

not stated.

The hack-technicolor repository names other GCNT boards, “## FGA2233 / GCNT-R” and “## OWA0131 / GCNT-N”, and does not name GCNT-X or EWA1330. Source: https://hack-technicolor.readthedocs.io/en/stable/Repository/

Searches on openwrt.org and forum.openwrt.org for EWA1330, EWA1331, GCNT-X, and Telia F1 returned other products (ZyXEL NR7101, D-Link DGS-1210). Those pages do not print this board.

OpenWrt commits for “eap1300” are EnGenius EAP1300 / EAP1300EXT. One commit prints “The EnGenius EAP1300 and EAP1300EXT use identical boards and firmware (as flashed) from the vendor.” That is a different product. Source: https://git.openwrt.org/?a=commit&h=85f6f882232367b64c7933fb4856fdf4999c6aae&p=openwrt%2Fopenwrt.git

The U-Boot file in section 4 is a Broadcom reference board, `model = "Broadcom bcm68360bg"`, and does not name this gateway. Source: https://qemu.googlesource.com/u-boot/+/b6c50e5831f6ce3800d4b3cf3c7aa35dde8c48d9/arch/arm/dts/bcm968360bg.dts

## Sources that added nothing

- Broadcom BCM957414 NIC datasheets and the BCM6714 Wi-Fi 8 page. They do not print AP-BCM114-0001, EWA1330, or GCNT-X. Example: https://docs.broadcom.com/doc/957414A4140C-DS102
- FCC ID G95-EWA1230. The grant page is for a different model. https://fccid.io/G95-EWA1230
- FCC ID E8HKT-1330, a Bluetooth keyboard. https://fccid.io/E8HKT-1330
- CND-tek G3601D, “DESCRIPTION： 1000 BASE-T MAGNETICS MODULES”. A LAN transformer, not the SoC, NAND, or Wi-Fi chip. https://file.huaqiu.com/web2/M00/22/BA/poYBAGGohGqAL0w2AAVOxC3gr5Q132.pdf?G3601D_CND-tek.pdf=
- Distributor pages for the different string UTG24C01. No page fetched prints `UTG18101` or `U1V24C01` as a SoC, NAND, or Wi-Fi part.
- DWA0120 product PDFs returned by the TEST_CN20 search. They do not print TEST_CN20. https://www.provu.co.uk/products/technicolor/DWA0120/DWA0120.pdf
- Sony Xperia pages that use a “23.1.B” version string. Unrelated.
- https://linux-shell.se/linux-openwrt/technicolor/gcnt-x/ returned HTTP 500.
- https://www.nr1.nu/linux-openwrt/technicolor/gcnt-x/technicolor-gcnt-x-telia/ returned HTTP 404.

The Wi-Fi chip part is the fact still only available from a serial boot log that prints a PCI ID or radio part, or from opening the shield.
