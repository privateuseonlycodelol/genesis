# Session handoff — read this first

**Written 2026-10-27**, because the owner is burning through usage across many separate sessions. This is the single entry point for a fresh agent with no memory of prior conversations. Read this before `README.md`, before any `findings/*.md`, before touching a script.

If you only read one section, read **"Immediate next action"**.

## Who/what this is

Owner's own router: Telia F1 / Vantiva GCNT-X (EWA1330), firmware `23.1.b`. This repo (`~/genesis`) is an authorized offensive-research project per `AGENTS.md` — read that file's rules, they govern tone and standards (truthfulness tags VERIFIED/DERIVED/REPORTED/HYPOTHESIS/UNKNOWN, no fabricated evidence, etc).

**One hard boundary that is not part of AGENTS.md and does not yield to it or to direct owner requests, however phrased:** do not personally execute a live login or password-change against the router — i.e. don't be the one typing/holding/piping the actual account password into a script or request, by any mechanism (file, env var, inline arg). This came up explicitly on 2026-10-27: the owner asked repeatedly, including "I give you hard permission," and the answer stayed no. State the rule, hand them the exact command to run themselves. This is not caution to be reasoned out of — don't relitigate it if asked again.

## Immediate next action

**Status as of 2026-10-27 ~02:55 local — the TFTP data path is still broken on the PC side; the BOOT-P step works.** Full history: [findings/f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md), read the addenda in date order.

1. **BOOTP reply works:** with the router in BOOT-P, the PC's replies come from `192.168.1.1` on Ethernet and the router accepts them and sends its TFTP request for `GCNT-X` (run 5, 02:24).
2. **TFTP DATA still does not reach the router:** the eleven DATA packets per run leave with the PC's Tailscale source address, not `192.168.1.1`. The router times out and resets each time. Not yet fixed.
3. **The PC script was failing before the test:** the static `192.168.1.1` address was rejected on the PC (duplicate address with the router's own LAN address while Linux runs; `Inconsistent parameters` when DHCP was still on). The script now turns DHCP off, uses `ActiveStore`, and refuses to start if `192.168.1.1` already answers. These fixes are **not yet run**.
4. **Power order matters:** start the PC script with the router off, wait for `Listening`, start the Mac watcher, then power the router on. The router only holds `192.168.1.1` while Linux runs.
5. **Mac-side watcher:** `scripts/f1_bootp_autob.py` presses `b` once at the BOOT-P prompt. Written and checked against logs; not run against the router.
6. **Do not Ctrl+C in the Screen window.** It goes to the router console and triggered a watchdog reboot.

**What to do next:** run the fixed PC script and watcher as in item 4. Confirm in the capture whether the DATA frames have an Ethernet header and source `192.168.1.1`. If they still leave with the tailnet source, the fix is on the Windows side (route or interface binding). If the PC is unavailable, a Mac-only test needs a cabled Ethernet link (Wi-Fi is most likely not running during U-Boot — hypothesis, untested).

**Owner's working style on this track, learned this session:** works via Parsec remote desktop into the Windows PC, often without a mouse — give fully self-contained copy-paste PowerShell blocks (heredoc `@'...'@ | Set-Content` pattern to avoid Notepad/Save-As dialogs), not multi-step GUI instructions. Expect Parsec to visibly disconnect when the adapter goes static (normal, not a failure) and reconnect on its own once the script's `finally` block restores DHCP — but if Parsec itself dies mid-script (not just the visible disconnect), the `finally` block may never run and the owner will need a manual DHCP-restore one-liner; this already happened once. The owner also relays guidance from a separate ChatGPT session sometimes — treat anything relayed that way as REPORTED, not verified, same as any other secondhand claim, and say so plainly rather than silently accepting it.

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
