#!/usr/bin/env bash
# Offline RBI inspection: metadata, header TLVs, payload magic.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RBI="${1:-$ROOT/artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi}"
LOG_DIR="$ROOT/artifacts/logs"
mkdir -p "$LOG_DIR"

if [[ ! -f "$RBI" ]]; then
  echo "Missing RBI: $RBI" >&2
  exit 1
fi

BASE="$(basename "$RBI" .rbi)"
OUT="$LOG_DIR/rbi-inspect-${BASE}.txt"

{
  echo "=== file ==="
  file "$RBI"
  echo
  echo "=== stat ==="
  ls -la "$RBI"
  echo
  echo "=== shasum ==="
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$RBI"
  else
    sha256sum "$RBI"
  fi
  echo
  echo "=== xxd head 256 bytes ==="
  xxd -l 256 "$RBI"
  echo
  echo "=== rbi_header.py ==="
  python3 "$ROOT/scripts/rbi_header.py" "$RBI"
  echo
  echo "=== strings (board / product) ==="
  strings -a "$RBI" | rg -i 'BLI2|GCNT|EWA1330|Technicolor|boardname' | head -20 || true
} | tee "$OUT"

echo "Wrote $OUT"
