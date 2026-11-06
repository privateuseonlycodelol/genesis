# UART Serial Credentials Test, Bank-1 Overlay Restructure & Web Management Triage — 2026-11-06

## Result Summary

This pass executed the three planned follow-up tracks:
1. **Serial Console Credentials Testing:** Probed `/dev/cu.usbserial-0001` with multiple non-root usernames and credential formats to determine whether `restricted_shell` can be guided to authenticate as `admin`, `engineer`, or any non-root account.
2. **Bank-Specific Overlay Alignment:** Restructured the `rootfs_data` overlay staging to align specifically with `/overlay/bank_1`, injecting wrapper binaries for `/bin/restricted_shell` to override Technicolor's Clash access-control policies, and adding `/etc/rc.d/S99triage` init hooks.
3. **Web Management Triage:** Utilized the active web admin session (port 80) to extract live telemetry, hardware/firmware metadata, network interface stats, client tables, and security role boundaries.

---

## 1. Serial Console Credentials Testing (VERIFIED)

- **Tool:** [`scripts/f1_test_serial_credentials.py`](../scripts/f1_test_serial_credentials.py)
- **Raw Artifacts:** [`artifacts/uart/uart-credentials-probe-20261106-015821/`](../artifacts/uart/uart-credentials-probe-20261106-015821/)
- **Syslog Verification:** [`artifacts/exports/live-check-uart-credentials-20261106/response.bin`](../artifacts/exports/live-check-uart-credentials-20261106/response.bin) (73,265 bytes)

### Observations
Nine probe payloads were sent to the serial line at 115200 8N1:
1. `\n`
2. `admin\n`
3. `engineer\n`
4. `root\n`
5. `login admin\n`
6. `\nadmin\n`
7. `\nengineer\n`
8. `\r\n`
9. `admin\r\n`

### Findings
- The serial line echoes input in cooked mode and immediately re-prints:
  `Please press Enter to activate this console.`
- Device syslog captured the exact daemon execution sequence for every single probe:
  ```text
  user.notice restricted_shell: User  is connecting through tty...
  user.notice lua: [clash-access-control] User root has no serial access
  user.notice restricted_shell: No suitable login found for root on serial
  ```
- **VERIFIED Behavior:** `restricted_shell` does **not** read username credentials from stdin or present an interactive login prompt. On `tty` activation, it inspects the calling process context (where `getlogin()` returns empty on an unauthenticated terminal), observes two spaces (`User  is connecting`), defaults the target evaluation account to `root`, fails the Lua `[clash-access-control]` check, and immediately exits.

---

## 2. Bank-Specific Overlay Restructuring (VERIFIED offline)

### Mechanism Analysis
- **Init Timing:** OpenWrt `procd` (PID 1) reads `/etc/inittab` from the base SquashFS partition before `mount_root` switches to `/overlay/bank_1`. Consequently, overriding `/etc/inittab` in the overlay does not prevent `procd` from invoking `/bin/restricted_shell` on console activation.
- **Bypass Strategy:** In Linux `overlayfs`, an upper-layer executable completely shadows and replaces a lower-layer read-only executable. By staging a wrapper script at `/bin/restricted_shell` (and `/usr/bin/`, `/usr/sbin/`, `/sbin/`), the system executes the wrapper upon console activation, bypassing `restricted_shell` and the Lua Clash policy entirely.
- **Init Daemon Hook:** Injected `/etc/init.d/triage` and `/etc/rc.d/S99triage` (mode 0755) to ensure automated startup under SysVinit / OpenWrt `rcS` even if `/etc/rc.local` is bypassed.

### Implemented Tooling & Bundle Generation
- Updated [`scripts/generate_f1_overlay.py`](../scripts/generate_f1_overlay.py) with:
  - `RESTRICTED_SHELL_WRAPPER` (`exec /bin/sh --login "$@"`) staged across `/bin/`, `/usr/bin/`, `/usr/sbin/`, and `/sbin/`
  - `INITD_TRIAGE_CONTENT` staged at `/etc/init.d/triage` and `/etc/rc.d/S99triage`
  - Bank-1 and Bank-2 full hierarchy alignment
- Unit test suite [`scripts/test_generate_f1_overlay.py`](../scripts/test_generate_f1_overlay.py) updated and passing (3/3 tests).
- Recompiled [`artifacts/firmware/overlay-injection-bundle.itb`](../artifacts/firmware/overlay-injection-bundle.itb):
  - UBIFS Size: 13,967,360 bytes (SHA-256: `123eb68967e0382326c4807d0bb40d6469c616878413061c87751325445c7deb`)
  - FIT Bundle Size: 13,968,537 bytes (SHA-256: `01bad25bc6b2278bf1a800be38d591834d3dadc79267b143751c7c75783484d3`)
  - Validation: 0 errors, 0 warnings.

---

## 3. Web Management Triage (VERIFIED)

- **Tool:** [`scripts/f1_web_management_triage.py`](../scripts/f1_web_management_triage.py)
- **Saved Evidence:** [`artifacts/triage/web-admin-20261106-020151/`](../artifacts/triage/web-admin-20261106-020151/)

### Live Device State
| Metric / Parameter | Live Value | Source Modal |
| --- | --- | --- |
| **Product Vendor** | `Vantiva` | `/modals/system-info-modal.lp` |
| **Product Name** | `Telia F1` | `/modals/system-info-modal.lp` |
| **Board / Hardware** | `GCNT-X` | `/modals/system-info-modal.lp` |
| **Software Version** | `23.1.b` | `/modals/system-info-modal.lp` |
| **Firmware Full String** | `23.1.b.0448-7241010-20260205081324` | `/modals/system-info-modal.lp` |
| **Serial Number** | `CP2242AD8AN` | `/modals/system-info-modal.lp` |
| **MAC Address** | `A0:B5:3C:C6:62:82` | `/modals/system-info-modal.lp` |
| **Flash Bank Size** | `134217728` bytes (128 MiB) | `/modals/system-config-modal.lp?action=getbanksize` |
| **Reboot Cause** | `Power` | `/modals/system-info-modal.lp` |
| **Memory / CPU Usage** | `79%` Memory, `15%` CPU | `/modals/system-info-modal.lp` |
| **Ethernet Port 4 (`eth3`)** | Connected, 1000 Mbps (Rx: 494.5 MB, Tx: 820.1 MB) | `/modals/diagnostics-network-modal.lp` |
| **Ethernet Port 5 (`eth4`)** | Connected, 1000 Mbps (Rx: 829.4 MB, Tx: 498.9 MB) | `/modals/diagnostics-network-modal.lp` |
| **Wi-Fi 2.4 GHz (`wl1`)** | Connected (`Telia-C66283`) | `/modals/diagnostics-network-modal.lp` |
| **Connected Client** | `192.168.1.39` (`80:60:b7:db:eb:08`) | `/modals/device-modal.lp` |
| **NTP Servers** | `ntp-cust1.telia.com, ntp-cust2.telia.com` | `/modals/time-management-modal.lp` |
| **CWMP / UserMgr Gate** | Redirect to `/login.lp` (enforces `engineer` role) | `/modals/cwmpconf-modal.lp`, `/modals/usermgr-modal.lp` |

---

## What Was Not Shown

- No interactive root shell spawned by serial keystrokes prior to reflashing the newly restructured overlay.
- `engineer` role pages (`cwmpconf-modal.lp`, `usermgr-modal.lp`) remain inaccessible to the `admin` role session.
- Hardware cryptographic keys (`RANDOM_KEY_B`, `OSIK`) have not yet been dumped from memory.
