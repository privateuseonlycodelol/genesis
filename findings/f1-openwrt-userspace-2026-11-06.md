# OpenWrt on this F1 — 2026-11-06

## Result

There is no OpenWrt firmware for GCNT-X / EWA1330. OpenWrt 25.12.6 has no BCM6856 target. This unit's bootloader checks the signature on `bootfs`. An unsigned kernel hangs. `CONFIG_KEXEC` is absent from the running config, and `CONFIG_MODULE_SIG_FORCE` is set, so a second kernel cannot be loaded from Linux and an OpenWrt kernel module cannot be inserted.

The outside path that does run is an aarch64 userspace under the vendor kernel.

**VERIFIED.** The kernel is aarch64 and has `CONFIG_BINFMT_ELF` and `CONFIG_COMPAT_BINFMT_ELF`.

- A static aarch64 glibc program, `/tmp/aa64hello`, printed `aarch64-ok pid=15138` and exited 0. SHA-256 `f40a6190370304f55d16ea4991bdbb2aa2cd9d51ee78e3e79b8dc33a7e1ed81e`.
- Alpine 3.14 musl BusyBox, invoked as `/tmp/ld-musl-aarch64.so.1 /tmp/busybox`, printed `musl-ok` and `Linux OpenWrt 4.19.235 ... aarch64 Linux`. BusyBox SHA-256 `46ea456e6a74d6686d79869aec1c451c60b06380d7ae9416cb2bb77d00ec8bac`. Loader SHA-256 `55f53a6f9566281f21772a5d84119ee233028daa4e159b4ff04fa47da229ffda`. Both were removed from `/tmp` afterward.
- `dnsproxy` stayed pid 8717. Init was not replaced. No volume was written.

OpenWrt's aarch64 userspace is the same kind of musl binary. A chroot of an older aarch64 OpenWrt root can therefore run on this kernel. A 2026 OpenWrt userspace was not tried. It would see the network interfaces this kernel already created. It would not bring Broadcom Wi-Fi or switch drivers of its own.

A public report of mainline U-Boot on a BCM96856 board used Broadcom CFE, reported 128 MiB of RAM, and had no Ethernet. This unit's boot log is Vantiva U-Boot, not CFE. That chainload does not apply here.

## What was not shown

An OpenWrt rootfs as the boot userspace. Overlaying `/sbin/init` was not done. A current OpenWrt release was not unpacked. Nothing here survives as a replacement for the signed image.
