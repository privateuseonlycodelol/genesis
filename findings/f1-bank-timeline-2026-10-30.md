# Boot-bank timeline and bank-swap runbook (2026-10-30)

## Question

Which bank did the 23.1.b unit boot, when did it change, and can the SPL menu swap banks on purpose?

## Result

**The committed bank was switched to Bank 2 inside the 22:01 probe session, by U-Boot's own metadata path, not by a key the probe sent.** The log shows `Getting committed 1 valid 1,2 seq 2,1`, then UBI metadata1 and metadata2 removed and recreated, then `Setting committed 2 valid 0,2 seq 2,1` (`artifacts/uart/2026-10-27/interrupt-probe-20261027-220151.log` lines 4215–4238). The next boot is Bank 2 (line 4285). The probe sent only space and Ctrl-C in the minutes before that. **The trigger inside U-Boot is UNKNOWN.** No live device contact was made in this pass. The bank-swap test is a runbook below and has **not** been run.

## Timeline (boot banks from UART logs)

Each row is the `Booting : Bank N` line and the boot-order line in the named log. Times are the file's last-save time, not the boot time.

| Log (artifacts/uart/…) | Saved | Booted | Boot order | Status |
| --- | --- | --- | --- | --- |
| `2026-10-27/router-boot-20261027-010457-82769.log` (and -012651, -014657) | 10-27 01:08–01:48 | Bank 2 | `5 3` | VERIFIED |
| BOOT-P bundle run (see [tried.md](tried.md) 19:09 entry) | 10-27 19:09 | Bank 2 → Bank 1 (commit) | `3 5` after | VERIFIED per tried.md and session log |
| `2026-10-27/passive-20261027-195325.log` | 10-27 19:55 | Bank 1 | `3 5` | VERIFIED (lines 594, 1609) |
| `2026-10-27/interrupt-probe-20261027-220151.log` | 10-27 22:04 | Bank 1 (three boots, lines 807, 1577, 2892); then commit to Bank 2 (lines 4215–4238), then Bank 2 boot (line 4285) | `3 5` → `5 -1` | VERIFIED |
| `2026-10-27/interrupt-probe-boot.log` | 10-27 22:08 | Bank 2 (lines 795, 2144) | `5 -1` | VERIFIED |
| `2026-10-27/interrupt-probe-{keys,cr-control,restart-a,…}.log` | 10-27 22:10–22:43 | Bank 2 | `5 -1` | VERIFIED (from the Booting line; not every file checked line by line) |
| `2026-10-28/*.log` (interrupt-probe-restart-cr-control*, menu-release-test, menu-recovery-test, menu-recovery-test-r1) | 10-28 13:26–13:44 | Bank 2 | `5 -1` | VERIFIED |

- **VERIFIED:** U-Boot printed `Setting committed 2 valid 0,2 seq 2,1` (line 4238) before the Bank 2 boot. This is the commit that moved the bank. The earlier 22:08 log has no commit line, because the flip had already happened.
- **VERIFIED:** the sequence in the 22:01 log is `Read … metadata1 returned 0`, `Getting committed 1 valid 1,2 seq 2,1`, `Remove UBI volume metadata1`, `Remove UBI volume metadata2`, then the commit to 2. This is the same metadata path the BOOT-P bundle run used on 19:09 (see [tried.md](tried.md)).
- **Not shown:** what caused U-Boot to run that metadata path at that boot. Only space and Ctrl-C were sent during the surrounding minutes, and the probe's allowlist excludes `r` (script line 23).

## What the probe sent (VERIFIED from source and log)

- `scripts/f1_uart_interrupt_probe.py` sets `ALLOWED_KEYS = KEY_CYCLE + (a, space, ^C)` (line 23). It never sends `b`/`B` (BOOT-P) and it cannot send `r`.
- `interrupt-probe-boot.log` shows `# sent b' '` and `# sent b'\x03'` at the start. The script's `KEY_CYCLE` contents were not checked in this pass.
- **DERIVED:** the probe did not send the SPL fallback key `r`. A bank change inside its window needs another explanation (a restart, the boot itself, or an earlier event). This is a hypothesis, not a finding.

## Hypotheses for the metadata rewrite (to test offline first)

- **H1 (U-Boot commit path on a boot with a bad or stale metadata read):** the log shows `read from metadata1 returned 0`, then U-Boot recreated both metadata volumes and committed Bank 2. Check: the `read from metadata1 returned 0` context and whether the same message appears in the 10-28 or earlier logs.
- **H2 (a key in the SPL window):** a space or Ctrl-C sent during boot changed the SPL state. Check: what was sent right before the metadata read in the 22:01 log (already shown: space and Ctrl-C, same as earlier boots that did not commit).
- **H3 (owner or restart script):** `scripts/f1_restart_router.py` or a power action changed state. Check: the restart records for 10-27 between 22:01 and 22:08.

**Checked:** the `metadata1 returned`, `Getting committed`, and `Setting committed` lines appear in **only** `interrupt-probe-20261027-220151.log` (3 hits, lines 4214, 4215, 4238) across all 10-27 and 10-28 UART logs. The 19:09 BOOT-P commit (2 to 1) is recorded in the BOOT-P session log, not in these UART files. So the metadata path is seen once in the UART record, and H1 cannot be tested against other UART boots yet.

## Bank-swap runbook (NOT RUN)

**Gate:** owner present at the device, UART logging on, and explicit go-ahead. Do not start without all of these.

1. **Before state:** power-cycle with no keys sent (passive capture). Record the `Booting : Bank N` line and the `Volume Boot Order` line. Expected: Bank 2 (`5 -1`), per the 10-28 logs.
2. **Test:** the SPL menu is entered by sending `a` during boot (per [f1-boot-menu-a-key-2026-10-27.md](f1-boot-menu-a-key-2026-10-27.md): `a` every 0.1 s, menu at about line 74 after 32 keys). Sequence: power-cycle, send `a` repeatedly until the SPL menu banner appears, then send `r` + CR, wait 5 s, then `go` + CR. Do not send `r 1` (recovery, ignored by the behnd TPL per [f1-unturned-stones-2026-10-29.md](f1-unturned-stones-2026-10-29.md)). Capture the whole run. (Corrected 2026-10-30: the earlier wording omitted the `a` entry step.)
3. **Expected if the source trace is right (DERIVED):** `r` selects fallback, and the boot moves to Bank 1 (`selected_img_idx = 3 - committed`). Pass = next `Booting : Bank 1` line after the swap, with boot order `3 5` or the equivalent.
4. **Fail condition:** Bank 2 boots again, or the menu does not appear. Record it as a negative result in `tried.md`. Do not retry more than once in the same session.
5. **After:** power-cycle to the state the owner wants, and record the final bank.

**Never send:** `jtag` (calls `SEC_CTRL_KEY_CLEAN_ALL` and `SEC_CTRL_SOTP_LOCK_ALL`, which erase keys); `b`/`B` (BOOT-P, which writes flash); `rpc.system.switchover` (a reboot-based write that is a separate test).

**Unknown before the test:** whether `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT` is set on this board (so a commit may roll back on its own, which would confound the result). The 22:01 log has no `fallback` line (checked). Check the next boot after step 2 for any fallback message.

**Note:** the commit from 22:01 means the device is now committed to Bank 2 unless something reversed it. The 10-28 logs confirm Bank 2 boots after that.

## What was not shown

- The cause of the 22:04–22:08 flip.
- Whether the device rolls back committed banks automatically.
- That `r` + `go` swaps banks on this unit. Only the source trace says so.

## Reproduction (offline, no device contact)

```bash
cd /Users/nils/genesis
grep -a -n -E "Booting +:|Volume Boot Order" artifacts/uart/2026-10-27/interrupt-probe-20261027-220151.log artifacts/uart/2026-10-27/interrupt-probe-boot.log
grep -n "ALLOWED_KEYS" scripts/f1_uart_interrupt_probe.py
grep -a -n -i -E "committed|fallback|check_fallback" artifacts/uart/2026-10-27/interrupt-probe-*.log
```

## Live result (2026-10-30, swap test run)

- **VERIFIED:** the SPL menu opened after `a` keys at 0.1 s. Menu text: `r - Boot Fallback; 1 - recovery`, `go - continue or run from uart loaded binary`, `jtag - Unlock JTAG`, `wdt`, `h` (`~/Desktop/bank-swap-20261030-032340.log`, lines 60-75).
- **VERIFIED:** `r` + CR and `go` + CR were sent (lines 298-299). The boot after them was **Bank 2** with boot order `5 -1` (lines 620, 851). No `Setting committed` line. The only `fallback` hit is the menu text.
- **Result:** NEGATIVE for the `r` fallback swap on this unit. The source-based expectation (Bank 1) did not hold. The run also does not reach the `# end` marker, so the rest of that boot is not captured.
- **Not shown:** why `r` did not swap. Possible causes: fallback is not compiled into this build, the flag needs another key, or the menu input path differs from the source. Tested: one run only.
- **Logged:** [tried.md](tried.md) (2026-10-30 entry). No further live keys sent.

## Correction (2026-10-30, reverse-engineering pass)

- **VERIFIED:** `early_abort.c` and `selected_img_idx` are **not** in `artifacts/` (`find` and `grep` return nothing). The swap explanation in step 3 above, and in [f1-unturned-stones-2026-10-29.md](f1-unturned-stones-2026-10-29.md), cites a source copy that cannot be re-checked here. Treat `selected_img_idx = 3 - committed` and the `r` fallback mechanism as **UNVERIFIED**.
- **VERIFIED:** `do_check_fallback` (`artifacts/firmware/vendor-uboot-bcmbca-5.04behnd/sdk_test_commands.c:2921-2950`) is compiled only with `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT` (line 2920). It counts failed boots and calls `reset` below the threshold; it does **not** pick a bank. Whether this build enables the flag is still UNKNOWN.
- **Blocked:** the bank-select code for the SPL `r` path needs the SPL image itself (from a NAND dump or a vendor build that matches the device), which is not in the repo.
