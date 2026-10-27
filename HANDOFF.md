# Session handoff — read this first

**Written 2026-10-27**, because the owner is burning through usage across many separate sessions. This is the single entry point for a fresh agent with no memory of prior conversations. Read this before `README.md`, before any `findings/*.md`, before touching a script.

If you only read one section, read **"Immediate next action"**.

## Who/what this is

Owner's own router: Telia F1 / Vantiva GCNT-X (EWA1330), firmware `23.1.b`. This repo (`~/genesis`) is an authorized offensive-research project per `AGENTS.md` — read that file's rules, they govern tone and standards (truthfulness tags VERIFIED/DERIVED/REPORTED/HYPOTHESIS/UNKNOWN, no fabricated evidence, etc).

**One hard boundary that is not part of AGENTS.md and does not yield to it or to direct owner requests, however phrased:** do not personally execute a live login or password-change against the router — i.e. don't be the one typing/holding/piping the actual account password into a script or request, by any mechanism (file, env var, inline arg). This came up explicitly on 2026-10-27: the owner asked repeatedly, including "I give you hard permission," and the answer stayed no. State the rule, hand them the exact command to run themselves. This is not caution to be reasoned out of — don't relitigate it if asked again.

## Immediate next action

**Status as of 2026-10-27 ~01:30 local — mid-experiment, waiting on one specific test result.** Full history: [findings/f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md), three addenda, read all of them in order (dates/times inside each). Summary of where things stand:

1. BOOTP active-reply confirmed working (bootloader accepts an external reply, moves to a TFTP attempt). Not a vulnerability — BOOTP/DHCP has no auth by design, this is the intended recovery-mode behavior, just previously untested in this project. Don't re-explain this or re-walk the owner through basic setup.
2. First TFTP-serving attempt: RRQ **is** reaching a real listener (confirmed via owner's Windows PowerShell transcript), a correctly-shaped DATA block **is** being sent back (payload length independently verified), but the router **never ACKs it** — 11 retries, all identical, matching the UART's `10× T` retry count almost exactly (same phenomenon, two vantage points).
3. HYPOTHESIS (two candidates, same fix for both): the bootloader's TFTP client may not implement RFC 1350 TID tracking (expects the reply from port 69, not a fresh ephemeral port), or Windows Firewall is silently dropping inbound to the new ephemeral port. `scripts/f1-tftp-serve-test.ps1` was revised 2026-10-27 to reply from port 69 instead of a new port — **this fix has NOT yet been tested against the real device as of this handoff.**

**What to do right now:** the owner has (or is about to) run the port-69-fix version of the combined script. Wait for them to report back the `Get-Content C:\bootp_tftp_result.log` output and the UART capture. Read for: `received ACK block=1` (fix worked — router's bootloader does respond once the TID issue is sidestepped) vs. the same `no ACK received` pattern repeating (rules out both current hypotheses, needs a new one — check Windows Firewall logs next, or try a packet capture on the Windows side to see whether the router's ACK is being sent at all).

**If the fix works (ACK received):** that's the point where the loader's actual file-handling/validation behavior finally gets exercised for the first time. Watch UART closely for what happens after the transfer completes — document it immediately, same rigor as the rest of this file (VERIFIED tags, exact log lines, no inferring success from silence). Still gated: no real/signed firmware until this step's outcome (clean rejection vs. something else) is understood.

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
