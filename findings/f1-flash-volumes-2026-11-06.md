# Flash volumes pulled over SSH root (2026-11-06)

## What this is

**VERIFIED** from `ssh root@192.168.1.1`: `/proc/mtd` and `ubinfo -a`. The copies are under `artifacts/firmware/flash-2026-11-06/` (gitignored). They are the on-flash volumes. They are not one file U-Boot can TFTP back as a recovery image.

`/rom` is the decrypted squashfs (`/dev/dm-1`). Its `bootfs` directory is an empty placeholder. The kernel and U-Boot are inside the `bootfs1` FIT.

## Partition map

| Device | Size | Name |
| --- | --- | --- |
| mtd0 | 512 MiB | `brcmnand.0` (the whole NAND; not dumped) |
| mtd1 | 2 MiB | `loader` |
| mtd2 | 6 MiB | `dri` |
| mtd5 | 502 MiB | `image` (UBI container; volumes dumped instead) |
| ubi0_1 / ubi0_2 | 272 B each | `metadata1`, `metadata2` |
| ubi0_3 | 8,615,821 B | `bootfs1` |
| ubi0_4 | 54,853,632 B | `rootfs1` |
| ubi0_5 | 8,615,825 B | `bootfs2` |
| ubi0_6 | 60,186,624 B | `rootfs2` |

Both metadata volumes say `COMMITTED=1`, `VALID=1,2`, `SEQ=8,7`.

## Where the kernel and bootloader are

**VERIFIED** by walking the FIT in `bootfs1.ubi.bin`.

| Piece | File | Offset in `bootfs1.ubi.bin` | Length | What the bytes are |
| --- | --- | --- | --- | --- |
| ARM Trusted Firmware | `bootfs1-atf.bin` | 20225 | 57441 | FIT image `atf` |
| U-Boot | `bootfs1-uboot.bin` | 77669 | 3,298,984 | FIT image `uboot`, description `U-Boot`. First instruction is an AArch64 branch, not an ELF |
| Kernel | `bootfs1-kernel.lzma` | 3383329 | 3,678,822 | FIT image `kernel`, description `4.19 kernel`, LZMA |
| Uncompressed kernel | `bootfs1-kernel.Image` | carved from the LZMA | 10,375,176 | ARM64 Image (`ARMd` at offset 56) |
| This board's DTB | `bootfs1-fdt-GCNT-X.dtb` | 8283185 | 54555 | FIT image `fdt_GCNT-X` |

`bootfs1` version string: `23.1.b.0448-7241010-20260205081324`, image `5044p1GCNT-X0062231`. `bootfs2` version string: `23.1.b.0448-7241017-20260223134332`. Same image id, later package date.

`loader.mtd1.bin` is the 2 MiB loader partition. It contains the strings `SPL`, `TPL`, and `U-Boot`, and a Broadcom `bcm96856` device tree at offset `0x17620`. `dri.mtd2.bin` is an older FIT (`23.1.b.dev-7220000-20240819075244`) that also contains a U-Boot image.

## Rootfs volumes

**VERIFIED:** `rootfs1.ubi.bin` and `rootfs2.ubi.bin` have no FIT, squashfs, or UBIFS magic. The first 4 KiB of each measures entropy 7.96. The `bootfs1` FIT `brcm_rootfs_encrypt` node describes dm-verity plus AES-XTS, with the decrypted filesystem mounted as squashfs on `/dev/dm-1`.

**VERIFIED (decrypt, bank 1).** The running command line has `ubi.block=0,4` and `aes-xts-plain64` with a 32-byte key (64 hex characters). That key is stored only in `artifacts/secrets/rootfs-xts.key` (mode 0600). AES-XTS, sector size 512, little-endian sector tweak, first half of the key as the data key, decrypts the first 98,312 sectors of `rootfs1.ubi.bin`. The result is `rootfs1.squashfs` (50,335,744 bytes, SHA-256 `79870839a95ed6c945a362fb0e42fa6ce5a4acf933ed1a1989d799a160e3bcb3`). `unsquashfs -s` reports SquashFS 4.0, xz, 48.00 MiB, created Thu Feb 5 09:13:26 2026. `etc/image_version` is `5044p1GCNT-X0062231`. `bin/restricted_shell` matches the copy in `rom.tar.gz`.

**VERIFIED (decrypt, bank 2).** The bank-1 key does not open `rootfs2`. The older 32-byte key printed on UART after `SUCCESS:Found /trust/key_image_aes` (14 of 16 captured boots, for example `artifacts/uart/2026-10-12/router-boot-20261012-202834-76414.log`) does. It is a different value from the live command-line key and is stored only in `artifacts/secrets/rootfs2-xts.key`. Decrypting the first 108,184 sectors, the length in the `bootfs2` mapper string, yields `rootfs2.squashfs` (55,390,208 bytes, SHA-256 `16c7d9be858e4ac639f3e49d0ff0d8df20ee72112a078d247d7d6518b7308546`). SquashFS 4.0, xz, 52.82 MiB, created Mon Feb 23 14:43:41 2026, 7,671 inodes. `etc/image_version` is also `5044p1GCNT-X0062231`. That timestamp matches the `bootfs2` package string `23.1.b.0448-7241017-20260223134332`.

The FIT `tch_keys/key1` node (`emek`, 32 bytes) does not decrypt eRIP item `0121` under AES-CBC with a strict PKCS#7 check. The old `r2secr` module was not loaded.

**VERIFIED (OSCK).** `ripdrv` is loaded at `0xffffff8000904000`. Its `.bss` symbol `eck` (24 bytes at section offset `0x1c0`) holds a length of 16 and a pointer to the next BSS buffer. Those 16 bytes, read through `/proc/kcore`, decrypt item `0121` from the eRIP backup: AES-128-CBC, IV = first 16 bytes of the 320-byte item, strict PKCS#7. Plaintext is 288 bytes, saved only at `artifacts/secrets/osck.bin` (mode 0600). The key bytes are not written here.

**VERIFIED (signature).** The 288 bytes are a 32-byte key plus a 256-byte signature. RSA-PSS SHA-256, salt length 32, exponent 65537, checks that signature. The modulus is the first 256 bytes of cleartext eRIP item `011E` (512 bytes total). The signed message is the item id as a big-endian `uint16` (`0x0121`) followed by the 32-byte key. The 32-byte key alone is `artifacts/secrets/osck-key.bin` (mode 0600).

The same AES key and the same signature check open every encrypted item in the backup: 14 of 14, all RSA-PSS ok. Plaintext is under `artifacts/secrets/erip-decrypted/` (mode 0600). Item `0108` is 64 bytes of data plus the signature, and those 64 bytes match `/proc/rip/0108` once the trailing newline is dropped.

**VERIFIED (19.x RBI).** That 32-byte OSCK unwraps `artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`. `scripts/attempt_rbi_decrypt.py`'s first `0xB7` check returns `unwrap_ok`, then the payload inflates and the inner `0xB0` layer is a 62,914,560-byte image (exactly 60 MiB), SHA-256 `f3391cf964f15faa22f9ff3fbc590f034d2b54ae2269cbf81a4177cb697bd838`, saved as `artifacts/firmware/rbi-19x-inner.bin`. A SquashFS 4.0 xz filesystem sits at offset `0x1400000`, created Mon Jan 18 17:30:12 2021, 28.36 MiB, 7,956 inodes. A device tree at `0x306008c` has `root=/dev/mtdblock1` and `rootfs_offset=0x01400000`. The 71 earlier community and boot-log guesses were the wrong key. This one is this unit's OSCK, and it opens that reference image. Do not flash the 19.x image onto this board.

The FIT also has a `security` node and key nodes. Those values are not copied here.

## Whole NAND

**VERIFIED.** `dd if=/dev/mtd0 bs=1048576` returned 512+0 records, 536,870,912 bytes, saved as `artifacts/firmware/flash-2026-11-06/nand.mtd0.bin`. SHA-256 `271b94f970535510ebe2b5c27d232e57917618ed1b744e2b11b89f04f4aa1feb`.

The file matches the pieces already copied: bytes `0x000000`–`0x200000` are `loader.mtd1.bin`, and bytes `0x200000`–`0x800000` are `dri.mtd2.bin`. Offset `0xa00000` starts with `UBI#`, which is the `image` partition (`mtd5`, 0x1f600000 bytes). Layout of the chip:

| Offset | Length | Partition |
| --- | --- | --- |
| `0x000000` | 2 MiB | `loader` |
| `0x200000` | 6 MiB | `dri` |
| `0x800000` | 1 MiB | `eripv2_bak1` |
| `0x900000` | 1 MiB | `eripv2_bak2` |
| `0xa00000` | 502 MiB | `image` (UBI: bootfs, rootfs, overlay, and the rest) |

This is the ECC-corrected data from `/dev/mtd0`, not a spare-byte (OOB) dump. It is not itself a FIT U-Boot can TFTP.

## Recovery bundles

**VERIFIED (offline, not flashed).** `scripts/build_f1_fit_skeleton.py`'s standard builder packed each dumped bank into the FIT shape `flash_upgrade_img_bundle()` writes. `scripts/validate_f1_fit_bundle.py` reports both structurally valid, 0 warnings.

| File | SHA-256 | What it writes |
| --- | --- | --- |
| `artifacts/firmware/GCNT-X-23.1.b-bank1.itb` (63,470,903 bytes) | `f0c6fd4a0bb485cb47b089ccaea4e7f6672c4dda2b9f89e3a1eace4404c70422` | `bootfs1.ubi.bin` + `rootfs1.ubi.bin` |
| `artifacts/firmware/GCNT-X-23.1.b-bank2.itb` (68,803,903 bytes) | `df94efe0dc54d69edaf7afaec222aba1d03a830a712b03247223668f1ec200ff` | `bootfs2.ubi.bin` + `rootfs2.ubi.bin` |

The inner bootfs bytes are the vendor FIT from the NAND dump, including the `GLED` container that follows the FDT. The rootfs bytes are the encrypted volume, which is what `/brcm_rootfs_encrypt` expects. The upgrade path writes the inactive bank and then commits it. A bank change runs the factory-reset path and can erase the overlay, including the SSH root added there. These files were not sent to the router.

## What was not dumped

`rootfs_data` (ubi0_20) and `opt` (ubi0_21) were not copied again as separate volumes; both sit inside the `image` UBI at `0xa00000`. The live `mtd14` eripv2 device was busy earlier; the backup copies are at `0x800000` and `0x900000` in this dump.
