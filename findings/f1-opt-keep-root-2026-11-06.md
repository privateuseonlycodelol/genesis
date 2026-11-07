# Opt-volume SSH restore — 2026-11-06

The overlay parking lot dies if an upgrade runs `ubi remove rootfs_data`. U-Boot's flasher commands name `rootfs_data`, `data`, `eripv2`, `bootfs`, `rootfs`, and `fit1`. They do not name `opt` (`ubi0_21`). `airlauncher-daemon` reads `/launcher/applications/application[@index=N]/executable` from `/airties-edge/etc/cdf/data.xml` on that volume and runs it with `execvp`.

## Installed

**VERIFIED, same evening, before this Mac left the LAN.** `/airties-edge` and the LCM upper path are the same file on `/dev/ubi0_21` (inode 1238).

- `/airties-edge/genesis/keep-root` is the script in `scripts/f1_keep_root.sh`. Mode 755.
- Beside it, mode 600 copies of the live `/etc/shadow` and `/etc/config/dropbear`, and mode 644 copies of `/etc/passwd` and `/etc/shells`. Those copies were not read back off the router.
- `data.xml` gained application index 10, name `keep-root`, enable true, log false, executable `/airties-edge/genesis/keep-root`. The previous ten applications are still there. `cloud-comm` index 2 is still `enable` false. The backup is `data.xml.bak-keep-root` on the same volume.
- `KEEP_ROOT_ONCE=1` ran the script and it exited 0, so it did not rewrite the live SSH files.

The script waits until `/etc/shadow` exists. If root is not a `$6$` hash, `/bin/sh` is missing from `/etc/shells`, or the dropbear UCI enable is not `1`, it copies the saved files back and restarts dropbear. Otherwise it does nothing. It then sleeps so the launcher does not treat an exit as a crash. That restore path was not run against a wiped overlay.

## Launcher

**VERIFIED and incomplete.** The running `airlauncher-daemon` (pid 18547) was killed so it would reread the file. A new one started only after `LD_LIBRARY_PATH=/airties-edge/lib`, because a bare start could not find `libacbus.so`. That process (pid 26434) was still in `--dormant` and had not started `keep-root`. The programs the old launcher had been supervising (`multiap_controller`, `air-steer-ng-daemon`, and the other enabled Airties applications) were not in the process list after the kill. `hostapd` pids 16174 and 14927 were still there, and `dnsproxy` was up. No wake message was delivered. The string next to the dormant wait is `wake` on `com.airties.launcher.*`. This pass did not find the sender.

This Mac then moved to the phone hotspot (`172.20.10.2`). Nothing after that was checked.

## Upgrade scenarios (read from the live image, 2026-11-07; no upgrade was run)

Board is `brcm,brcm-v8A`, booted bank 1. `/rom/lib/upgrade/platform.sh` takes the `bcm_flasher` branch for that board. After a successful flash it renames `/overlay/<inactive-bank>` to `*.remove_due_to_upgrade` and creates `/overlay/data.remove_due_to_upgrade`. `/rom/lib/mount_root/10_remove_due_to_upgrade` deletes those overlay markers. `/rom/lib/mount_root/20_rtfd_remove` deletes the overlay bank named by `/overlay/remove_due_to_rtfd`. None of these scripts mention `opt` or `ubi0_21`. Live volumes are `rootfs_data` = ubi0_20 mounted on `/overlay`, and `opt` = ubi0_21 mounted on `/opt/lcm.technicolor.com`. The device U-Boot log's bundle members are `bootfs`, `rootfs`, `loader`, `rootfs_data`, and `ramfs_rd`. `opt` is not one of them.

`keep-root` was running at this read (the launcher is not in the dormant state seen when it was killed by hand).

| Scenario | What the code does to the hook | Would SSH come back |
| --- | --- | --- |
| Normal sysupgrade on this board | Inactive `bootfs`/`rootfs` replaced. That bank's overlay dir and the `data` volume are marked for deletion. `opt` is not named. | Files remain. On the next full boot the current launcher would start the script. The deployed script restores when the root hash or shell differs from the saved copies, `/bin/sh` is missing, dropbear is disabled, or password, root-password, or root login is off. That full restore has not been run against a wiped overlay. |
| Factory reset that only removes an overlay bank | `20_rtfd_remove` deletes that bank directory under `/overlay`. | The `opt` file and `data.xml` entry stay. Same launcher condition as above. A reset that also formats `ubi0_21` was not found in these scripts and was not run. |
| Generic OpenWrt `nand.sh` path | `ubirmvol` of `rootfs_data`, and `ubiformat` of the whole image MTD if given a UBI image. | This board's `platform_do_upgrade` does not call that path. A full `ubiformat` of the image MTD would destroy `opt` with every other volume. |
| U-Boot recovery of a bundle with the members listed above | Writes those members. Does not name `opt`. | Same as the sysupgrade row, provided the new rootfs still starts `airlauncher-daemon` on `/airties-edge/etc/cdf/data.xml`. |
| Image or LCM update that replaces `data.xml` or drops the launcher | The application entry is only started from that file. | The script can remain on disk and never run. |

## Effectiveness (live read, 2026-11-07; no files rewritten)

The launcher is the parent of `keep-root` on this boot, so a full start does reach the script. The four saved files are byte-identical to `/etc/shadow`, `/etc/passwd`, `/etc/shells`, and `/etc/config/dropbear`. Root's live and saved password field is a `$6$` hash, the shell is `/bin/sh`, and `/bin/sh` is a symlink to busybox. `/etc/shells` lists `/bin/ash`, `/bin/restricted_shell`, and `/bin/sh`. Dropbear UCI has `enable=1`, `PasswordAuth=on`, `RootPasswordAuth=on`, `Interface=lan`, `Port=22`. `RootLogin` is unset; the init script defaults it to 1. The init script turns password login off with `-s` when `PasswordAuth` is 0, root password login off with `-g` when `RootPasswordAuth` is 0, and root login off with `-w` when `RootLogin` is 0.

The script at the time of this read never looks at those three flags. It treats SSH as healthy when the root field matches `^root:$6$`, `/etc/shells` has a line `/bin/sh`, and `dropbear.@dropbear[0].enable` is `1`. An image that keeps those three and sets `RootPasswordAuth`, `PasswordAuth`, or `RootLogin` to 0 is left unchanged. An image that ships its own `$6$` root hash, with `/bin/sh` in shells and dropbear enabled, is also left unchanged, so the saved password is not put back.

The restore branch copies whole files. It does not edit the root line. A successful restore replaces every account in `passwd` and `shadow`, and replaces the dropbear config, including `Interface=lan`. `cp` failures are ignored. If `/etc/init.d/dropbear` is missing, the files are copied and nothing is restarted. The check runs once. After that the process sleeps for an hour at a time and does not look again. If `/etc/shadow` is still absent after 60 seconds, the script exits 0. `KEEP_ROOT_ONCE=1` has exited 0 against an already-good system. The branch that copies the saved files onto a broken system has not been run.

The shells check does match the failure that blocked SSH on 2026-11-06: dropbear rejected root because `/etc/passwd` said `/bin/sh` and `/etc/shells` did not list it. That is the one broken state the old script was built to notice.

## Fix (deployed 2026-11-07)

`scripts/f1_keep_root.sh` was replaced on the router (`/airties-edge/genesis/keep-root`, 3436 bytes; previous bytes kept as `keep-root.bak-20261107`). The running copy is process 1981, parent `airlauncher-daemon` 19943.

The script now compares the live root hash with the saved root hash, the live root shell with the saved shell, `/bin/sh` in `/etc/shells`, `enable=1`, and treats `PasswordAuth`, `RootPasswordAuth`, and `RootLogin` as broken when they are `0` or `off`. Empty `RootLogin` stays acceptable because the init script defaults it on. A repair replaces only the root field in `shadow` and the root shell in `passwd`, appends `/bin/sh` when it is missing, and sets those dropbear options from the saved config. It then restarts dropbear. The loop repeats every 60 seconds. `cp` has to succeed before the temp file replaces the destination.

**VERIFIED in one SSH session, then a second login.** `KEEP_ROOT_ONCE=1` on the healthy system exited 0 and left `shadow` identical. Removing the `/bin/sh` line from `/etc/shells` and running once put the line back. Setting `RootPasswordAuth=0`, committing, and running once set it back to `on`. `PasswordAuth` stayed `on`, `enable` stayed `1`, and port 22 was still listening. A new SSH login returned uid 0. The hash values were not printed.

## What was not shown

An upgrade that leaves `opt` in place and still starts this launcher has not been done. A bundle that erases that volume, or a firmware that drops the launcher, removes this hook. The script does not put the parking lot or the DNS proxy back.

## Undo

Restore `data.xml.bak-keep-root` over `data.xml`, delete `/airties-edge/genesis`, and start the launcher again with `LD_LIBRARY_PATH=/airties-edge/lib`.
