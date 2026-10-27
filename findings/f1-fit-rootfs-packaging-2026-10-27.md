# FIT packaging of a SquashFS rootfs (offline) — 2026-10-27

## Scope and status

Offline only. No device contact, no TFTP, no UART write, no flash. The FIT image below was built and checked on the host, not sent to the router.

**Result:** `scripts/build_f1_fit_skeleton.py` gained a `--rootfs <squashfs>` option. A FIT with `/images/rootfs` and `config-1:rootfs = "rootfs"` builds and round-trips in the builder's own parser. Two images were built: a shadow-only stub (`fit-rootfs-shadow.itb`) and a stub with a cross-built dropbear and an altered shadow (`fit-rootfs-dropbear-shadow.itb`, see the later section). Neither is a full root filesystem, and neither is known to boot.

## Later update: dropbear packaged (same day)

The earlier denial was retried at the user's request, in smaller steps (download, unpack, configure, build). Each step succeeded.

- Source: `dropbear-2026.94.tar.bz2` from matt.ucc.asn.au, sha256 `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81` (REPORTED: the tarball was not checked against an upstream signature).
- Build: `CC=aarch64-linux-gnu-gcc LDFLAGS=-static ./configure --host=aarch64-linux-gnu --disable-zlib --disable-lastlog --disable-utmp --disable-utmpx --disable-wtmp --disable-wtmpx --disable-loginfunc --disable-pututxline --disable-pam`, then `make PROGRAMS="dropbear dropbearkey"`. The build exited 0. The only messages were static-link linker warnings.
- VERIFIED: `file` reports both binaries as `ELF 64-bit LSB executable, ARM aarch64, statically linked`.
  - `dropbear` sha256 `caa60f96fc6b5b1d6f1379864a30ebb5255eec1f2bb22836fe4dd37cd0ea2771`
  - `dropbearkey` sha256 `39b6df8e0d6eee5d7fcb45e0b5dbd8f11fb3ed72b33b28eddf43c7be5d81c206`
- VERIFIED: the squashfs `artifacts/rootfs-build/rootfs-dropbear-shadow.squashfs` (sha256 `542f9987…3a46af74`) contains `usr/sbin/dropbear`, `usr/bin/dropbearkey` and `etc/shadow`. unsquashfs extraction reproduces both binary hashes and the shadow file byte-for-byte.
- VERIFIED: the FIT `fit-rootfs-dropbear-shadow.itb` (3,495,040 bytes) embeds that squashfs byte-for-byte, its stored sha256 matches, `config-1:rootfs = 'rootfs'`, and there is no `/images/bootfs` member.
- **Not verified:** the binaries were not executed. No aarch64 emulator (`qemu-aarch64`) is installed on this host. Whether dropbear runs on the device is UNKNOWN.
- **Not done:** no host keys were generated or packaged. Dropbear needs `/etc/dropbear` host keys, and these were left for the device to create at runtime.

## What changed

- `scripts/build_f1_fit_skeleton.py`
  - `build_standard_fit_skeleton(rootfs_data=...)` adds `/images/rootfs` (`type = "filesystem"`, `compression = "none"`, sha256 `hash-1`) and sets `config-1:rootfs = "rootfs"`.
  - No `bootfs` member is added. The `kernel-1` dummy payload is still present but is not referenced by any U-Boot member name (see Limits).
  - `--rootfs` is rejected unless `--mode standard`, and the input must start with the SquashFS magic `hsqs`.
- `scripts/test_build_f1_fit_skeleton.py`: three new tests (rootfs round-trip with type, compression, hash and config reference; no rootfs member when not requested; exact-length payload with FDT padding). `python3 scripts/test_build_f1_fit_skeleton.py` → 8 tests OK.

## Why `rootfs` must be the config property name

From `findings/f1-bootp-lan-2026-10-13.md` Addendum 8 (UART log `artifacts/bootp/live-mac/session-20261027-190854.log`):

- VERIFIED from the log: U-Boot searches `config-1` for the names `bootfs`, `rootfs`, `loader`, `rootfs_data`, `ramfs_rd`. For each it prints `... not found in configuration config-1 ...skipping!` when absent. The names come from the log text, not from source.
- DERIVED: the config property `rootfs = "rootfs"` is the lookup that would select a `rootfs` image node. This was **not tested** with a rootfs present. In the 19:08 run every member was absent.

## Build (VERIFIED, offline)

Commands run from the repository root. Outputs are in `artifacts/rootfs-build/` (gitignored).

```bash
mkdir -p artifacts/rootfs-build/stage/etc
# root hash: openssl sha512crypt, random lab password stored in artifacts/secrets/f1-rootfs-lab-root.password (0600, not printed)
printf 'root:%s:19000:0:99999:7:::\n' "$(openssl passwd -6 -salt <16-hex> "$(cat artifacts/secrets/f1-rootfs-lab-root.password)")" > artifacts/rootfs-build/stage/etc/shadow
mksquashfs artifacts/rootfs-build/stage artifacts/rootfs-build/rootfs-shadow.squashfs -comp gzip -all-root -noappend -no-xattrs -no-progress
python3 scripts/build_f1_fit_skeleton.py --out artifacts/rootfs-build/fit-rootfs-shadow.itb --rootfs artifacts/rootfs-build/rootfs-shadow.squashfs
python3 scripts/build_f1_fit_skeleton.py --inspect artifacts/rootfs-build/fit-rootfs-shadow.itb
```

Tool versions: mksquashfs/unsquashfs from `/opt/homebrew/bin` (version not recorded); openssl from `/opt/homebrew/bin`.

| Check | Result |
| --- | --- |
| `unsquashfs -l rootfs-shadow.squashfs` | `squashfs-root/etc/shadow` only |
| Source squashfs | 4096 bytes, `shasum -a 256` = `5a159889…e634f6` |
| FIT `/images/rootfs:data` length and sha256 (via `FdtReader`) | 4096, `5a159889…e634f6` — equals the source file hash (VERIFIED, independent `shasum`) |
| FIT `/images/rootfs/hash-1:value` | equals sha256 of the data (VERIFIED) |
| FIT `/configurations/config-1:rootfs` | `'rootfs'` (VERIFIED) |
| FIT header magic / totalsize | `0xd00dfeed`, 5248 bytes = file length (VERIFIED) |
| Shadow hash reproduces from the stored lab password | `openssl passwd -6 -salt <stored salt>` equals the stored field (VERIFIED; password value not recorded in this file) |
| Negative: non-squashfs `--rootfs` | exit 1, `does not start with SquashFS magic 'hsqs'` |
| Negative: `--rootfs` with `--mode minimal` | exit 1, `requires --mode standard` |

## Blocked

- **Dropbear:** resolved in the later update above. The first attempt was denied by the auto-mode classifier. A retry at the user's request succeeded.
- **Base rootfs:** no decrypted or dumped 23.1.b `rootfs2` exists (see `findings/f1-rootfs-key-l598-2026-10-27.md`). The squashfs above therefore contains only `etc/shadow`. It is not a root filesystem and has no init, libraries, or device config.

## What was not shown

- Not flashed. No device was contacted in this pass.
- Not known to boot. The kernel command line on the device maps the rootfs through `verity` (`/dev/ubiblock0_6`) and then `crypt` (`aes-xts-plain64`). A plaintext squashfs is expected to fail at those layers. Whether U-Boot's bundle path writes plaintext or applies that encryption/verity is unknown. Not tested.
- Not an independent FIT parser check. `dtc`, `fdtget` and `fdtdump` are not installed on this host. The structure was checked only with the builder's own `FdtReader` plus the external hash and magic checks above. A second parser is still needed.
- Flashing a `rootfs` member that U-Boot finds in config would overwrite the rootfs volume. The effect on the device's fallback bank is unknown. Treat any flash as potentially bricking and do it only as a deliberate, separate step.

## Correction to Addendum 8

`findings/f1-bootp-lan-2026-10-13.md` Addendum 8 said the recovery path was a "clean, 100% reliable arbitrary rootfs flashing exploit". The UART log shows every member skipped (`not found in configuration config-1 ...skipping!`). The only state change was the UBI metadata bank-sequence rewrite. No partition was written. See the correction added to that file.

## Reproduction

```bash
python3 scripts/test_build_f1_fit_skeleton.py
python3 scripts/build_f1_fit_skeleton.py --inspect artifacts/rootfs-build/fit-rootfs-shadow.itb
unsquashfs -l artifacts/rootfs-build/rootfs-shadow.squashfs
shasum -a 256 artifacts/rootfs-build/rootfs-shadow.squashfs
```

## Next highest-value test (offline)

1. Obtain an aarch64 dropbear binary by a route the user has approved, then rebuild the staging tree and FIT.
2. Cross-check the FIT with an independent parser (install `dtc`, then `fdtdump` and `fdtget -t x … /images/rootfs data`).
3. Find the 23.1.b partition layout (`ubinfo`/UBI volume table, or the bundle template in the boot log) to see whether `rootfs` is written as plaintext or re-encrypted. This decides whether a stub can ever boot.

## Independent FIT parse with dtc (2026-10-27, later)

Closes the "independent FIT parser" gap noted above. The parser is `dtc` built from kernel.org source, not Homebrew.

- **Source:** `cdn.kernel.org/pub/software/utils/dtc/dtc-1.8.1.tar.xz`, sha256 `23526015a6f1550e0541a53fe7acea1b5a11e3697cdf3a3bdc076abc38f6045d` (VERIFIED hash only). The `.sign` file was downloaded, but the PGP signature was **not** checked because `gpg` is not installed.
- **Build:** `make NO_PYTHON=1` in `dtc-1.8.1/`, exit 0, using system bison 2.3 and flex 2.6.4. `dtc --version` reports `DTC 1.8.1`.
- **Brew:** the `brew install dtc` background job was cancelled. Its bottle downloads go through `ghcr.io`, which does not connect from this network (see the connectivity notes in the chat record).

Results, with `dtc -I dtb -O dts` as the decoder:

| Image | dtc decode | rootfs bytes vs source squashfs |
| --- | --- | --- |
| `fit-rootfs-shadow.itb` | exit 0 | `rootfs` data equals `rootfs-shadow.squashfs` (4096 B, sha256 `5a159889…e634f6`) |
| `fit-rootfs-dropbear-shadow.itb` | exit 0 | `rootfs` data equals `rootfs-dropbear-shadow.squashfs` (3,493,888 B, sha256 `542f9987…3a46af74`) |

- **VERIFIED:** both FITs decode with the second parser. `config-1` has `rootfs = "rootfs"`, and `bootfs` is absent in both.
- **VERIFIED negative control:** a copy with a zeroed first byte is rejected with `FATAL ERROR: Blob has incorrect magic number`.
- **Warnings (not errors):** `node_name_vs_property_name` for `/compatible` and `/configurations/config-1/compatible`. These come from the builder's layout, which uses a property and a subnode with the same name. U-Boot's `compatible`-node handling accepted that layout on the device, per Addendum 7.
- **Not done:** `fdtget` would not run, since only `libfdt.a` was built and the dylib was missing. The byte check went through the `dtc` decode text instead. The decode is still independent of `FdtReader`.
- **Still open:** whether U-Boot writes the `rootfs` member as plaintext or re-encrypts it. Its source is unreachable from this network.

## Write path of the bundle `rootfs` member (vendor U-Boot source, 2026-10-27)

Source: `RMerl/asuswrt-merlin.ng`, `release/src-rt-5.04behnd.4916/bootloaders/u-boot-2019.07/board/broadcom/bcmbca/`. The repo head was commit `ca72a61f8bc5ef920e29d63d53d9864262208f0c` when queried. The raw files were fetched from `main` just before that query, so they may not be from exactly that commit. Local copies and hashes: `artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/` (`SHA256SUMS`, gitignored). The device banner (`U-Boot 2019.07 (Jan 06 2025)`) has not been matched to this tree.

- **VERIFIED (source):** `flash_upgrade_img_bundle()` (`sdk_test_commands.c:2597`) verifies all bundle hashes, checks `compatible`, then loops over `fn_table` (`bootfs`, `rootfs`, then `loader` and the others). For each member it calls `get_binary_from_bundle()` and `continue`s when the member is missing. That matches the device log's `... not found ...skipping!` lines.
- **VERIFIED (source):** `flash_rootfs()` (`sdk_test_commands.c:1914`) selects NAND on NAND media, unless `CONFIG_BCMBCA_VFBIO` is set. `flash_rootfs_nand()` (`:1171`) does `ubi part image`, removes `rootfs<N>` if present, runs `ubi create rootfs<N>` with the size, then `ubi write <addr> rootfs<N> <size>`. The bytes are written **raw**, with no encryption and no verity step.
- **VERIFIED (source):** `bcm_handle_mapper()` (`sdk_test_commands.c:1491`) reads the `/brcm_rootfs_encrypt` node from the **bootfs FIT** (`fit` argument). If that node is missing it returns 1. Otherwise it builds the device-mapper string from that node's `mapper` template and substitutes `%DEVICE%` and `%IMAGE_KEY%`. The rootfs layering on the device (verity, then crypt) therefore comes from the boot FIT, not from the rootfs data.
- **DERIVED:** the device's UBI layout (`rootfs2 = ubi0:6`, `ubiblock0_6` created from it, bank switch on commit) fits the NAND path. This does not prove `CONFIG_BCMBCA_VFBIO` is unset on the F1.
- **DERIVED:** a rootfs member goes into the inactive bank's `rootfs<N>` volume. The 2026-10-27 bank switch (Bank 2 to Bank 1) suggests that bank is the target. The write itself was not observed.
- **DERIVED:** a plaintext squashfs at that volume has no verity or crypt layer that matches it, so the mapper should fail at the verity or crypt layer, not at squashfs. Whether the device then falls back to the other bank is **UNKNOWN**. The fallback logic was not traced.
- **Not shown:** any boot with a written `rootfs` member. The `CONFIG_BCMBCA_VFBIO` value for this board, and the `get_img_index_for_upgrade()` logic, were not checked.

## Independent FIT parse with dtc: status

The "still open" item in the dtc section above is partly answered: the write path is now traced in source. The remaining open item is whether the device's current `bootfs` FIT carries a `/brcm_rootfs_encrypt` node with a verity/crypt `mapper`. That node is in the bootfs, which this work has not read.

## Device bootfs FIT and /brcm_rootfs_encrypt: status (2026-10-27)

- **BLOCKED:** the device's current bootfs FIT was **not** read. It is not in `artifacts/` (no bootfs dump exists locally). No shell or U-Boot prompt was reachable. The UART logs show only the `*** Press b to enter BOOT-P ***` prompt (14 occurrences) and no autoboot interrupt. BOOT-P is a recovery path that serves files to the device, not a read path.
- **VERIFIED (device log, masked):** the device's kernel command line builds this device-mapper table (`artifacts/uart/2026-10-27/router-boot-20261027-010457-82769.log`):
  `lroot: 0 108184 verity 1 /dev/ubiblock0_6 /dev/ubiblock0_6 512 512 108184 108185 sha256 <root digest, masked> <salt, masked> 1 check_at_most_once`, then `lroot2: 0 108184 crypt aes-xts-plain64 <key, masked> 0 /dev/dm-0 0`.
  So verity (sha256, on the rootfs2 UBI volume) and then AES-XTS crypt are both active on the device. The root digest and key are masked, and the `/brcm_rootfs_encrypt` node has not been read to confirm where the digest comes from.
- **DERIVED:** the verity root digest is set by U-Boot's `bcm_handle_mapper()` from the bootfs FIT (see the source trace above). A plaintext stub cannot match it, so verity should reject the volume before any squashfs parsing. Whether the device then falls back to the other bank is still UNKNOWN.
- **DERIVED:** because crypt sits above verity, the data on flash must be the AES-XTS ciphertext plus a matching hash tree, both made at build time. A plaintext squashfs written with `ubi write` cannot be correct for this mapping, so the stub route does not produce a bootable rootfs.
- **Next step (needs a decision):** read the bootfs. Options are a U-Boot console or shell on UART if one can be reached, or a root shell on the device. Either is a live-device action and needs your approval. The other route is the masked dm-crypt key, which the earlier disproof passes could not verify.

## Passive UART check for a U-Boot console (2026-10-27, live device)

- **Live, read-only:** a logger received bytes from `/dev/cu.usbserial-0001` at 115200 and sent nothing. The router was power-cycled by the owner. Log: `artifacts/uart/2026-10-27/passive-20261027-195325.log` (48,804 B at 19:54).
- **VERIFIED:** the boot runs U-Boot SPL, then TPL, then U-Boot 2019.07 (Jan 06 2025). The line `*** Press b to enter BOOT-P ***` appears, and then boot continues with **no** autoboot countdown and no \"Hit any key\" or \"stop autoboot\" text. No `=>` console prompt appears.
- **VERIFIED:** this boot used **Bank 1** (`Booting : Bank 1`, `Read 8615821 bytes from volume bootfs1`). The previous captured boots used Bank 2. The change is consistent with the 19:09 BOOT-P test, which switched the bank order to `3 5`.
- **VERIFIED:** Linux 4.19.235 starts, the overlay mounts `rootfs_data` (ubi0:20), and boot reaches userspace.
- **Result:** no U-Boot console was reachable by UART on this boot. Pressing a key at the BOOT-P window only reaches BOOT-P, which serves files and does not read flash. The bootfs FIT is still **not read**. Nothing was sent to the device.
- **Not shown:** whether any other interrupt (for example a longer key window or a different button) gives a console.
