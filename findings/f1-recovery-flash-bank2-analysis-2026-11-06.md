# Live BOOTP/TFTP Recovery Flashing, Bank 2 Switch & RTFD Characterization — 2026-11-06

## Result Summary

This pass executed the live recovery flashing of `overlay-injection-bundle.itb` (13,968,537 bytes) over Ethernet (`en10`), resolved the Darwin/Tailscale host route hijacking blocker, observed U-Boot committing Bank 2 (`seq 4,5`), captured the full kernel boot sequence through OpenWrt `mount_root`, and characterized the behavior of Technicolor's `/lib/mount_root/` RTFD scripts.

**VERIFIED:**
1. **Flashing Pipeline 100% Verified:**
   - Client offered IP migrated from `192.168.1.2` to `192.168.1.50`, completely bypassing a stale macOS host route to virtual interface `utun6` (Tailscale) that was triggering `[Errno 65] No route to host`.
   - `f1_bootp_tftp_mac.py` armed UDP/67 and UDP/69 scoped to `en10` (`AX88179B`), detected U-Boot prompt, sent `'b'`, served all 27,283 blocks via TFTP (`session-20261106-030227.log`), and received 100% of ACKs.
   - U-Boot verified SHA-256 digests for `kernel-1` and `rootfs_data`, wiped volume 20, wrote 13,967,360 bytes to dynamic volume `rootfs_data` (size 17,113,088 bytes / 67 LEBs).
2. **Bank Switch to Bank 2:**
   - U-Boot committed sequence counter `seq 4,5` (`Getting committed 1 valid 1,2 seq 4,3` -> `Setting committed 2 valid 1,2 seq 4,5`), resetting the gateway and booting into Bank 2.
   - Live web management triage confirmed the running firmware string changed from `23.1.b.0448-7241010-20260205081324` to `23.1.b.0448-7241017-20260223134332`.
3. **Mount Root & RTFD Execution Characterized:**
   - Serial console capture observed the kernel mounting volume 20 as UBIFS overlay and executing scripts in `/lib/mount_root/`:
     ```text
     mount_root: switching to ubifs overlay
     mount_root: executing script in /lib/mount_root
     mount_root: /lib/mount_root/00_overlay_bank_check.sh
     /overlay/bank_1/ : No such directory
     mount_root: /lib/mount_root/00_rtfd_all
     /overlay/bank_2/ : No such directory
     mount_root: /lib/mount_root/10_remove_due_to_upgrade
     mount_root: /lib/mount_root/20_rtfd_remove
     mount_root: /lib/mount_root/30_parameter_conversion
     NO_CONFIG_FOUND
     mount_root: /lib/mount_root/80_rtfd_restore
     ```
   - Because U-Boot incremented the sequence counter (`seq 4,5`), preinit scripts `10_remove_due_to_upgrade` and `20_rtfd_remove` treated the boot as a firmware upgrade / factory reset, cleaning the overlay bank folders and falling back to `80_rtfd_restore` which restored clean factory defaults from `/rom`.
4. **Crontab & TTY Execution Traces (Syslog Verified):**
   - Live syslog export (`artifacts/exports/live-check-uart-action-now/response.bin`, 72,767 bytes) confirmed:
     - TTY login attempts trigger `restricted_shell: User  is connecting through tty...` -> `lua: [clash-access-control] User root has no serial access`.
     - `crond` runs as `root` every 60 seconds executing `/usr/share/transformer/scripts/obuspa_retriever.sh`, which invokes `restricted_shell: User root is connecting through Crontab...`.

---

## Detailed Tooling & Artifacts

| Component | Path / Command | Outcome |
| --- | --- | --- |
| TFTP Flasher | `python3 scripts/f1_bootp_tftp_mac.py --iface en10 --no-set-ip --no-pcap --allow-non-root --file artifacts/firmware/overlay-injection-bundle.itb --reboot` | Flashed 27,283 blocks, U-Boot committed Bank 2 |
| Session Log | [`artifacts/bootp/sessions/session-20261106-030227.log`](../artifacts/bootp/sessions/session-20261106-030227.log) | 58,153 lines; full TFTP & U-Boot boot trace |
| Web Triage | [`scripts/f1_web_management_triage.py`](../scripts/f1_web_management_triage.py) | 16 endpoints polled; confirmed Bank 2 firmware build `20260223134332` |
| Triage Bundle | [`artifacts/triage/web-admin-20261106-031133/`](../artifacts/triage/web-admin-20261106-031133/) | 19 raw files + summary JSON |
| Live Syslog Export | [`artifacts/exports/live-check-uart-action-now/response.bin`](../artifacts/exports/live-check-uart-action-now/response.bin) | 72,767 bytes; captured serial & cron execution |

---

## What Was Not Shown

- Root shell prompt not yet obtained on UART due to `mount_root` RTFD cleaning on the initial upgrade boot.
- Hardware cryptographic keys (`RIP_ID_RANDOM_KEY_B`, `OSIK`) have not yet been extracted from memory.

---

## Next Steps

1. **Overlay Persistence Beyond RTFD:** Investigate which paths or file flags survive `10_remove_due_to_upgrade` / `20_rtfd_remove` in Technicolor's mount scripts (e.g. `rtfd_preserve`, or non-bank paths in `/overlay/`).
2. **Cron Environment Injection:** Leverage the verified 60-second root crontab invocation of `/usr/share/transformer/scripts/obuspa_retriever.sh` or its parent directories if shadowed by overlay.
3. **Second-Boot Observation:** Verify whether a clean second reboot (without sequence increment) preserves custom overlay staging once RTFD has completed.
