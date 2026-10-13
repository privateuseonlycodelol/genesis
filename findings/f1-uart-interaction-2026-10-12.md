# Owned F1 UART interaction and BOOT-P follow-up — 2026-10-12

## Result

This follow-up tested the live UART on the owner's Telia F1 / Vantiva EWA1330, board GCNT-X, reported firmware `23.1.b`. It resolves some input and recovery questions; it does **not** produce a Linux shell, root, a bootloader command prompt, firmware readout, or a demonstrated exploit.

**VERIFIED from the active Screen logfile and observed terminal:** the Mac's CP2102 UART RX path receives device output. The user pressed `b` at the U-Boot `*** Press b to enter BOOT-P ***` invitation. The capture then printed `Entering BOOT-P mode (reason: BUTTON_PUSH )`. This strongly associates the keypress with accepted BOOT-P entry; the `BUTTON_PUSH` label alone does not distinguish a keyboard event from a physical control.

**VERIFIED test condition:** during that BOOT-P attempt, **no WAN or Ethernet cable was connected to the router**. The bootloader logged repeated `bcmbca_eth_send:Failed to send packet len 428: no active_port set`, then `Retry time exceeded; starting again`, `BOOTP Reply timeout`, and `Resetting the gateway`. This is a timeout with no router Ethernet link. It does not test whether BOOT-P can serve or receive recovery traffic over a connected LAN, and it does not establish a protocol defect. The router automatically booted again. The owner confirmed a later reset/power-cycle was deliberate, not spontaneous.

**VERIFIED Linux-console interaction:** Return, a typed `id` followed by Return, and later Ctrl+J were tried while the Linux `Please press Enter to activate this console.` invitation was visible. The owner explicitly clarified that they were pressing Return; the earlier literal `Enter` in the log was a separate typed-text test. The owner then reported that Ctrl+J produced the activation invitation again. The active capture has `id` as input text followed by another invitation, but no command output, `uid=`, login prompt, or shell prompt. This supports that some characters/newline reached the console path. It does **not** establish that `id` executed, identify what process the firmware launches, or prove the console is disabled. Repeated invitations may simply track repeated activation attempts; they are not by themselves evidence of an exit/crash loop.

**VERIFIED on this unit (2026-10-12, log viewer):** after UART console activation, the router logged a **tty** (serial) `restricted_shell` decision, not only cron launcher rows. Private export: `/Users/nils/Downloads/logviewer-2.txt` (HTML modal snapshot, ~60 KiB, 198 log rows in the table). At **Oct 12 21:00:18** and **21:00:20** (two pairs):

| Process | Message (verbatim) |
| --- | --- |
| `restricted_shell` | `User  is connecting through tty...` |
| `lua` | `[clash-access-control] User root has no serial access` |
| `restricted_shell` | `No suitable login found for root on serial` |

Earlier rows in the same file still show `User root is connecting through Crontab...` paired with `obuspa_retriever.sh` — the cron pattern documented on 2026-10-11. The tty trio above is distinct and aligns with the public [hack-technicolor issue #321](https://github.com/hack-technicolor/hack-technicolor/issues/321) report, but this copy is from **this** GCNT-X / reported **23.1.b** session, not from another owner's paste.

**DERIVED:** UART Enter/newline reaches the console activation path; the firmware then applies **Clash access-control** and does not offer a root serial login. That explains the repeated `Please press Enter to activate this console.` invitation with no shell/`uid=` on the UART capture. It is **not** proof that UART RX/TX is broken, and it is **not** a demonstrated bypass or exploit.

**VERIFIED private artifact state:** `/Users/nils/Desktop/router-boot-20261012-202834-76414.log` is **202,782 bytes**, SHA-256 `9f9ae07e8a4f9a2fa6005e308f24b58ede71a64f778edc6aae540a568f6add77`. A later same-evening re-read (`screen -ls`, `shasum`, raw-byte scan) found the same size and hash. Screen session `76417.f1boot-20261012-202834-76414` was still **Attached**. The log contains three BTRM boot starts, two Linux 4.19.235 banners, one BOOT-P entry, 16 Linux console invitations, the literal `id` input once, 17 `no active_port set` errors, and one BOOTP timeout. The original 86,162-byte capture remains SHA-256 `3f242d10ede0a08f3c2d72ebb4966f80222ade017b3e03690ffc08c72fa27feb`.

### Same-capture re-read

**VERIFIED:** both kernel command lines include `console=ttyS0,115200`. The first invitation is printed immediately after `procd: - init -`, and boot continues (`urngd`, `kmodloader`). The waiter does not block init. Strings `login:`, `uid=`, `askfirst`, `restricted`, and `Magic SysRq` are absent. The fifteen `# ` hits are U-Boot `## Checking hash(es)` / `## Loading` lines, not a shell prompt.

**VERIFIED:** the final console cluster is 354 bytes. Invitations are separated only by CRLF, then fourteen literal `^[[A` sequences (bytes `5e 5b 5b 41`), one CRLF, and a final invitation. That cluster contains no ESC byte. Elsewhere the file has 194 raw ESC bytes, all SGR color sequences such as `ESC [ 0 m`, and the last of those sits before this cluster. Screen did not rewrite ESC into caret notation for the whole logfile.

**DERIVED:** those fourteen `^[[A` runs match Linux `ECHOCTL` echo of Up-arrow auto-repeat: the kernel echoes ESC as `^[` and then echoes `[A`. The invitation is reprinted after the line, with no other stdout. This places those keystrokes in the cooked tty echo path. It still does not name the program that waits for the line, show that a command ran, or show a Clash / `restricted_shell` decision. Those decision strings are not in the UART log.

**VERIFIED:** this Mac had no path to the gateway during the re-read. The default route to `192.168.2.1` used `172.20.10.1` on `en0`. One `curl --noproxy '*' --max-time 5 http://192.168.2.1/login.lp` timed out (exit 28, HTTP 000). No login and no logviewer request were sent.

### Evening pass (same date, ~21:05–21:08)

**VERIFIED:** evening capture in Cursor Terminal (`screen` `80986`, session `f1boot-20261012-210529-80983`). Primary path: `/Users/nils/Desktop/router-boot-20261012-210529-80983.log`. **Preserved copy (2026-10-12 ~21:12):** `artifacts/uart/2026-10-12/router-boot-20261012-210529-80983.log` — **232,270 bytes**, SHA-256 `eda5cdf7e38e9824b34718b87dbdb74a5d27a36a1cd73adb0d4002d07d4742a5` (gitignored; snapshot while Screen still attached). Contents: **2×** `Entering BOOT-P mode` (`BUTTON_PUSH`); first BOOT-P **17×** `no active_port set` → BOOTP timeout; second BOOT-P **`active port 0`** and **`Link Up 1 Gbps Full duplex`** → still **2×** `BOOTP Reply timeout` (no responder on that link); **2×** Linux **4.19.235**, **2×** console invitation, **4×** BTRM, no `uid=`/`id` execution.

**DERIVED:** link during the **second** U-Boot BOOT-P window was present; failure mode shifted from `no active_port set` to BOOTP timeout only. That still does **not** prove a working recovery server was offered on the cabled device.

**Operational (not device behavior):** Mac internet via phone hotspot does not participate in BOOT-P; F1 Wi‑Fi (`192.168.2.1`) is separate from hotspot. Log viewer was reached via authenticated fetch/save (`logviewer-2.txt`); the **Management** modal shell can show a **Log Viewer** tab, but `isFeatureLogViewerFlag = false` hides it from some dashboards — direct URL `/modals/logviewer-modal.lp` still works when logged in.

## Reproduction and environment

- Device: owner's Telia F1 / Vantiva EWA1330, GCNT-X, reported `23.1.b`.
- Adapter: Silicon Labs CP2102, macOS `/dev/cu.usbserial-0001`, reported `AppleUSBSLCOM`; adapter power pin disconnected. UART wiring as reported: router TX → adapter RX, adapter TX → router RX, shared GND.
- Capture: macOS `/usr/bin/screen` **4.00.03**, started by `bash /Users/nils/genesis/scripts/f1-boot-capture.command` in the visible macOS Terminal, not the embedded Genesis terminal. Screen config enables logging; logfile is private on Desktop. Current observed Screen session: `76417.f1boot-20261012-202834-76414`; capture path above. The helper was not previously verified on physical hardware; this run did produce readable live output and a growing logfile.
- Older adapter configuration attempts (`termios.tcsetattr`, `stty`, `IOSSIOSPEED`, `cu`) failed with the recorded errors in [UART-HANDOVER.md](../UART-HANDOVER.md). Unplugging the CP2102 from the Mac cleared stalled Screen/stty processes and removed the device node; reconnecting restored it. Earlier 0-byte attempts are not evidence of no device output.
- Capture analysis was local and read-only; no network services were started, no firmware was sent, and no bootloader commands were issued.

For a local review, without printing identifiers from the capture:

```sh
shasum -a 256 /Users/nils/Desktop/router-boot-20261012-202834-76414.log
python3 - <<'PY'
from pathlib import Path
p = Path('/Users/nils/Desktop/router-boot-20261012-202834-76414.log')
b = p.read_bytes()
for marker in (b'Entering BOOT-P mode', b'no active_port set',
               b'BOOTP Reply timeout',
               b'Please press Enter to activate this console.',
               b'\r\nid\r\n', b'uid='):
    print(marker.decode(errors='replace'), b.count(marker))
PY
```

## What was not established

- No Linux shell, login, UID, root, or command execution.
- No interactive Linux shell, login prompt, or `uid=` on UART despite working input and tty activation.
- Exact shipped `inittab`/launcher binary and Clash policy source on disk are still unextracted; log lines name `restricted_shell`, `lua`, and `[clash-access-control]` only.
- No matching 23.1.b rootfs or executable was available to decompile. The upstream OpenWrt `askfirst` helper is only a behavioral reference: it waits for newline then `execvp`s a configured program; it is not proof that this firmware uses that helper unchanged ([source](https://lxr.openwrt.org/source/procd/utils/askfirst.c)).
- At the time of the first UART pass, no Ethernet was connected, so that log alone could not show BOOTP on the wire. **Superseded for the LAN question (2026-10-13):** a Windows pktmon capture on a cabled PC recorded the 428-byte BOOTREQUESTs and no replies. See [f1-bootp-lan-2026-10-13.md](f1-bootp-lan-2026-10-13.md).
- No successful BOOT-P transfer, flash operation, firmware extraction, U-Boot shell, JTAG transaction, or key recovery.
- No spontaneous reset during this pass. One BOOT-P retry timeout reset is captured; the user separately confirmed another reset was deliberate.
- **Superseded:** older repo logviewer slices had cron-only `restricted_shell` rows; the 2026-10-12 `logviewer-2.txt` export adds tty/Clash denial on this unit.

## Next highest-value work

1. **Stop UART console probing for root/shell** unless a new hypothesis appears (different firmware build, policy change, or offline binary showing another entry). Policy denial is established on this unit.
2. **BOOT-P listen-only is done** ([f1-bootp-lan-2026-10-13.md](f1-bootp-lan-2026-10-13.md)): boot file **`GCNT-X`**, no Offer. **Next:** `scripts/f1-bootp-reply.ps1` on the cabled Windows PC (expect TFTP error, no RBI yet).
3. **Firmware / keys:** config export decrypt still needs `RIP_ID_RANDOM_KEY_B`; offline 23.1.b rootfs or a supported read path remains the decompilation input. UART text and denied serial login do not supply executables.

Do not repeat Enter/`id`/Ctrl+J spam on the console. Do not repeat the old Python serial relay or `cu` attempt.
