# Boot-time SPL menu opened by holding `a` (GCNT-X, 23.1.b) — 2026-10-27

## Summary

**VERIFIED:** on this unit (23.1.b, `Board is FLD secure`, SPL `…-SECURE`), a stream of `a` keys sent while the router boots opens an SPL menu. Two boots showed it: one cold power-on and one web-UI restart. A control boot sent only CR and did not show it.

**VERIFIED:** the menu waits for input and did not advance on its own during the 90–150 s probe windows. After the menu opened, the only response to later `a` keys was echo. One CR sent afterwards returned only blank spaces. The router then stopped answering on 192.168.1.1 (HTTP 000, no ping). A power-cycle by hand is the only recovery we have tried.

**Not shown:** what each menu option does on this build; whether the menu times out; whether CR alone releases it; whether `go`, `r`, or `lb` do anything useful. Nothing here is a shell, root, or a flash read.

## Evidence

| Run | Log (artifacts/uart/2026-10-27/) | Keys sent | Result |
| --- | --- | --- | --- |
| Cold power-on, `a` at 0.1 s | `interrupt-probe-key-a-2.log` | 768 `a` (32 before menu) | SPL banner at line 68, menu at line 74; only `a` echo after; timeout |
| Cold power-on, control | `interrupt-probe-cr-control.log` | 29 CR at 1 s | Boot to Linux `mount_root`; no menu strings |
| Web-UI restart, `a` at 0.1 s | `interrupt-probe-restart-a.log` | 1264 `a` | SPL banner line 478, menu line 484; timeout; router unreachable afterwards |
| One CR after menu | `interrupt-probe-enter-after-menu.log` | 1 CR | 174 bytes, blank spaces only; `login.lp` HTTP 000 |

The web restart was sent with `scripts/f1_restart_router.py --base http://192.168.1.1 --yes`. It returned HTTP 200 with no login marker. That is the UI's `system_reboot` action, not `system_softReset`.

The earlier `a` run `interrupt-probe-key-a.log` (22:24) is inconclusive. The router was not powered inside that window, and the only router output was a leftover Linux fragment.

## Source (vendor copy, NOT matched to the device build)

Source: `board/broadcom/bcmbca/early_abort.c` from the 5.04behnd.4916 U-Boot tree (`RMerl/asuswrt-merlin.ng`, commit `ca72a61f8bc5ef920e29d63d53d9864262208f0c`). Fetched via `gh api`; not in the repo.

- DERIVED: `catch_early_abort()` listens for about 0.5 s for the byte `a`. On a match, it prints the menu and then reads input with `_get_chars('\r', …)`, so it blocks until a CR arrives. That fits the device staying parked.
- VERIFIED (text match): the menu strings in the device log match this source file exactly.
- VERIFIED (text mismatch): the device menu omits the `ddr`, `bid`, `mcb`, `id`, and `lb` lines that the source prints. So the device build is not this source, which matches the earlier finding in `f1-uboot-source-trace-2026-10-27.md`.
- DERIVED from the code, not tested: `jtag` calls the SOTP lock path (`SEC_CTRL_SOTP_LOCK_ALL`) and then the JTAG unlock. This is treated as a one-way action and is not to be sent.
- DERIVED from the code, not tested: `go` continues the boot, or jumps to a binary loaded over Ymodem if one was loaded. The loader (`lb`) is in the source, but the device menu does not list it, so its presence on this build is UNKNOWN. No signature check was seen on that path in the copy.

## Related claims (REPORTED, not reproduced)

The hack-technicolor issue #321 thread reports a CFE-style menu on a 19.x firmware: holding `a` at power-on gives `CFE-ROM WAS ABORTED … c continue / s DDR safe mode`. This unit runs SPL/U-Boot on 23.1.b, and the reported CFE menu is a different string. The two may share a trigger but are not the same menu. Source: [hack-technicolor issue #321](https://github.com/hack-technicolor/hack-technicolor/issues/321).

## Tools added (uncommitted until this commit)

- `scripts/f1_uart_interrupt_probe.py` — logs bytes, sends a key cycle or a single key, never `b`/`B`. Tests: `scripts/test_f1_uart_interrupt_probe.py`.
- `scripts/f1_restart_router.py` — one `system_reboot` POST after a saved-session check. Refuses without `--yes`. Never sends `system_softReset` or a factory reset. Tests: `scripts/test_f1_restart_router.py`.
- `scripts/f1_session_store.py` — `ensure_admin_session` takes `base=` (default unchanged, `192.168.2.1`).
- `scripts/f1_bootp_tftp_mac.py` — the BOOT-P run now saves the port's service config and restores it on exit (`--keep-ip` skips it). Tests: `scripts/test_f1_bootp_restore.py`. Not yet exercised against the router.

No credential values appear in any file above. The password is read from `artifacts/secrets/f1-admin.password`, which is gitignored.

## Reproduction

```bash
cd /Users/nils/genesis
python3 scripts/f1_uart_interrupt_probe.py /dev/cu.usbserial-0001 artifacts/uart/2026-10-27/<log>.log --timeout 90 --keys a --interval 0.1
python3 scripts/f1_restart_router.py --base http://192.168.1.1 --yes
python3 -m unittest scripts/test_f1_uart_interrupt_probe.py scripts/test_f1_restart_router.py scripts/test_f1_bootp_restore.py
```

## Next (not done)

1. Power-cycle the router and check the serial output for the TPL/U-Boot banner before anything else.
2. Warm-restart with CR only, to separate the `a` trigger from the restart itself.
3. Test whether a CR or a timeout releases the menu, with the log running the whole time.
4. Do not send `jtag`. Treat `go`/`lb` as a separate decision with its own review.

## Release test (2026-10-28): one CR released the menu

Run: `scripts/f1_menu_release_test.py` (sent `a` every 0.1 s until `Use enter to confirm` appeared, then one CR, then logged for 90 s), with a web restart via `scripts/f1_restart_router.py --yes`. Log: `artifacts/uart/2026-10-28/menu-release-test.log`.

- VERIFIED: menu line at log line 276; the single CR was sent at line 279; the boot then continued through SPL to U-Boot TPL (line 580), U-Boot 2019.07 (line 689), `Press b` (line 835), and Linux `mount_root` (line 1217).
- VERIFIED: `Booting : Bank 2` (line 839). Linux came up.
- Not shown: whether CR is needed at all. There was no run that waited without CR, so the timeout behavior is still unknown.
- One run. Not repeated, by request.

Earlier 2026-10-28 control (`interrupt-probe-restart-cr-control-3.log`): CR-only web restart with no `a` booted through SPL with no menu. Result: holding `a` is the trigger on a warm restart, as on a cold boot.

Probe bugs fixed on 2026-10-28 (both in `scripts/f1_uart_interrupt_probe.py`): the Linux banner counted as a stop marker before SPL, and SPL scrolled out of the 512-byte stop window. Tests: `scripts/test_f1_uart_interrupt_probe.py`.
