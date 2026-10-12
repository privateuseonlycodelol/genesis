# F1 boot capture — selected LF-indexed evidence

Companion to [the detailed interpretation](f1-boot-log-2026-10-12.md). **VERIFIED:** each numbered record below comes from the owner-supplied log with SHA-256 `3f242d10ede0a08f3c2d72ebb4966f80222ade017b3e03690ffc08c72fa27feb`. Source: 86,162 bytes, 1,632 LF records. This is a selected evidence appendix, not the full raw transcript or an independent capture.

Line numbers are assigned before stripping CR/ANSI; L588 includes text that a terminal could overwrite. Long hex strings (including ordinary hashes), MACs, UUIDs and IPv4-shaped text are conservatively redacted. Trailing source spaces are shown as visible `␠` glyphs. L598's unlabeled hex value is deliberately withheld. Known image hashes are separately documented in the interpretation. Raw private copy: `artifacts/uart/20261012-193402/raw.log`; machine-readable inventory: `index.json` in that directory. No raw file is tracked.

Generated using `python3 scripts/index_f1_boot_log.py`; literal-fixture checks: `python3 scripts/test_index_f1_boot_log.py`. Matching text indicates a message occurred, not that an exploit, shell, key recovery or external service was established. Parent-reviewed extraction; empty lines and repetitive DDR calibration/DMA details are omitted.

## Selected source records

```text
L0002: BTRM
L0036: U-Boot SPL 2019.07 (Jul 25 2024 - 13:09:42 +0530)
L0038: Strap Register: 0x13008176
L0039: Board is FLD secure
L0044: WARNING -- JTAG UNLOCK IS ENABLED
L0049: digest sha256 OK
L0052: digest sha256 OK
L0055: U-Boot DDR standalone 2019.07 (Dec 15 2022 - 21:44:37 -0800) Build: 50404p1@424599
L0329: DDR test done successfully
L0331: WDT:   Started with servicing (60s timeout)
L0334: digest sha256 OK
L0336: U-Boot TPL 2019.07 (Jul 25 2024 - 13:08:58 +0530)
L0337: Board is FLD secure
L0350: erip -- image from 10485760 to 536870912
L0353: UBI warning: LEB 0 of 1 is missing
L0354: UBI warning: Failed to load volume 18
L0355: UBI warning: Failed
L0356: ERR :rip2_flash_ubi_init failed -22
L0357: EFU: Skip OFF, vol18: eripv2efu not found
L0361: Volume Boot Order: 5 3␠
L0363: SELECTED Image 2 FIT_VOL_ID is 5
L0364: Retry boot 1 times.
L0365: Launch image from vol 5...
L0368: Found FIT format U-Boot
L0372: Fit checksum Pass␠
L0373: INFO: Found key emek in under /trust/tch_keys
L0374: INFO: Found key emcv in under /trust/tch_keys
L0375: INFO: Legacy SDR detected. Consider upgrading to latest SDR format
L0376: INFO: Found potential SDR: delg_id:12345 maxrollbck:3 size:268
L0377: INFO: Found potential SDR: PubKey:0x2306f4e2 Sig:0x3daccf6e
L0378: emsa_pss_verify salt_len 0x20 hash_len 0x20
L0379: INFO: SDR Authentication Successfull!
L0380: emsa_pss_verify salt_len 0x20 hash_len 0x20
L0381: INFO: Found potential Security Node: Policy:0xedfe0dd0 Sig:0xa725c544 Size:2352
L0382: emsa_pss_verify salt_len 0x20 hash_len 0x20
L0383: INFO: Security Node Authentication Successfull!
L0384: INFO: Found potential Encrypted AES Key: KAES:0xbb090960 len:48
L0385: FIT Header Authentication Successfull!
L0386: INFO: Found key secret_1 in under /security_policy/encoded_keys
L0387: INFO: Key data for key secret_1 not found! Skipping Key!
L0388: INFO: Found key secret_2 in under /security_policy/encoded_keys
L0389: INFO: Key data for key secret_2 not found! Skipping Key!
L0390: INFO: Found key image_aes in under /trust/encoded_keys
L0391: INFO: Found key cli_seed in under /trust/encoded_keys
L0392: INFO: Found disabled /security_policy/anti-rollback node!
L0393: INFO: Found disabled /trust/anti-rollback node!
L0394: INFO: Found /security_policy/sec_restriction/sec_exports  in security policy
L0395: INFO: Found item:key_dev_specific_delegate_private_256 id:SEC_ITEM_KEY_DEV_SPECIFIC in fit
L0396: INFO: Found item:key_dev_specific_delegate_private_512 id:SEC_ITEM_KEY_DEV_SPECIFIC in fit
L0397: INFO: Found item:key_dev_specific_delegate_secure_512 id:SEC_ITEM_KEY_DEV_SPECIFIC in fit
L0398: INFO: Found /trust/sec_exports  in fit
L0399: INFO: Found item:key_dev_specific_256 id:SEC_ITEM_KEY_DEV_SPECIFIC in fit
L0400: INFO: Found item:key_dev_specific_512 id:SEC_ITEM_KEY_DEV_SPECIFIC in fit
L0401: INFO: Found item:serial_num id:SEC_ITEM_SER_NUM in fit
L0404: ## Checking hash(es) for Image atf ... sha256+ OK
L0406: ## Checking hash(es) for Image uboot ... sha256+ OK
L0408: ## Checking hash(es) for Image fdt_GCNT-X ... sha256+ OK
L0412: INFO: Creating /trust/brcm_pub_key
L0413: INFO: Adding exported item node brcm_pub_key to dtb, size:256
L0418: INFO: Creating /trust/key_image_aes
L0419: INFO: Adding exported decoded key node key_image_aes to dtb, size:32
L0420: INFO: Creating /trust/key_cli_seed
L0421: INFO: Adding exported decoded key node key_cli_seed to dtb, size:32
L0422: INFO: Found matching item for SEC_ITEM_KEY_DEV_SPECIFIC = 21
L0423: INFO: Creating /trust/key_dev_specific_delegate_private_256
L0424: INFO: Adding exported item node key_dev_specific_delegate_private_256 to dtb, size:32
L0425: INFO: Found matching item for SEC_ITEM_KEY_DEV_SPECIFIC = 21
L0426: INFO: Creating /trust/key_dev_specific_delegate_private_512
L0427: INFO: Adding exported item node key_dev_specific_delegate_private_512 to dtb, size:64
L0428: INFO: Found matching item for SEC_ITEM_KEY_DEV_SPECIFIC = 21
L0429: INFO: Creating /trust/key_dev_specific_delegate_secure_512
L0430: INFO: Adding exported item node key_dev_specific_delegate_secure_512 to dtb, size:64
L0431: INFO: Found matching item for SEC_ITEM_KEY_DEV_SPECIFIC = 21
L0432: INFO: Creating /trust/key_dev_specific_256
L0433: INFO: Adding exported item node key_dev_specific_256 to dtb, size:32
L0434: INFO: Found matching item for SEC_ITEM_KEY_DEV_SPECIFIC = 21
L0435: INFO: Creating /trust/key_dev_specific_512
L0436: INFO: Adding exported item node key_dev_specific_512 to dtb, size:64
L0437: INFO: Found matching item for SEC_ITEM_SER_NUM = 22
L0440: INFO: No TEE detected, scrubbing secure items!
L0441: INFO: Scrubbing secure node /trust/key_dev_specific_delegate_secure_512
L0444: U-Boot 2019.07 (Jan 06 2025 - 22:32:33 +0000), Build: 20250106223231-c5207534ab
L0446: DRAM:  512 MiB
L0447: Strap Register: 0x13008176
L0514: Chip ID: BCM68360_B1
L0515: Broadcom B53 Dual Core: 1500MHz
L0516: RDP: 1400MHz
L0518: WDT:   Started with servicing (80s timeout)
L0526: In:    serial0
L0527: Out:   serial0
L0528: Err:   serial0
L0529: Board is FLD secure
L0534: Initializing U-Boot...
L0547: Registered phy device: PHY_TYPE_RTL8226:0x5
L0548: Registered phy device: PHY_TYPE_RTL8226:0x7
L0558: Failed to find phy for port port_wan (phy_wan_serdes)
L0563: [Rtl8226b_phy_init-652]: Set RTL8226B to SERDES 0 mode␠
L0564: [Rtl8226b_phy_init-662]: Disable RTL8226B auto-negotiation␠
L0565: [_phy_init-402]: RTL8226 PHY initialize successfully.
L0566: [_phy_power_set-55]: return RTL8226B Power set.
L0567: No export under key_dev_specific_delegate_private_512
L0568: No export under key_cli_seed
L0569: No export under key_image_aes
L0570: copying emek
L0571: copying emcv
L0572: Initialize eRIP Driver..␠
L0573: Read 253952 bytes from volume eripv2 to 000000001ff9d479
L0580: Uboot Version       :  U-Boot 2019.07 (Jan 06 2025 - 22:32:33 +0000)20250106223231-c5207534ab␠
L0584: Board Mnemonic      : GCNT-X
L0585: Secure Mode         : FLD
L0586: Market ID           : FFF0
L0587: Bank duplication not supported
L0588: *** Press b to enter BOOT-P ***                                                                          XRDP Ethernet driver un-initialize
L0589: [_phy_power_set-55]: return RTL8226B Power set.
L0592: Booting             : Bank 2
L0594: Read 8615825 bytes from volume bootfs2 to 0000000002000000
L0595: emsa_pss_verify salt_len 0x20 hash_len 0x20
L0596: FIT Header Authentication Successfull!
L0598: [REDACTED_HEX]ERROR:Unable to add a fixup to FDT
L0599: ## Loading kernel from FIT Image at 02000000 ...
L0601:    Verifying Hash Integrity ... OK
L0603:      Description:  4.19 kernel
L0605:      Compression:  lzma compressed
L0606:      Data Start:   0x0233a025
L0607:      Data Size:    3678822 Bytes = 3.5 MiB
L0608:      Architecture: AArch64
L0610:      Load Address: 0x00100000
L0611:      Entry Point:  0x00100000
L0612:      Hash algo:    sha256
L0613:      Hash value:   [REDACTED_LONG_HEX]
L0614:    Verifying Hash Integrity ... sha256+ OK
L0615: ## Loading fdt from FIT Image at 02000000 ...
L0617:    Verifying Hash Integrity ... OK
L0619:      Description:  dtb
L0621:      Compression:  uncompressed
L0622:      Data Start:   0x027e6435
L0623:      Data Size:    54555 Bytes = 53.3 KiB
L0624:      Architecture: AArch64
L0625:      Hash algo:    sha256
L0626:      Hash value:   [REDACTED_LONG_HEX]
L0627:    Verifying Hash Integrity ... sha256+ OK
L0631: RSVD: not found enrty for adsl
L0632: RSVD: not found enrty for bufmem
L0633: RSVD: not found enrty for rnrmem
L0634: RSVD: Allocated for rdp1    32MB
L0635: RSVD: Allocated for rdp2    8MB
L0636: RSVD: Allocated for dhd0    11MB
L0637: RSVD: Total 0x03400000 bytes CMA reserved memory @ 0x1cc00000
L0639: Starting kernel ...
L0642: Linux version 4.19.235 (repowrt-builder@b855aa8caa5c) (gcc version 10.3.0 (Buildroot 2021.02.4)) #3 SMP PREEMPT Tue Mar 11 05:27:32 UTC 2025
L0643: Machine model: GCNT-X
L0644: earlycon: bcm63xx_uart0 at MMIO 0x00000000ff800640 (options '115200n8')
L0645: bootconsole [bcm63xx_uart0] enabled
L0649: psci: probing for conduit method from DT.
L0650: psci: PSCIv1.1 detected in firmware.
L0651: psci: Using standard PSCI v0.2 function IDs
L0652: psci: MIGRATE_INFO_TYPE not supported.
L0653: psci: SMC Calling Convention v1.0
L0657: CPU features: enabling workaround for ARM erratum 843419
L0658: CPU features: enabling workaround for ARM erratum 845719
L0660: CPU features: detected: Kernel page table isolation (KPTI)
L0662: Kernel command line: coherent_pool=4M cpuidle_sysfs_switch pci=pcie_bus_safe console=ttyS0,115200 earlycon rootwait cma=56M mtdparts=brcmnand.0:2097152(loader),6291456(dri),1048576(eripv2_bak1),1048576(eripv2_bak2),526385152@10485760(image) root=/dev/dm-1 ubi.mtd=image ubi.block=0,6 rootfstype=squashfs dm-mod.create="lroot,,,ro, 0 108184 verity 1 /dev/ubiblock0_6  /dev/ubiblock0_6  512 512 108184 108185 sha256 **************************************************************** **************************************************************** 1 check_at_most_once ; lroot2,,,ro,0 108184 crypt aes-xts-plain64 **************************************************************** 0 /dev/dm-0 0" swflag=E1 secmode=SEC
L0665: Memory: 383844K/524288K available (7550K kernel code, 404K rwdata, 1672K rodata, 448K init, 410K bss, 29852K reserved, 110592K cma-reserved)
L0686: bootloader version  U-Boot2019.07(01/06/2025-22:32:33+0000)20250106223231-c5207534a
L0689: smp: Bringing up secondary CPUs ...
L0692: smp: Brought up 1 node, 2 CPUs
L0693: SMP: Total of 2 processors activated.
L0694: CPU features: detected: 32-bit EL0 Support
L0695: CPU features: emulated: Privileged Access Never (PAN) using TTBR0_EL1 switching
L0696: CPU: All CPU(s) started at EL2
L0707: Strap Register: 0x13008176
L0775: bcm-dgasp ff85a024.dying_gasp: Dying Gasp platform device brcm,dgasp-periph matched
L0776: dg-periph-reg: 0x00000000ff85a024<-->0xffffff8008b95024:0x00000000
L0816: console [ttyS0] enabled
L0817: bootconsole [bcm63xx_uart0] disabled
L0818: bootconsole [bcm63xx_uart0] disabled
L0822: nand: device found, Manufacturer ID: 0x98, Chip ID: 0xdc
L0823: nand: Toshiba TC58NVG2S0H 4G 3.3V 8-bit
L0824: nand: 512 MiB, SLC, erase size: 256 KiB, page size: 4096, OOB size: 256
L0825: bcm63xx_nand ff801800.nand: Adjust timing_1 to 0x6532845b, timing_2 to 0x00091e94
L0826: bcm63xx_nand ff801800.nand: detected 512MiB total, 256KiB blocks, 4KiB pages, 27B OOB, 8-bit, BCH-8
L0827: Bad block table found at page 131008, version 0x01
L0828: Bad block table found at page 130944, version 0x01
L0829: nand_read_bbt: bad block at 0x000018000000
L0830: nand_read_bbt: bad block at 0x000018040000
L0831: 5 cmdlinepart partitions found on MTD device brcmnand.0
L0832: Creating 5 MTD partitions on "brcmnand.0":
L0833: 0x000000000000-0x000000200000 : "loader"
L0834: 0x000000200000-0x000000800000 : "dri"
L0835: 0x000000800000-0x000000900000 : "eripv2_bak1"
L0836: 0x000000900000-0x000000a00000 : "eripv2_bak2"
L0837: 0x000000a00000-0x000020000000 : "image"
L0872: device-mapper: ioctl: 4.39.0-ioctl (2018-04-03) initialised: dm-devel@redhat.com
L0916: ubi0: attaching mtd5
L0917: ubi0: scanning is finished
L0918: ubi0: attached mtd5 (name "image", size 502 MiB)
L0919: ubi0: PEB size: 262144 bytes (256 KiB), LEB size: 253952 bytes
L0920: ubi0: min./max. I/O unit sizes: 4096/4096, sub-page size 4096
L0921: ubi0: VID header offset: 4096 (aligned 4096), data offset: 8192
L0922: ubi0: good PEBs: 2002, bad PEBs: 6, corrupted PEBs: 0
L0923: ubi0: user volume: 11, internal volumes: 1, max. volumes count: 128
L0924: ubi0: max/mean erase counter: 7/3, WL threshold: 4096, image sequence number: 0
L0925: ubi0: available PEBs: 586, total reserved PEBs: 1416, PEBs reserved for bad PEB handling: 34
L0926: ubi0: background thread "ubi_bgt0d" started, PID 746
L0927: block ubiblock0_6: created from ubi0:6(rootfs2)
L0928: device-mapper: init: waiting for all devices to be available before creating mapped devices
L0929: device-mapper: ioctl: dm-0 (lroot) is ready
L0930: device-mapper: ioctl: dm-1 (lroot2) is ready
L0934: Registered phy device: PHY_TYPE_RTL8226:0x5
L0935: Registered phy device: PHY_TYPE_RTL8226:0x7
L0938: VFS: Mounted root (squashfs filesystem) readonly on device 254:1.
L0941: Checked W+X mappings: passed, no W+X pages found
L0942: Run /sbin/init as init process
L0943: open: No such file or directory
L0944: init: Console is alive
L0945: init: - watchdog -
L0950: init: - preinit -
L0951: UBIFS (ubi0:20): background thread "ubifs_bgt0_20" started, PID 914
L0952: UBIFS (ubi0:20): recovery needed
L0953: UBIFS (ubi0:20): recovery completed
L0954: UBIFS (ubi0:20): UBIFS: mounted UBI device 0, volume 20, name "rootfs_data"
L0955: UBIFS (ubi0:20): LEB size: 253952 bytes (248 KiB), min./max. I/O unit sizes: 4096 bytes/4096 bytes
L0956: UBIFS (ubi0:20): FS size: 102342656 bytes (97 MiB, 403 LEBs), journal size 5079040 bytes (4 MiB, 20 LEBs)
L0957: UBIFS (ubi0:20): reserved for root: 4833895 bytes (4720 KiB)
L0958: UBIFS (ubi0:20): media format: w5/r0 (latest is w5/r0), UUID [REDACTED_UUID], small LPT model
L0959: UBIFS mount OK
L0960: UBIFS (ubi0:20): un-mount UBI device 0
L0961: UBIFS (ubi0:20): background thread "ubifs_bgt0_20" stops
L0963: UBIFS (ubi0:20): background thread "ubifs_bgt0_20" started, PID 957
L0964: UBIFS (ubi0:20): UBIFS: mounted UBI device 0, volume 20, name "rootfs_data"
L0965: UBIFS (ubi0:20): LEB size: 253952 bytes (248 KiB), min./max. I/O unit sizes: 4096 bytes/4096 bytes
L0966: UBIFS (ubi0:20): FS size: 102342656 bytes (97 MiB, 403 LEBs), journal size 5079040 bytes (4 MiB, 20 LEBs)
L0967: UBIFS (ubi0:20): reserved for root: 4833895 bytes (4720 KiB)
L0968: UBIFS (ubi0:20): media format: w5/r0 (latest is w5/r0), UUID [REDACTED_UUID], small LPT model
L0969: mount_root: switching to ubifs overlay
L0970: mount_root: executing script in /lib/mount_root
L0971: mount_root: /lib/mount_root/00_overlay_bank_check.sh
L0972: mount_root: /lib/mount_root/00_rtfd_all
L0973: mount_root: /lib/mount_root/10_remove_due_to_upgrade
L0974: mount_root: /lib/mount_root/20_rtfd_remove
L0975: mount_root: /lib/mount_root/30_parameter_conversion
L0976: HOMEWARE_CONFIG_mount_root: /lib/mount_root/80_rtfd_restore
L0977: ON_ACTIVE_BANK
L0979: platform: module license 'Proprietary' taints kernel.
L0984: eRIPv2 secrets passed correctly to Linux
L0985: procd: - early -
L0986: procd: - watchdog -
L0987: procd: - watchdog -
L0988: procd: - ubus (running as root!) -
L0989: procd: - init -
L0990: Please press Enter to activate this console.
L0997: ncr_master_key_set_internal
L0998: ncr: driver 0.4-tch loaded.
L0999: cryptodev: driver 1.11 loaded.
L1000: OSCK Loaded!
L1001: keymanager: Client private key loaded! (client_rsa_privkey)
L1016: UBIFS error (ubi0:10 pid 1681): ubifs_mount: too few LEBs (9), min. is 17
L1017: UBIFS error (ubi0:11 pid 1691): ubifs_mount: too few LEBs (9), min. is 17
L1040: Broadcom BP3 Driver - Platform: TELCO, BPA: v0, BLOB: v1, License Folder: "/data/licenses", Chip Name: 68360, OUI: A0B53C, Release Tag: 5.04L.04p1
L1041: [ERROR dumpframe] __license_verify_and_load,154: Wrong CCF size 0 expected 1076
L1042: [ERROR dumpframe] traverse_dir_read_files_iteratively,147: Cannot open /data/licenses directory
L1043: [ERROR dumpframe] BP3_SEC_LicenseLoad,621: Failed to load licenses from storage
L1044: BP3 status - provisioned
L1075: 	Pkt HW acceleration is disabled/unavailable.
L1078: 	Pkt HW acceleration is disabled/unavailable.
L1107: [_phy_init-456]: RTL8226 PHY initialize successfully.
L1108: [_phy_power_set-58]: return RTL8226B Power set.
L1123: Broadcom Packet Flow Cache HW acceleration enabled.
L1185: hub 1-0:1.0: config failed, hub doesn't have any ports! (err -19)
L1220: platform regulatory.0: Direct firmware load for regulatory.db failed with error -2
L1221: cfg80211: failed to load regulatory.db
L1244: CFG80211-ERROR) wl_setup_wiphy :␠
L1246: CFG80211-ERROR) wl_cfg80211_apply_eventbuffer :␠
L1248: CFG80211-ERROR) wl_cfg80211_set_cac_state_change_eventbits :␠
L1249: failed to set WLC_E_CAC_STATE_CHANGE bit
L1265: DHD  concate_extfdimg_name: Final FW path is /etc/wlan/dhd/43684b0/release/rtecdc.bin␠
L1272: dhdpcie_hybridfw_get_next_block Found section 0 with length 2023624
L1273: dhdpcie_hybridfw_get_next_block Found section 1 with length 1040384
L1285: 	 FWID 0x73359306, flags 0x10b10086, dcap1 0x2f8f0000 dcap2 0x00000005
L1344: PCIe IPC Host Dongle Training Completed!
L1399: dhd_sync_with_dongle: GET_REVINFO device 0x442b, vendor 0x14e4, chipnum 0xaaa4, corerev 129
L1400: Dongle Host Driver, version 17.10.251.7305 (r) [a4efbc31b4] BSPv4W13
L1401: Compiled in drivers/net/wireless/bcmdhd
L1403: Register interface [wl0]  MAC: [REDACTED_MAC]
L1416: CFG80211-ERROR) wl_setup_wiphy :␠
L1418: CFG80211-ERROR) wl_cfg80211_apply_eventbuffer :␠
L1420: CFG80211-ERROR) wl_cfg80211_set_cac_state_change_eventbits :␠
L1421: failed to set WLC_E_CAC_STATE_CHANGE bit
L1437: DHD  concate_extfdimg_name: Final FW path is /etc/wlan/dhd/43684b0/release/rtecdc.bin␠
L1444: dhdpcie_hybridfw_get_next_block Found section 0 with length 2023624
L1445: dhdpcie_hybridfw_get_next_block Found section 1 with length 1040384
L1457: 	 FWID 0x73359306, flags 0x10b10086, dcap1 0x2f8f0000 dcap2 0x00000005
L1516: PCIe IPC Host Dongle Training Completed!
L1568: dhd_sync_with_dongle: GET_REVINFO device 0x442a, vendor 0x14e4, chipnum 0xaaa4, corerev 129
L1569: Dongle Host Driver, version 17.10.251.7305 (r) [a4efbc31b4] BSPv4W13
L1570: Compiled in drivers/net/wireless/bcmdhd
L1572: Register interface [wl1]  MAC: [REDACTED_MAC]
L1579: [INF ponserdes] wan_serdes_config: SERDES: Wan type: AE_2_5G
L1592: [Rtl8226b_phy_init-652]: Set RTL8226B to SERDES 2 mode␠
L1593: [Rtl8226b_phy_init-662]: Disable RTL8226B auto-negotiation␠
L1594: [_phy_init-456]: RTL8226 PHY initialize successfully.
L1595: [_phy_power_set-58]: return RTL8226B Power set.
L1596: [_phy_power_set-58]: return RTL8226B Power set.
L1597: [_phy_power_set-58]: return RTL8226B Power set.
L1598: WLSSK (34) init isBrReady 0
L1599: WLSSK (34) init isBrReady 0
L1600: WLSSK (37) init isBrReady 0
L1601: WLSSK (40) init isBrReady 0
L1602: WLSSK (40) isBrReady 1
L1603: WLSSK (40) plugins loading disabled
L1604: WLSSK (40) restart 15
L1605: OCSD Enter (build timestamp: [Tue Jan  7 01:49:17 UTC 2025], LogLevel[0])
L1606: apiosd Enter (build timestamp: [Tue Jan  7 01:31:09 UTC 2025])
L1607: lxc.mount: debug  Setting opt creator bank 1
L1608: apibdk_sd::60.306:error:absdEvent_updateNetworkChange:1236:Missing interface or device: data={"is_bridge":false,"is_deleted":false,"isLayer3":true,"interface":"gt0","up":false,"pending":false,"available":true,"autostart":false,"dynamic":false,"proto":"gretap","data":{},"errors":[{"subsystem":"gretap","code":"MISSING_PEER_ADDRESS"}]}
L1609: Err: rc: 1684, Empty key, OR saepk:0
L1610: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1611: Err: rc: 1684, Empty key, OR saepk:0
L1612: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1613: Err: rc: 1684, Empty key, OR saepk:0
L1614: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1615: WLSSK (73) restart done
L1616: WLSSK (73) init done
L1617: WLSSK (75) restart 15
L1618: Err: rc: 1684, Empty key, OR saepk:0
L1619: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1620: Err: rc: 1684, Empty key, OR saepk:0
L1621: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1622: Err: rc: 1684, Empty key, OR saepk:0
L1623: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1624: WLSSK (106) restart done
L1625: WLSSK (106) restart 0
L1626: Err: rc: 1684, Empty key, OR saepk:0
L1627: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1628: Err: rc: 1684, Empty key, OR saepk:0
L1629: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1630: Err: rc: 1684, Empty key, OR saepk:0
L1631: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1632: WLSSK (130) restart done
```

## Final 35 source records (includes overlap)

```text
L1598: WLSSK (34) init isBrReady 0
L1599: WLSSK (34) init isBrReady 0
L1600: WLSSK (37) init isBrReady 0
L1601: WLSSK (40) init isBrReady 0
L1602: WLSSK (40) isBrReady 1
L1603: WLSSK (40) plugins loading disabled
L1604: WLSSK (40) restart 15
L1605: OCSD Enter (build timestamp: [Tue Jan  7 01:49:17 UTC 2025], LogLevel[0])
L1606: apiosd Enter (build timestamp: [Tue Jan  7 01:31:09 UTC 2025])
L1607: lxc.mount: debug  Setting opt creator bank 1
L1608: apibdk_sd::60.306:error:absdEvent_updateNetworkChange:1236:Missing interface or device: data={"is_bridge":false,"is_deleted":false,"isLayer3":true,"interface":"gt0","up":false,"pending":false,"available":true,"autostart":false,"dynamic":false,"proto":"gretap","data":{},"errors":[{"subsystem":"gretap","code":"MISSING_PEER_ADDRESS"}]}
L1609: Err: rc: 1684, Empty key, OR saepk:0
L1610: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1611: Err: rc: 1684, Empty key, OR saepk:0
L1612: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1613: Err: rc: 1684, Empty key, OR saepk:0
L1614: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1615: WLSSK (73) restart done
L1616: WLSSK (73) init done
L1617: WLSSK (75) restart 15
L1618: Err: rc: 1684, Empty key, OR saepk:0
L1619: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1620: Err: rc: 1684, Empty key, OR saepk:0
L1621: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1622: Err: rc: 1684, Empty key, OR saepk:0
L1623: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1624: WLSSK (106) restart done
L1625: WLSSK (106) restart 0
L1626: Err: rc: 1684, Empty key, OR saepk:0
L1627: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0
L1628: Err: rc: 1684, Empty key, OR saepk:0
L1629: Err: rc: 3665: conversion fn returned err for sae_password in iface wl0.1
L1630: Err: rc: 1684, Empty key, OR saepk:0
L1631: Err: rc: 3665: conversion fn returned err for sae_password in iface wl1
L1632: WLSSK (130) restart done
```
