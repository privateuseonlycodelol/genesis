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

## What was not shown

An upgrade that leaves `opt` in place and still starts this launcher has not been done. A bundle that erases that volume, or a firmware that drops the launcher, removes this hook. The script does not put the parking lot or the DNS proxy back.

## Undo

Restore `data.xml.bak-keep-root` over `data.xml`, delete `/airties-edge/genesis`, and start the launcher again with `LD_LIBRARY_PATH=/airties-edge/lib`.
