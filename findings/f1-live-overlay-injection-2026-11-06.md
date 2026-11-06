# Live BOOTP/TFTP Overlay Injection & UART Clash Access-Control Analysis — 2026-11-06

## Result Summary

This pass executed the live recovery flashing of a custom 13.9 MB `rootfs_data` UBIFS bundle over Ethernet (`en10`) and analyzed the live router behavior on UART (`/dev/cu.usbserial-0001`) and HTTP management (`192.168.1.1`).

**VERIFIED:**
1. **Flashing Pipeline Verified:** U-Boot recovery fully received all 27,283 blocks (13,967,360 bytes) of `artifacts/firmware/overlay-injection-bundle.itb` via TFTP (`session-20261106-013445.log`), validated SHA-256 digests, wiped volume 20, and successfully created a dynamic volume of **17,113,088 bytes (67 LEBs)**. The previous `-EINVAL` journal geometry failure (where volume was 25 LEBs) was completely resolved.
2. **U-Boot Success & Reboot:** U-Boot committed the image sequence (`Setting committed 1 valid 1,2 seq 4,3`), reset the gateway, and booted into Bank 1.
3. **UART Console State:** Linux boots to the OpenWrt/procd console prompt: `Please press Enter to activate this console.`.
4. **Clash Access-Control Interception:** When Enter/newline is transmitted over UART, the system echoes input but does not spawn a shell. A concurrent live syslog export from the web management interface (`artifacts/exports/live-check-uart-action/response.bin`) captured the exact internal kernel/userspace sequence at `01:39:54`:
   ```text
   user.notice restricted_shell: User  is connecting through tty...
   user.notice lua: [clash-access-control] User root has no serial access
   user.notice restricted_shell: No suitable login found for root on serial
   ```
5. **Network Daemon State:** HTTP port 80 is OPEN. Dropbear SSH (port 22) and fallback telnetd (port 23) are CLOSED.

---

## Detailed Observations & Evidence

### 1. TFTP & U-Boot Flashing (`session-20261106-013445.log`)
- Tool: `sudo python3 scripts/f1_bootp_tftp_mac.py --iface en10 --uart /dev/cu.usbserial-0001 --file artifacts/firmware/overlay-injection-bundle.itb`
- Transfer: 27,283 TFTP blocks acknowledged by client IP `192.168.1.2`.
- Hash checks:
  ```text
  ## Checking hash(es) for FIT Image at 01000000 ...
     Hash(es) for Image 0 (kernel-1): sha256+ 
     Hash(es) for Image 1 (rootfs_data): sha256+ 
  Flashing rootfs_data (rootfs_data: 0xd52000 bytes from 0x1000270) to rootfs_data1.....
  Remove UBI volume rootfs_data (id 20)
  Creating dynamic volume rootfs_data of size 17113088
  13967360 bytes written to volume rootfs_data
  INFO: Image upgrade successfull!!
  Setting committed 1 valid 1,2 seq 4,3
  resetting ...
  ```

### 2. Live UART Console & Clash Gate
- Serial device: `/dev/cu.usbserial-0001` (115200 8N1).
- Direct transmission of newlines and test strings (`id\n`, `uname -a\n`) resulted in echo followed immediately by:
  `Please press Enter to activate this console.`
- Device syslog confirmed that `procd` spawns `restricted_shell` on console activation:
  ```text
  Fri Nov  6 01:39:54 2026 user.notice restricted_shell: User  is connecting through tty...
  Fri Nov  6 01:39:54 2026 user.notice lua: [clash-access-control] User root has no serial access
  Fri Nov  6 01:39:54 2026 user.notice restricted_shell: No suitable login found for root on serial
  ```
- **Mechanism:** `restricted_shell` invokes a Lua-based policy script `[clash-access-control]`. With an empty connecting user string on `tty`, it defaults to checking if `root` has serial privileges. Because the stock policy lacks serial access for root, `restricted_shell` exits immediately. `procd` notices the child exit and respawns the `askfirst` prompt.

### 3. Overlay Staging & Execution Analysis
- Injected `/etc/inittab` (`::askconsole:/bin/sh --login`) did not replace the console launcher. In OpenWrt/Homeware, `procd` (PID 1) parses `/etc/inittab` from the read-only SquashFS `/rom` partition before `mount_root` pivots to the overlay.
- Injected `/etc/rc.local` (`telnetd -p 23`) did not produce an open listening port on port 23. Two hypotheses:
  - Hypothesis A: Homeware dual-bank overlay isolation (`00_overlay_bank_check.sh`) mounts `/overlay/bank_1` rather than the root of `/overlay`.
  - Hypothesis B: Preinit script `10_remove_due_to_upgrade` / `20_rtfd_remove` cleaned unreferenced overlay files upon detecting the sequence counter increment (`seq 4,3`).

---

## What Was Not Shown

- No interactive root shell prompt (`# `) obtained on UART or network.
- Cryptographic keys (`RIP_ID_RANDOM_KEY_B`, `OSIK`) have not yet been extracted from memory/flash.
- Vendor SquashFS rootfs has not been decrypted or dumped directly.

---

## Next Steps

1. **Investigate Clash Serial User Authentication:** Determine if `restricted_shell` accepts a username/login argument or if specific environment parameters / inputs can select another account (e.g. `engineer` or `admin`).
2. **Overlay Target Refinement:** Align overlay structure to match Homeware's specific bank structure and verify whether `rc.local` is executed by Homeware init scripts.
3. **Web Management Modal Vectors:** Investigate authenticated management endpoints that may execute diagnostics or configuration changes under the active admin session.
