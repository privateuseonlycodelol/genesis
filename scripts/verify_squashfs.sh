#!/usr/bin/env bash
# Look for squashfs magic in a tree or file; optionally unsquashfs to OUT_DIR.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$ROOT/artifacts/extracted/19x-reference}"
OUT_DIR="${2:-$TARGET/squashfs-root}"
LOG_DIR="$ROOT/artifacts/logs"
mkdir -p "$LOG_DIR"

OUT="$LOG_DIR/verify-squashfs-$(basename "$TARGET").txt"

{
  echo "=== target ==="
  echo "$TARGET"
  echo
  if [[ -f "$TARGET" ]]; then
    echo "=== binwalk (file) ==="
    binwalk "$TARGET" 2>/dev/null || true
    echo
    echo "=== squashfs offsets (rg hsqs) ==="
    xxd "$TARGET" | rg 'hsqs' | head -5 || echo "(no hsqs magic)"
  elif [[ -d "$TARGET" ]]; then
    echo "=== find hsqs in tree ==="
    find "$TARGET" -type f -size +1k 2>/dev/null | while read -r f; do
      if xxd -l 4 "$f" 2>/dev/null | rg -q 'hsqs'; then
        echo "squashfs: $f"
      fi
    done
    echo
    echo "=== unsquashfs candidates ==="
    find "$TARGET" -name '*.squashfs' -o -name 'squashfs.img' 2>/dev/null | head -10
  else
    echo "Target missing (expected decrypted bin or extract dir)"
  fi

  if command -v unsquashfs >/dev/null 2>&1; then
    IMG="$(find "$TARGET" -type f \( -name '*.squashfs' -o -name 'squashfs.img' \) 2>/dev/null | head -1 || true)"
    if [[ -n "$IMG" && -f "$IMG" ]]; then
      echo
      echo "=== unsquashfs $IMG -> $OUT_DIR ==="
      rm -rf "$OUT_DIR"
      mkdir -p "$(dirname "$OUT_DIR")"
      unsquashfs -d "$OUT_DIR" -f "$IMG" && echo "OK: $OUT_DIR"
    fi
  fi
} | tee "$OUT"

echo "Wrote $OUT"
