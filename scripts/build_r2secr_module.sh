#!/usr/bin/env bash
# Build r2secr.ko against a Homeware/OpenWrt kernel tree (run on Linux with cross toolchain).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/tools/secr/src/r2secrets.arm"
OUT="${ROOT}/tools/secr"

usage() {
  cat <<'EOF'
Usage: build_r2secr_module.sh

Required environment:
  KDIR          Path to built kernel (e.g. .../linux-4.1.52)
  CROSS_COMPILE e.g. aarch64-openwrt-linux-gnu- or aarch64-linux-gnu-
  ARCH          arm64 for GCNT-X (aarch64 4.1.52), arm for 32-bit boards

Example (values are placeholders — use your OpenWrt/staging tree):
  export KDIR=/path/to/linux-4.1.52
  export ARCH=arm64
  export CROSS_COMPILE=aarch64-linux-gnu-
  ./scripts/build_r2secr_module.sh

Output: r2secr.ko copied to tools/secr/r2secr.${ARCH}.custom.ko
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

: "${KDIR:?set KDIR to kernel build dir}"
: "${CROSS_COMPILE:?set CROSS_COMPILE}"
: "${ARCH:=arm64}"

cd "$SRC"
make -C "$KDIR" M="$PWD" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" modules
install -m 644 r2secr.ko "$OUT/r2secr.${ARCH}.custom.ko"
echo "built $OUT/r2secr.${ARCH}.custom.ko"
modinfo "$OUT/r2secr.${ARCH}.custom.ko" | rg 'vermagic|filename' || modinfo "$OUT/r2secr.${ARCH}.custom.ko" | head -5
