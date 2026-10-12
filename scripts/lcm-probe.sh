#!/usr/bin/env bash
# Probe Telia LCM for GCNT-X firmware channel manifests (23.1 / 23.1.b).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${LOG_DIR:-artifacts/logs}"
mkdir -p "$LOG_DIR"

BOARD="${GENESIS_BOARD:-GCNT-X}"
CHAN="${GENESIS_CHAN:-f1_1.0-1}"
if [[ -z "${GENESIS_SERIAL:-}" ]]; then
  echo "Set GENESIS_SERIAL (unit serial; not stored in the public repo)." >&2
  exit 1
fi
SERIAL="$GENESIS_SERIAL"
BASE="${GENESIS_LCM_BASE:-http://lcm.teliasmartrgw.com/ipk/hw}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

probe() {
  local ver="$1"
  local url="${BASE}/${BOARD}/fw/${ver}/chan/${CHAN}/sn/${SERIAL}"
  local out="${LOG_DIR}/lcm-${ver}-${STAMP}.json"
  local stable="${LOG_DIR}/lcm-${ver}.json"

  echo "GET $url"
  if curl -sSL --max-time 45 "$url" -o "$out"; then
    cp "$out" "$stable"
    echo "  -> $out"
  else
    printf '{"error":"curl failed","version":"%s","url":"%s"}\n' "$ver" "$url" > "$out"
    cp "$out" "$stable"
    echo "  -> $out (curl error)" >&2
  fi
}

probe "23.1"
probe "23.1.b"
