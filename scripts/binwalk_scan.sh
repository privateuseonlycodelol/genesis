#!/usr/bin/env bash
# Binwalk signature scan + entropy plot for an RBI or decrypted .bin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUT="${1:-$ROOT/artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi}"
LOG_DIR="$ROOT/artifacts/logs"
mkdir -p "$LOG_DIR"

if [[ ! -f "$INPUT" ]]; then
  echo "Missing file: $INPUT" >&2
  exit 1
fi

if ! command -v binwalk >/dev/null 2>&1; then
  echo "binwalk not installed (brew install binwalk)" >&2
  exit 1
fi

BASE="$(basename "$INPUT")"
OUT="$LOG_DIR/binwalk-${BASE}.txt"
ENTROPY_PNG="$LOG_DIR/${BASE}.png"

{
  echo "=== binwalk ==="
  binwalk "$INPUT"
  echo
  echo "=== binwalk -e (extract) ==="
  EXTRACT_DIR="$LOG_DIR/_${BASE}.extracted"
  rm -rf "$EXTRACT_DIR"
  mkdir -p "$EXTRACT_DIR"
  (cd "$EXTRACT_DIR" && binwalk -e "$INPUT") || echo "(no extractable signatures)"
  echo
  echo "=== extract dir ==="
  find "$EXTRACT_DIR" -type f 2>/dev/null | head -50 || true
} | tee "$OUT"

if binwalk -E "$INPUT" -O "$ENTROPY_PNG" >/dev/null 2>&1; then
  echo "Entropy plot: $ENTROPY_PNG"
fi

echo "Wrote $OUT"
