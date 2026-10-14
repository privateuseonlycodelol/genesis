# Genesis UART Handover: Telia F1 / Vantiva GCNT-X

## Current state — read this before the older setup history

**Updated 2026-10-13** (BOOT-P LAN capture). Canonical evidence: [f1-uart-interaction-2026-10-12.md](findings/f1-uart-interaction-2026-10-12.md), [f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md), [f1-research-composite-2026-10-13.md](findings/f1-research-composite-2026-10-13.md).

### What was established

- The owner's Telia F1 / Vantiva EWA1330, GCNT-X, reported firmware `23.1.b`; adapter is CP2102, Mac device `/dev/cu.usbserial-0001`, adapter 3.3 V disconnected, router TX→adapter RX, adapter TX→router RX, GND common.
- A physical Screen 4.00.03 capture now worked after the CP2102 was unplugged/replugged. Command: `bash ~/genesis/scripts/f1-boot-capture.command`, run from the user's visible macOS Terminal. Current observed Screen session: `76417.f1boot-20261012-202834-76414`; logfile: `~/Desktop/router-boot-20261012-202834-76414.log`.
- At the last documented snapshot the logfile was **202,782 bytes**, SHA-256 `9f9ae07e8a4f9a2fa6005e308f24b58ede71a64f778edc6aae540a568f6add77`; it may have grown while Screen is attached. Always get its current size/hash before relying on counts. It contains three BTRM boot starts, two Linux 4.19.235 banners, one BOOT-P entry, 16 Linux activation invitations, one captured literal `id`, 17 `no active_port set` errors and one BOOTP timeout.
- **Live input verified at the bootloader:** the user pressed lowercase `b` at `*** Press b to enter BOOT-P ***`, followed by `Entering BOOT-P mode (reason: BUTTON_PUSH )`. The timing strongly supports the keypress being accepted. Do not conflate the `BUTTON_PUSH` label alone with proof of its source.
- **Early BOOT-P (no Ethernet):** first attempts had **no WAN/LAN cable** → `no active_port set`, then `BOOTP Reply timeout`. **Later UART capture:** Ethernet **link up**, still `BOOTP Reply timeout` (no server on the wire).
- **2026-10-13 Windows PC on router LAN:** pktmon + Wireshark recorded **17** full BOOTREQUESTs; boot file name **`GCNT-X`**; **no** DHCP Offer. Evidence: [f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md). **Not done:** answer from PC (`scripts/f1-bootp-reply.ps1`), TFTP, or RBI flash.
- **Linux console remains unresolved:** at the `Please press Enter to activate this console.` prompt, the user pressed Return multiple times. They separately typed the word `Enter` once and `id` once, then pressed Return. They later pressed Ctrl+J and explicitly reported seeing the invitation print again. The logfile captures literal `Enter` and `id`, followed by invitations, but no shell/login/UID output. This is evidence of input characters arriving, not evidence that `id` executed, or that root shell access exists. The user corrected the previous agent: invitation repetitions matched their repeated keypresses; don't describe the repetitions as a spontaneous loop/crash.
- The owner confirmed the reset following the BOOTP timeout / before the later boot was deliberate. Do not call it a spontaneous crash.
- Community evidence: a different GCNT-X owner reports `Restricted_Shell`/Clash access-control messages denying root serial access in [hack-technicolor issue #321](https://github.com/hack-technicolor/hack-technicolor/issues/321). This is **REPORTED, third party**; not fetched from this owner's fresh logs and not verified on matching 23.1.b code. Existing saved web logviewer captures contain `restricted_shell` cron rows but none of the serial denial phrases. Do not promote the issue comment to current-unit fact.

### What not to repeat or infer

- Do not ask for more Return, literal “Enter”, `id`, or Ctrl+J repetitions. They produced no shell and add little information. The owner has already clarified what they pressed. If receiving a result, check bytes/logs instead of second-guessing whether they used the right key.
- Do not say the UART input path is entirely broken: lowercase `b` selected BOOT-P, and console input characters were captured.
- Do not say Linux access is definitively disabled or blocked by `Clash-access-control` until this unit's own current log or matching 23.1.b executable shows that.
- Do not call the repeated prompt an error loop. The user was pressing keys; upstream OpenWrt reference code can print its invitation again when a supervisor restarts a child, but matching vendor implementation/config has not been obtained.
- Do not infer a firmware readout from a UART text log or BOOT-P entry. No RBI/current image, executable bytes, recovery payload exchange, shell, root, JTAG read, or flash dump was acquired.
- Do not interpret `no active_port set` as permanent — it was the **no-cable** case. Cabled listen-only capture is done; next is **BOOTP reply**, not another passive-only capture.
- Do not send firmware, attempt a flash, or run a guessed CFE/U-Boot command as an exploratory step.
- Do not repeat the exact failed Python `termios.tcsetattr()` helper, prior `cu`, embedded-Terminal Screen attempt, or `stty -f /dev/cu.usbserial-0001` settings query. Unplugging the CP2102 cleared stalled processes; macOS Terminal Screen subsequently succeeded.
- App terminal visibility is easy to confuse: `mcp__codex_app__read_thread_terminal` sometimes showed the Genesis zsh prompt, while the user's separate Terminal had Screen attached. A Screen process marked attached does not mean the Codex app's terminal is displaying it. Ask which pane only if ambiguity remains; in this pass the user explicitly confirmed the router invitation was on screen.
- Keep the earlier verified 86,162-byte capture (hash `3f242d10ede0a08f3c2d72ebb4966f80222ade017b3e03690ffc08c72fa27feb`) distinct from the new multi-boot log. Don't call it a new interactive capture.

### Best next work

1. **BOOT-P reply (Windows PC on LAN):** run `scripts/f1-bootp-reply.ps1` **before** power-on/`b`; Mac UART watches for TFTP vs timeout. Boot name in capture is **`GCNT-X`**. No RBI on the PC until UART confirms the reply path. See [f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md).
2. **Stop UART Enter/`id` spam** — serial root denied on this unit (logviewer).
3. **Decompile / decrypt** still needs rootfs or `RIP_ID_RANDOM_KEY_B`; see [research composite](findings/f1-research-composite-2026-10-13.md).
4. Wi‑Fi coax: reseat on **`ANT*`**, not **`4G-ANT*`** ([board visual](findings/f1-board-visual-2026-10-12.md)).

### Recent recovery chronology and test truth table

| Stage | Input / condition | Observed output | Bounded result |
|---|---|---|---|
| Old verified capture | Receive only; no recorded input | Linux 4.19.235; Enter invitation | Boot output and invitation existed; interactivity unknown. |
| New Screen capture | CP2102 unplug/replug; Screen launched in visible macOS Terminal; router power-cycled | Readable U-Boot/Linux output; fresh log grew | Physical UART output/capture verified. |
| Linux invitation | Multiple Return presses; typed `Enter` and `id`; Ctrl+J later, no Ethernet connected | Invitation appeared again; typed bytes captured; no shell/login/UID response | Input path has evidence; program execution/auth result unknown. Prompt repeats may track keypresses. |
| BOOT-P (no cable) | `b`; no Ethernet | `no active_port set`; BOOTP timeout | Link absent. |
| BOOT-P (cable, no server) | `b`; LAN to PC, no DHCP server | Link up; BOOTP timeout (UART) | Requests on wire; see next row. |
| BOOT-P LAN listen | Windows pktmon/Wireshark | **17** BOOTREQUESTs; boot file **`GCNT-X`**; no Offer | [f1-bootp-lan-2026-10-13.md](findings/f1-bootp-lan-2026-10-13.md) |
| BOOT-P reply | `f1-bootp-reply.ps1` | **Not run yet** | Expected: TFTP error without RBI. |
| After reset | Owner says reset/power-cycle was deliberate | New BTRM/U-Boot and Linux boot captured | Not a spontaneous reset/crash. |

## Previous setup history

## Purpose

Continue investigating UART access on the user's own Telia F1 / Vantiva GCNT-X (EWA1330), reported to run firmware `23.1.b`. The immediate objective is to determine what the UART exposes and whether the console prompt is interactive.

Keep these claims separate:

- A UART boot log exists.
- A console prompt appears.
- The prompt accepts input.
- A shell is available.
- The shell has root privileges.
- JTAG is physically accessible or usable.

Evidence for one does not establish the others.

## Device and wiring

- Router UART **CN1** (`findings/serial-header.jpg`): four **through-holes** on the board (`3.3V GND TX RX` silkscreen), not a factory pin header for clipping Dupont leads. Electrical contact is at those holes (soldered wire or a added header); Dupont jumpers belong on the CP2102 adapter side. Details: [f1-uart-23.1b.md](findings/f1-uart-23.1b.md).
- USB-UART adapter: Silicon Labs CP2102.
- macOS serial callout: `/dev/cu.usbserial-0001`.
- USB registry identified vendor ID `4292` (`0x10c4`), product ID `60000` (`0xea60`), product string “CP2102 USB to UART Bridge Controller.”
- The observed macOS driver was `AppleUSBSLCOM`.
- Wiring reported by the user:
  - Router TX → adapter RX
  - Adapter TX → router RX
  - GND → GND
  - Adapter 3.3V left disconnected

## Verified existing capture

The existing file is:

`~/Desktop/router-boot-20261012-193402-64722.log`

It is 86,162 bytes (about 84 KB). Previously recorded SHA-256:

`3f242d10ede0a08f3c2d72ebb4966f80222ade017b3e03690ffc08c72fa27feb`

The file was checked and contains:

- `WARNING -- JTAG UNLOCK IS ENABLED`
- Linux version `4.19.235`
- `Please press Enter to activate this console.`

This verifies boot output was captured. The available capture did not establish that input after the console prompt produced a usable shell. The JTAG message alone does not identify pins or prove physical JTAG access.

The user reported the file was made during an earlier Screen-based run. The log content is verified; the exact command/session provenance is based on the conversation unless independently checked.

## Failed capture attempts and exact evidence

### Latest failed Python attempt

The user ran the Python-based helper and posted this error:

```text
termios.error: (22, 'Invalid argument')
```

It occurred in `configure_serial()` during `termios.tcsetattr()`.

The attempted log is:

`~/Desktop/router-boot-20261012-202007-74774.log`

It is 0 bytes. This attempt did not capture boot output. It is a serial configuration failure, not evidence that the router produced no output.

The Python relay was tested against a simulated pseudo-UART: byte forwarding, display, logging, Enter-to-carriage-return, and clean exit passed. That was only a software-path test, not validation with the physical CP2102. The Python helper was then removed from the current shell script.

### Real adapter settings probes

In the agent's execution environment, tests against the connected CP2102 reported:

- Python `tcsetattr()` setting 115200: `EINVAL / Invalid argument`.
- macOS `stty -f /dev/cu.usbserial-0001 115200`: `tcsetattr: Invalid argument`; subsequent readback still reported 9600 baud.
- Apple `IOSSIOSPEED` ioctl probes with 32-bit and 64-bit request variants: device error 83.
- A staged attempt to set 230400 before 115200: also `EINVAL`.

These results show those tested configuration calls failed in that execution environment. Do not extrapolate them into a claim that no macOS terminal method can work; the older capture is evidence that a Screen-based capture was previously successful.

### Screen and cu history

The original user command included `screen -L -Logfile ...`; the installed Screen rejected `Logfile` as an unknown option. Do not repeat that exact command.

Screen attempts from the embedded Genesis terminal produced errors including:

```text
SetTTY (fd 5): ioctl failed: Invalid argument
```

Another run showed:

```text
Cannot open line '/dev/cu.usbserial-0001' for R/W: Resource busy
Sorry, could not find a PTY.
```

At one point `lsof` showed a Screen process holding the device. Later `screen -ls` reported no Screen sockets. Check the current terminal and port holder before stating whether the device is busy.

A `cu` attempt without sudo failed while creating a UUCP lock file and then reported “Line in use.” A sudo `cu` run later failed with:

```text
/usr/bin/cu: Can't set terminal settings: Invalid argument
```

Do not send the user through another untested `cu` attempt.

## Current helper state

The current helper path is:

`~/genesis/scripts/f1-boot-capture.command`

It was changed back to Screen-based logging after the Python method failed with the CP2102. Its shell syntax and Screen configuration parsing were checked. The current version has **not** been tested against the physical router.

Current helper behavior:

- It selects `/dev/cu.usbserial-0001` by default.
- It creates a timestamped log path on the Desktop and prints that path.
- It creates a Screen configuration setting a logfile and enabling logging.
- It starts `/usr/bin/screen` at 115200 baud.
- It tells the user to exit with **Ctrl+A, then K, then Y**.
- It is intended to run from **macOS Terminal.app outside the embedded Genesis terminal**.
- It should not require sudo.

Do not claim this version works until a real capture produces a nonempty log with recognizable boot text.

## Terminal visibility and password incident

The agent incorrectly claimed a capture session had been opened in a visible Codex terminal. The tool had returned a queued status, and the Genesis terminal snapshot did not show that session. A separate `exec_command` PTY is not necessarily visible or interactive for the user. Never tell the user to enter credentials or commands into a terminal unless its visibility and prompt are confirmed.

A password-like value was typed at a zsh shell prompt and echoed as a command; zsh returned “command not found.” The user later ran the helper and it reached the sudo prompt before the Python serial-setting traceback. Do not repeat or quote the value. The user said they do not care about its exposure. Still, do not request a password unless a clear, genuine sudo prompt is visible to the user.

## Recommended next step

1. If the user wants to inspect the device behavior, start with the existing verified capture at `~/Desktop/router-boot-20261012-193402-64722.log`; no new capture is needed merely to establish that boot output exists.
2. If a fresh capture is needed, use macOS Terminal.app outside the embedded Genesis terminal. Run the current helper there and verify that Screen opens before rebooting the router.
3. Once the capture is open, power-cycle the router. Press Enter only after the “Please press Enter” console prompt appears if testing whether it accepts input.
4. Exit Screen with **Ctrl+A, then K, then Y**. Do not suggest a backslash sequence; the user has a Swedish keyboard. Do not use Ctrl+A, D, which detaches and may leave the port occupied.
5. Verify the exact printed logfile path and confirm the file contains new, recognizable boot output before calling the new capture successful.
6. If Screen fails again, capture the exact current error and inspect the live port holder before proposing another method. Do not repeat identical attempts without a new hypothesis or corrected environment.

## Repository and communication constraints

The user explicitly said not to document this research pass in the repository. Do not add findings, reports, or tried-experiment entries for this UART troubleshooting unless the user later asks.

The repository's `AGENTS.md` describes broader authorized research on the user's owned device and requires evidence-based claims. For future work, follow the user's instruction not to document this pass. When reporting results, label observed facts separately from hypotheses and say plainly what has not been tested.

The user is frustrated by repeated unverified advice. Check the current Genesis terminal when asked about its state. Give one clear next action, explain exactly what result to expect, and do not claim success beyond what the file or live test proves.

