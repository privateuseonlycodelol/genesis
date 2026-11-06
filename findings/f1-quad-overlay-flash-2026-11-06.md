# Quadruple-vector overlay flash, cron hook, and config decrypt — 2026-11-06

## Result

The rebuilt `artifacts/firmware/overlay-injection-bundle.itb` (13,968,537 bytes) was flashed. The cron shadow of `obuspa_retriever.sh` ran as root and wrote `/proc/rip/*` into syslog. The first 64 bytes of item `0108` verify and decrypt the saved config export.

**VERIFIED**

- Command: `python3 scripts/f1_bootp_tftp_mac.py --iface en10 --no-set-ip --no-pcap --allow-non-root --timeout 300 --uart /dev/cu.usbserial-0001 --file artifacts/firmware/overlay-injection-bundle.itb --reboot`
- Web reboot: `session: srp_login`, `restart POST: HTTP 200`.
- TFTP: all 27,283 blocks ACKed at 19:11:21. Log: `artifacts/bootp/sessions/session-20261106-191039.log`.
- U-Boot: SHA-256 for `kernel-1` and `rootfs_data` passed. Wrote 13,967,360 bytes to dynamic volume `rootfs_data` (17,113,088 bytes). `Getting committed 1 valid 1,2 seq 6,5` then `Setting committed 2 valid 1,2 seq 6,7`.
- After that reset the same process pressed `b` again (`SENT 'b' (#2)` at 19:11:46). BOOTP was not being served during the post-transfer sleep, so U-Boot logged `BOOTP Reply timeout` and reset. The process was stopped. A later boot reached Linux userspace (`WLSSK`, `OCSD`). Watch log: `artifacts/uart/warm-reboot-20261106-191500/console.log`.
- After boot: TCP 80 open, TCP 23 connection refused, TCP 22 open with banner `SSH-2.0-dropbear` and `Permission denied (publickey,password)` for `root`, `User`, and `admin` using the web admin password.
- One syslog export (`scripts/f1_export_log_modal_once.py --confirm --out-name quad-overlay-boot-20261106`): HTTP 200, 69,300 bytes, window 19:18:41–19:19:03. `crond` ran `/usr/share/transformer/scripts/obuspa_retriever.sh` as root, and that invocation logged `GENESIS_KEYS` for `/proc/rip/0108`, `/proc/rip/0120`, `/proc/rip/011a`, and many other ids. That tag exists only in the staged cron hook, so the hook ran.
- Item `0108` reconstructed from that syslog line is 65 bytes. `scripts/decrypt_f1_config_export.py` uses the first 64. Against `artifacts/ui/readonly-control-20261012T021317Z/response-10.private`: `hmac_ok=true`, plaintext length 180776, `printable_ratio_head=1.0`, `contains_config_tag=false`. The plaintext is a UCI-style dump (`[*]` / `[section]` / `name=value`, 4888 lines). Private outputs: `artifacts/secrets/rip-0108.bin`, `artifacts/secrets/config-response-10.plain.private`. No `.rbi` URL in the plaintext. URL hosts include the already-known Telia ACS names (`acs.telia.com`, `acs.telia.lt`, `acs.dk.telia.net`, `acs.estpak.ee`, `acs.get.no`, `rgw.teliacompany.com`).

**DERIVED**

- Syslog `logger` lines are capped near 1040 characters. Item `0120` reconstructed to 197 bytes and the line ends mid-hexdump, so it is not a complete OSIK. Item `011a` is truncated the same way. Item `0108` fit in one line.

## REA

- `open_binary` on `artifacts/firmware/overlay-injection-bundle.itb` returned `unsupported binary format` (`file_format_rejected`). The FIT image is not an REA target on this host. `inspect_firmware_regions` requires Linux, Binwalk, and `prlimit`; this machine is macOS, so it was not run.
- `open_binary` on `tools/secr/r2secr.arm64.4.1.52.ko` succeeded. SHA-256 `12d30cc860a594c403ac0cb3060882db12d86a3c35b756a1a5bf22ea2a16d774`, ELF, arm64. `binary_overview` evidence `ev_a834f52219ad1365c9bfebf1363d8d173dc066bd2baa14afd7dca6b742f169a3`: 9 segments, 3 procedures, 14 strings. `list_strings` evidence `ev_91a394071aa2afc214de373b4e42b66b1365b105e4f72d11805421d3c8a4f4f6`: the strings are debug formats (`r2secr_struct`, `nextFreeItem`). This is the old 4.1.52 module, not the running 4.19.235 kernel. Session closed. It does not describe the live key dump.

## What was not shown

- No interactive root shell on UART, SSH, or telnet.
- `80_rtfd_restore` copy messages were not in the captured console slice. The cron hook running is the evidence the overlay file was executed.
- Item `0120` and `011a` are incomplete in this syslog window.
- Plaintext values were not copied into this finding.

## Second flash, same day (19:28Z)

The boot prompt watcher was changed so it sends `b` once per run. The cron hook was changed to log `/etc/shadow` and items `0120` and `011a` one hexdump line at a time. That bundle was flashed before the new hook needed to run.

**VERIFIED**

- `b` was sent once (`SENT 'b' (#1)` at 19:29:13). No second recovery entry. Log: `artifacts/bootp/sessions/session-20261106-192838.log`.
- TFTP completed, 27,283 blocks. `Setting committed 1 valid 1,2 seq 8,7`. `mount_root` ran `20_rtfd_remove` and `80_rtfd_restore`. Both `/overlay/bank_1` and `/overlay/bank_2` were reported missing.
- Enter on the serial console opened BusyBox ash as root: `uid=0(root)`, `Linux (none) 4.19.235 aarch64`. Prompt became `root@OpenWrt:/#`.
- Live `/etc/shadow` root field is a 101-character `$6$` SHA-512 crypt hash. `/rom/etc/shadow` root field is `*` (locked). OpenSSL `passwd -6` with the web admin password does not match the live hash. The hash file is `artifacts/secrets/shadow-root.hash`.
- `/proc/rip/0120` is 257 bytes. `/proc/rip/011a` is not a file.

## Root shell on SSH (19:38Z)

**VERIFIED.** The serial console was already `uid=0(root)`. Dropbear on `192.168.1.1:22` rejected logins with `User 'root' has invalid shell`. `/etc/passwd` says `/bin/sh`. `/etc/shells` listed only `/bin/ash` and `/bin/restricted_shell`. Appending `/bin/sh` made password login succeed: `ssh root@192.168.1.1` returned `uid=0(root)`.

`chpasswd` replaced the root shadow entry. The new hash matches `artifacts/secrets/f1-root.password` (mode 0600). The password is not written in this finding. An ed25519 public key was installed at `/etc/dropbear/authorized_keys` and `/root/.ssh/authorized_keys` (MD5 `1bef3eaeec3b2b5d5c083a74693c6937`) and was still rejected before the shell-list change; it was not retested after.

## Filesystem located (19:43Z)

**VERIFIED** over `ssh root@192.168.1.1`:

- Read-only firmware root is `/rom`, squashfs, 48.0M, 100% used, mounted from `/dev/root` (`/dev/dm-1`).
- Writable overlay is `/dev/ubi0_20` (UBIFS, volume 20) on `/overlay`, then `overlayfs` on `/` with `lowerdir=/`, `upperdir=/overlay/bank_1`, `workdir=/overlay/work`. `/overlay/bank_2` is absent. `/overlay/bank_1` exists.
- `/rom/etc/openwrt_release`: OpenWrt 21.02.1, `r16325-88151b8303`, target `brcmbca/bcm96856`, arch `arm_cortex-a53`. Kernel still `4.19.235` aarch64, built Tue Mar 11 05:27:32 UTC 2025.
- `/rom/etc/image_version` is `5044p1GCNT-X0062231`.
- The scripts that were missing locally are on the image: `/rom/lib/mount_root/` contains `00_overlay_bank_check.sh`, `00_rtfd_all`, `10_remove_due_to_upgrade`, `20_rtfd_remove`, `30_parameter_conversion`, `80_rtfd_restore`. `/rom/bin/restricted_shell` is 4916 bytes. `/rom/usr/lib/lua/clash-access-control.lua` is 3268 bytes. Both dated Feb 5 2026.

## Copies off the router (19:46 local)

**VERIFIED** over `ssh root@192.168.1.1`. Nothing below is a key, password, or hash.

- `artifacts/firmware/rom-2026-11-06/rom.tar.gz` is 61,895,232 bytes, gzip-clean, 7,411 members. BusyBox `tar` on the device rejected `--exclude`, so the stream is the firmware directories only (`bin`, `sbin`, `etc`, `lib`, `lib64`, `usr`, `www`, `webs`, `bootfs`, `data`, `custo`, `debug`, `airties-edge`). It contains `lib/mount_root/` (the six RTFD scripts), `bin/restricted_shell`, `usr/lib/lua/clash-access-control.lua`, `etc/image_version`, and `etc/cups/cupsd.conf`.
- `artifacts/secrets/device-2026-11-06/device-pull.tar` (mode 0600, 2,363,392 bytes) holds 94 `/proc/rip` items, `uci export` (150,648 bytes), and live `shadow`, `passwd`, `shells`, and `dropbear`. Saved sizes: `0108` 65 bytes, `0120` 257 bytes, `011a.cert` 4,868 bytes. There is no `0121` and no bare `011a`. A first `cp -a /proc/rip` aborted on `Input/output error` for the `signed` node; the saved set was copied per file.
- `dd` of `/dev/mtd14` and `/dev/mtdblock14` returned `Device or resource busy`. `mtd3` (`eripv2_bak1`) and `mtd4` (`eripv2_bak2`) are each 1,048,576 bytes and identical. The eRIP image is the first `0x3e000` bytes. `scripts/f1_erip_parser.py` (via `tools/venv`) finds 102 index records there. All 94 proc names are in that index. Also present, and absent from `/proc/rip`: `011f` (ECK, 304 bytes, not flagged encrypted), `0121` (OSCK, 320 bytes, flagged encrypted and signed), and `0620`–`0625`. The parser’s “valid” flag is false on every record, so that bit is not trusted. The 304-byte ECK item was not reduced to a 16-byte key, and OSCK was not decrypted.

`/etc/cups/cupsd.conf` matches `/rom/etc/cups/cupsd.conf` (1,052 bytes, MD5 `82b71646da074854501a4a45f45aee4e`). The file sets `Port 631`, allows `127.0.0.1` and `192.168.1.0/24` on `<Location />`, and sets `<Location /admin>` to `AuthType None` / `Allow From All`. It has no `<Policy>` block and does not set `WebInterface`. One GET each of `/` and `/admin/` from `192.168.1.100` still returned HTTP 403, 343 bytes.

The shell-list change and the new root password live in the writable overlay. A later RTFD wipe can remove them. The tarballs do not.

## Next

**Superseded 2026-11-06:** item `0121` is decrypted and its signature checks. See [f1-flash-volumes-2026-11-06.md](f1-flash-volumes-2026-11-06.md). The sentence below is the state when the backup was first copied.

The on-flash OSCK (`0121`, 320 bytes in the eRIP image) is still encrypted. The 16-byte ECK is not the raw `011f` blob.

**Superseded later the same night:** both rootfs volumes were copied and decrypted, and item `0121` was decrypted with the live `ripdrv` ECK to 288 bytes. See [f1-flash-volumes-2026-11-06.md](f1-flash-volumes-2026-11-06.md).
