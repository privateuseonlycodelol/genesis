# Session handoff — read this first

**Written 2026-10-27**, because the owner is burning through usage across many separate sessions. This is the single entry point for a fresh agent with no memory of prior conversations. Read this before `README.md`, before any `findings/*.md`, before touching a script.

If you only read one section, read **"Immediate next action"**.

## Who/what this is

Owner's own router: Telia F1 / Vantiva GCNT-X (EWA1330), firmware `23.1.b`. This repo (`~/genesis`) is an authorized offensive-research project per `AGENTS.md` — read that file's rules, they govern tone and standards (truthfulness tags VERIFIED/DERIVED/REPORTED/HYPOTHESIS/UNKNOWN, no fabricated evidence, etc).

**One hard boundary that is not part of AGENTS.md and does not yield to it or to direct owner requests, however phrased:** do not personally execute a live login or password-change against the router — i.e. don't be the one typing/holding/piping the actual account password into a script or request, by any mechanism (file, env var, inline arg). This came up explicitly on 2026-10-27: the owner asked repeatedly, including "I give you hard permission," and the answer stayed no. State the rule, hand them the exact command to run themselves. This is not caution to be reasoned out of — don't relitigate it if asked again.

## Immediate next action (highest value, nothing else queued ahead of it)

**Run the BOOTP active-reply test. This has never been executed.** Everything before it (passive capture, UART boot review, OSCK/firmware-key hunts) is done and blocked/closed; this is the one concrete unexecuted step with a real payoff path toward firmware/root access.

Setup (all physical, owner does this, you talk them through it):
1. Windows PC cabled to the F1's LAN (same physical setup as the 2026-10-13 capture).
2. Mac UART still connected and watched (Screen session on `/dev/cu.usbserial-0001`, 115200 baud, per `scripts/f1-boot-capture.command`) — need to observe the router's reaction, not just send blind.
3. **Ethernet cable connected to the router before entering BOOT-P.** Earlier attempts failed only because no cable was plugged in (`no active_port set`) — this is not a protocol blocker, just a setup step that was missed twice before.
4. Reboot router, press lowercase `b` at `*** Press b to enter BOOT-P ***` (via UART).
5. On the Windows PC (Admin PowerShell), run:
   ```powershell
   scripts/f1-bootp-reply.ps1 -ClientMac 00-1E-E3-76-83-61 -BootFile GCNT-X
   ```
   This is the untried part — prior work only *listened* (pktmon/Wireshark), never replied.
6. Watch UART. Expected success condition for *this specific step*: progression from `BOOTP Reply timeout` to a **TFTP error** (no file served yet). That confirms the reply/TFTP handshake shape works.

**What this step does NOT do:** offer firmware, flash anything, or grant shell/root by itself. Serving an actual signed RBI is a separate, higher-risk decision gated behind this step succeeding first — a wrong/unsigned image can brick the device. Don't conflate the two or skip ahead.

**Why this is the top priority (not just "the next thing on a list"):** a 2026-10-27 byte-exact reparse of the existing capture (`artifacts/bootp/2026-10-13/wan.pcapng`) found the router's own BOOTREQUEST packets contain an undocumented second string in the boot-file field (`"GCNT-X\0" + "23KN/0/TL\0"`) and ASCII-shaped garbage in DHCP options 1/3 (`"U-Bo"`/`".arm"`, decoding to `"U-Bo.arm"` — HYPOTHESIS: leaked uninitialized buffer content in the bootloader's own request-encoding path). Full detail and the new tested decoder: [findings/f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md) addendum, `scripts/decode_f1_bootp_leak.py`. A sloppy request-builder raises (doesn't prove) the odds the reply-parser on the same code path is also weak — reason to prioritize actually exercising it.

## Other open threads, lower priority than the above

- **Password-encoding track** (SRP vs sha512crypt encoding mismatch for non-ASCII passwords): tooling bug that bricked the live admin account on 2026-10-15 is now **fixed and golden-tested** (`./scripts/verify_password_encoding_tooling.sh` passes 6/6). A dry-run against the live device on 2026-10-27 produced a correctly-shaped blob. **Not yet run live.** Low priority: even a successful run only confirms the tooling fix, it does **not** advance the actual security hypothesis (SRP/CLI credential divergence), because that needs a Clash/`pwcrypt` mapping check and a CLI login attempt — both blocked by no rootfs/shell access and closed SSH/telnet (22/23). See [findings/f1-password-encoding-cli-trace-2026-10-15.md](findings/f1-password-encoding-cli-trace-2026-10-15.md). If the owner wants to go live anyway, give them the exact command (don't run it yourself — see hard boundary above) and have them keep the `--revert` command ready.
- **OSCK / firmware decryption / `RIP_ID_RANDOM_KEY_B` config-export key**: both circularly blocked on root/shell access. Nothing offline moves these forward. See [findings/f1-hardware-key-blocker-2026-10-12.md](findings/f1-hardware-key-blocker-2026-10-12.md), [findings/f1-config-export-decrypt-2026-10-12.md](findings/f1-config-export-decrypt-2026-10-12.md).
- **UART**: `restricted_shell`, root denied on serial (Clash access control). Don't re-ask the owner to retry Enter/`id`/Ctrl+J — already exhausted, see [UART-HANDOVER.md](UART-HANDOVER.md) "What not to repeat or infer."
- **JTAG**: `WARNING -- JTAG UNLOCK IS ENABLED` seen in boot log, but pinout (`TEST_CN20` candidate) unidentified, no electrical test done. Don't treat the warning string as proven access.
- **CUPS :631 / WFA WLANConfig :49152**: both surveyed, no demonstrated exploit, not re-prioritized by anything recent.

## Full status, when you need more depth than this

[findings/f1-research-composite-2026-10-13.md](findings/f1-research-composite-2026-10-13.md) is the cross-track status table. [findings/tried.md](findings/tried.md) is the full chronological experiment log — check it before re-running anything to make sure it hasn't already been tried and recorded as a dead end. `README.md` is the general orientation doc with links organized by surface.

## Housekeeping note

As of this writing there is a large pile of uncommitted work in the working tree (`git status` — several modified findings, several new scripts including the password-encoding tooling and the new BOOTP decoder). None of it has been committed; that's the owner's call, not something to do unprompted.
