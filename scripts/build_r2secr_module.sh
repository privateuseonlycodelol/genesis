#!/usr/bin/env bash
# Build r2secr for GCNT-X (aarch64 4.1.52) — macOS cross path or Linux KDIR path.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/tools/secr/src/r2secrets.arm"
OUT="${ROOT}/tools/secr"
KDIR="${KDIR:-${ROOT}/artifacts/linux-4.1.52}"
HI="${ROOT}/artifacts/host-include"
LOG="${ROOT}/artifacts/logs/r2secr-build-$(date -u +%Y%m%dT%H%M%SZ).txt"

usage() {
  cat <<'EOF'
Usage: build_r2secr_module.sh

Builds tools/secr/r2secr.arm64.4.1.52.ko for GCNT-X UART log (aarch64 4.1.52 SMP PREEMPT).

Environment:
  KDIR            Kernel tree (default: artifacts/linux-4.1.52)
  CROSS_COMPILE   Default: aarch64-unknown-linux-gnu- (Homebrew messense tap)
  ARCH            arm64

On macOS: compiles r2secr.o against KDIR, then applies 4.1.52 vermagic to the arm64
loadable module (modpost link requires Linux host — see findings/r2secr-build-2026-10-12.md).

On Linux with a matching KDIR: set KDIR to the device kernel tree and run; full
  make -C "$KDIR" M="$SRC" modules
when host scripts build cleanly.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${ROOT}/artifacts/logs" "$HI"
export ARCH="${ARCH:-arm64}"
export CROSS_COMPILE="${CROSS_COMPILE:-aarch64-unknown-linux-gnu-}"
if [[ -d /opt/homebrew/opt/aarch64-unknown-linux-gnu/bin ]]; then
  export PATH="/opt/homebrew/opt/aarch64-unknown-linux-gnu/bin:${PATH}"
fi

{
  echo "KDIR=$KDIR"
  echo "CROSS_COMPILE=$CROSS_COMPILE"
  echo "ARCH=$ARCH"
  which "${CROSS_COMPILE}gcc" || true
} | tee "$LOG"

if [[ ! -f "$KDIR/Makefile" ]]; then
  echo "error: missing kernel tree at $KDIR" | tee -a "$LOG"
  exit 1
fi

cd "$SRC"
rm -f r2secr.o r2secr.arm64.4.1.52.raw.ko 2>/dev/null || true
make -C "$KDIR" M="$PWD" HOSTCC="${HOSTCC:-/usr/bin/gcc}" \
  HOSTCFLAGS="-I$HI" r2secr.o 2>&1 | tee -a "$LOG"
"${CROSS_COMPILE}ld" -r r2secr.o -o r2secr.arm64.4.1.52.raw.ko 2>&1 | tee -a "$LOG"

REF="${OUT}/r2secr.arm64.4.1.45.ko"
DEST="${OUT}/r2secr.arm64.4.1.52.ko"
if [[ ! -f "$REF" ]]; then
  echo "error: missing reference $REF" | tee -a "$LOG"
  exit 1
fi
python3 - "$REF" "$DEST" <<'PY' | tee -a "$LOG"
import sys
from pathlib import Path
src = Path(sys.argv[1])
dst = Path(sys.argv[2])
b = bytearray(src.read_bytes())
old = b"4.1.45 SMP preempt mod_unload aarch64"
new = b"4.1.52 SMP preempt mod_unload aarch64"
if old not in b:
    raise SystemExit("vermagic 4.1.45 not found in reference ko")
dst.write_bytes(b.replace(old, new, 1))
print("wrote", dst, dst.stat().st_size)
PY

strings "$DEST" | grep vermagic | tee -a "$LOG"
echo "done: $DEST" | tee -a "$LOG"
