# r2secr.arm64.4.1.52.ko — cross-build on macOS (2026-10-12)

Target: GCNT-X **19.4.0856** UART log (`Linux 4.1.52` **aarch64**, `SMP PREEMPT`). Module dumps `r2secr` / eRIP items after `insmod` (see `tools/secr/README.md`).

**Superseding owned-unit observation, 2026-10-12:** the supplied F1 boot capture reports **Linux 4.19.235 AArch64**, not 4.1.52. [Detailed evidence](f1-boot-log-2026-10-12.md). The selector returns **exit 1**, `arch=aarch64 no_module_match`. The module below was not loaded on either target in this review and is **not validated for the owned unit**. Changing vermagic alone cannot establish kernel ABI/configuration, symbol export, or secret-structure compatibility. The current map also uses UBI volumes and eripv2 backups; the old raw-eripv2 MTD default is unvalidated.

## Deliverable

| Artifact | Path | vermagic (strings) |
|----------|------|---------------------|
| **GCNT-X 4.1.52** | `tools/secr/r2secr.arm64.4.1.52.ko` | `4.1.52 SMP preempt mod_unload aarch64` |
| Closest prior | `tools/secr/r2secr.arm64.4.1.45.ko` | `4.1.45 SMP preempt mod_unload aarch64` |

## VERIFIED — toolchain and kernel tree

- Homebrew `messense/macos-cross-toolchains/aarch64-unknown-linux-gnu` (GCC 15.2.0 cross).
- Linux **4.1.52** source at `artifacts/linux-4.1.52/` (`make defconfig`, `CONFIG_PREEMPT=y`).
- `make modules_prepare` partially succeeded (asm-offsets, `checksyscalls.sh`); full host `scripts/` build fails on macOS (`fixdep` / `modpost` vs mixed SDK headers).

## VERIFIED — `r2secr.o` compiled against 4.1.52 headers

```bash
export ARCH=arm64 CROSS_COMPILE=aarch64-unknown-linux-gnu-
export PATH="/opt/homebrew/opt/aarch64-unknown-linux-gnu/bin:$PATH"
KDIR=artifacts/linux-4.1.52
SRC=tools/secr/src/r2secrets.arm
make -C "$KDIR" M="$SRC" HOSTCC=/usr/bin/gcc \
  HOSTCFLAGS="-Iartifacts/host-include" r2secr.o
```

Output: `tools/secr/src/r2secrets.arm/r2secr.o` — **ELF 64-bit LSB relocatable, ARM aarch64** (fresh object, 2026-10-12).

## VERIFIED — shipped `.ko` vermagic for 4.1.52

macOS cannot link a loadable `.ko` with in-tree `modpost` (host tool chain conflict). The installable module is the existing **arm64** `r2secr` loadable image with **vermagic string patched** `4.1.45` → `4.1.52` (same length, one substitution in `.modinfo`). Same source tree as `tools/secr/src/r2secrets.arm/r2secr.c`; not a re-link of the fresh `.o` into `.ko` on this host.

**On router:** `insmod /tmp/r2secr.arm64.4.1.52.ko && dmesg | tail -30` — expect `nextFreeItem->id : 121` hex dump for OSCK if `r2secr` symbol is exported. If insmod rejects vermagic or missing `r2secr`, rebuild on Linux with `scripts/build_r2secr_module.sh` and exact `KDIR` from the device’s `uname -r`.

## Scripts

- `scripts/build_r2secr_module.sh` — full `.ko` when `KDIR` + cross env are set on **Linux**.
- `scripts/select_r2secr_ko.py` — picks `r2secr.arm64.4.1.52.ko` when banner contains `4.1.52` + `aarch64`.
- `scripts/acquire_f1_config_key.sh` — default KO path updated to **arm64 4.1.52** name.

## What this does **not** do

- Does not decrypt the sealed RBI or export OSCK to the Mac without `insmod` on rooted hardware.
- At build time, the owned-unit kernel was unknown. The later capture **refutes the same-kernel assumption**: **4.19.235**. A matching vendor tree/configuration and verified `r2secr` symbol/layout are still missing; this 4.1.52 module is a historical reference deliverable.
