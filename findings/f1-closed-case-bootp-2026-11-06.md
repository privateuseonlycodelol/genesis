# Closed-case BOOT-P entry — offline, 2026-11-06

No device contact. No flash, no SSH, no live POST. Images: `artifacts/firmware/flash-2026-11-06/bootfs1-uboot.bin` (3,298,984 bytes, AArch64, not ELF), `bootfs1-fdt-GCNT-X.dtb`, `loader.mtd1.bin`, `dri.mtd2.bin`, and the bank-1 ROM tree `artifacts/firmware/rom-2026-11-06/rom`. The October UART index already shows `Initializing U-Boot...` then `*** Press b to enter BOOT-P ***` on the same boot (`findings/f1-boot-log-2026-10-12-evidence.md` L0534, L0588).

## Verdict

One closed-case candidate is real in the bytes and still untested on the running router: an authenticated UI action writes the prozone bootp bit, and early U-Boot enters BOOT-P when that bit is the only one set in the low byte. The outside reset button is wired to the same action, but the U-Boot poll window is shorter than the 5 second hold, so a case-closed press is not expected to win. Nothing here is an unauthenticated LAN root.

## Prozone flag (DERIVED from the image, not live)

`/usr/bin/bootp` is a 103-byte script: write `1` to `/proc/prozone/bootp`, set reboot reason `BOOTP`, reboot. `rpc_system.ca` runs that script for `sys.bootp.enable`. `system-config-modal.lp` handles POST `action=system_bootp` by `proxy.set("sys.bootp.enable","1")` with no role check in that branch. The visible “LAN Upgrade” button is separate: `etc/config/web` feature `bootp` lists role `superuser` only, and `variant_helper.lua` `showLanUpgrade` is true. nginx session auth on the modal is unchanged from earlier passes. No TR-069/USP map names `sys.bootp`. `POST system_bootp` is still not tested on :80.

`platform.ko` `prozone_bootp_proc_write` stores that value in prozone area 8, bit 0. U-Boot’s early init (`Initializing U-Boot...`, call into the checker at file offset `0xb84dc`) reads the same area id 8. If the low byte is exactly 1, it prints `BLFLAG_ENABLE is set, Entering into boot-p`, clears bit 0, and branches to the same BOOT-P function the serial `b` path uses. `bootfail` is bit 5 of that same word (`mask 0x20`). `etc/init.d/zprozone` writes `0` to `bootfail`, `bootcounter`, and `bootbank` after a successful Linux start; it does not clear `bootp`. A crash loop that leaves bit 5 set does not take the “exactly 1” branch.

## Reset button (DERIVED timing, not live)

`fdt_GCNT-X` has one button node: `/buttons` compatible `tch,buttons`, child `push_button`, `ext_irq` second cell `0xc` (GPIO 12). `hold` is `bootp_cmd = <5>`. `release` is `reset`. The press text says “Hold for 5s to do restore to default”; that string is not the action. U-Boot multiplies the numeric property by 1000 and stores milliseconds, so the hold is 5 seconds. The handler sets a flag and prints `Please release the button`.

The only boot caller of the checker is that early-init function. Inside it, the prompt loop is 15 non-blocking serial polls separated by `udelay(200000)` (3.0 seconds of delay). The button flag is read once, after the loop. GPIO sampling for this node starts in that function, after the phy init already visible in the October log, not in the loader. `loader.mtd1.bin` has `Boot Fallback` / `recovery` strings and no `BOOT-P`, `push_button`, or `tch,buttons`. A 5 second hold does not fit in the 3 second window. Holding the button only after Linux is up still runs `etc/rc.button/reset` (`jffs2reset` at `SEEN >= 5`). `technicolor_button.ko` `gpio_buttons_gcntx` maps that same GPIO 12 to `BTN_0`, which `etc/config/button` calls the reset button.

Other boards inside `dri.mtd2.bin` label `push_button` “Hold for 5s to enter into bootp”. That label is not the GCNT-X node.

## Other candidates

- **RUDI frame during the prompt.** The same loop clears, then polls, a flag the image’s strings call `magic packet`. The setter is a short RUDI header check in the bootloader, not Wake-on-LAN. `etc/init.d/wol` is a userspace proxy for other hosts. The October log puts `XRDP Ethernet driver un-initialize` on the same record as the prompt, so the NIC is up and then torn down in that window. No frame was sent.
- **U-Boot shell.** The image contains an autoboot-password function. Captured boots print `Press b`, not `Enter password in %d seconds to stop autoboot`. The indexed log has no `=>` prompt. This is serial-only even if some other boot state reached it.
- **Boot-fail counter.** This U-Boot image has no `do_check_fallback` / `failed count` strings. The vendor file `sdk_test_commands.c` is a different tree (`findings/f1-uboot-source-trace-2026-10-27.md`). The counter bits are not the bootp bit.
- **`rootfs_data` from Linux.** `flash_upgrade_img_bundle` still writes that volume only after BOOT-P is already entered. No new userspace writer turned up outside the script above.

## What was not shown

A live POST, a live prozone write, a power-on button hold, or a frame during the prompt. No unauthenticated path to `/usr/bin/bootp`.
