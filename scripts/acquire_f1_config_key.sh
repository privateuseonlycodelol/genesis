#!/usr/bin/env bash
# Acquire RIP_ID_RANDOM_KEY_B (config.bin AES/HMAC key) on a *rooted* GCNT-X / Homeware gateway.
# Does not run from the Mac against an unrooted Telia 23.1.b box — copy secr/*.ko to USB first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECR="${ROOT}/tools/secr"
OUT="${1:-/tmp/f1-rip-keys}"

usage() {
  cat <<'EOF'
Usage: acquire_f1_config_key.sh [output-dir]

Run ON THE ROUTER as root (or via SSH), after copying matching r2secr.*.ko to /tmp.

Steps performed:
  1. uname -a (logged, not printed here if redirected)
  2. insmod r2secr.<matching>.ko ; dmesg tail → ECK (16 bytes)
  3. dd if=/dev/mtdX of=mtd-eripv2.bin (you must set MTD_DEV below)
  4. python3 eripv2.py on host with --eckey from dmesg

Set MTD_DEV to the eripv2 partition (often mtd5 on older maps; confirm with cat /proc/mtd).
On GCNT-X 19.x public logs the partition is named "eripv2" (256 KiB).

This script is a checklist wrapper; edit MTD_DEV and KO path before use.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# --- edit for your kernel / layout ---
KO="/tmp/r2secr.arm.4.1.52_p2v8.ko"
MTD_DEV="/dev/mtd4"
# ------------------------------------

mkdir -p "$OUT"
echo "output_dir=$OUT"
echo "ko=$KO"
echo "mtd=$MTD_DEV"

if [[ ! -f "$KO" ]]; then
  echo "error=missing_ko" >&2
  exit 1
fi

insmod "$KO" || true
dmesg | tail -n 30 >"$OUT/dmesg-r2secr.tail.txt"

if [[ -e "$MTD_DEV" ]]; then
  dd if="$MTD_DEV" of="$OUT/eripv2.mtd.bin" bs=4096
else
  echo "warn=mtd_missing" >&2
fi

cat <<EOF
next_on_pc:
  Parse ECK hex from $OUT/dmesg-r2secr.tail.txt (last r2secr data line).
  tools/venv/bin/python3 $SECR/eripv2.py --eripv2 $OUT/eripv2.mtd.bin --eckey '<16-byte hex>'
  Look for dumped file RIP_ID_RANDOM_KEY_B_0x0108-* (64 bytes).
  Decrypt export:
  tools/venv/bin/python3 $ROOT/scripts/decrypt_f1_config_export.py \\
    path/to/config.bin --randb RIP_ID_RANDOM_KEY_B_0x0108-* --output config.plain
EOF
