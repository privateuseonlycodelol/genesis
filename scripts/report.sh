#!/usr/bin/env bash
# Write findings/latest.md — small snapshot for Project "check genesis".
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p findings artifacts/{firmware,captures,logs}

OUT="findings/latest.md"
USER_NOTE="${1:-artifacts/logs/user-note.txt}"

shasum_rbi() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  else
    return 1
  fi
}

{
  echo "# Genesis report"
  echo
  echo "**Generated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "**Host:** (omitted)"
  echo
  echo "## UI grab reviews (newest first)"
  echo "- [\`f1-grab-notloggedin-2026-10-12.md\`](findings/f1-grab-notloggedin-2026-10-12.md) — \`notloggedin.zip\` is admin duplicate of ~05:57 grab, not logged-out"
  echo "- [\`f1-grab-045648-review.md\`](findings/f1-grab-045648-review.md) — finished 04:56:48Z zip; verbatim bodies; GET JSON"
  echo "- [\`f1-grab-040001-review.md\`](findings/f1-grab-040001-review.md) — script repair vs 03:38"
  echo "- [\`f1-grab-033853-review.md\`](findings/f1-grab-033853-review.md) — integrity, crypto, runtime map"
  echo
  echo "## LAN surfaces (non–port-80)"
  echo "- **CUPS :631** — [\`docs/f1-cups-631.md\`](docs/f1-cups-631.md) · [\`f1-cups-ipp-policy-2026-10-12.md\`](findings/f1-cups-ipp-policy-2026-10-12.md) · [\`f1-cups-ipp-readonly-matrix-2026-10-12.md\`](findings/f1-cups-ipp-readonly-matrix-2026-10-12.md)"
  echo "- **WFA WLANConfig :49152** — [\`f1-wfa-wlanconfig-49152-2026-10-12.md\`](findings/f1-wfa-wlanconfig-49152-2026-10-12.md)"
  echo "- **Listener inventory** — [\`management-auth-boundaries-2026-10-12.md\`](findings/management-auth-boundaries-2026-10-12.md)"
  echo

  for dir in artifacts/firmware artifacts/captures artifacts/logs; do
    echo "## \`$dir\`"
    echo '```'
    _u="$(whoami 2>/dev/null || echo user)"
    ls -la "$dir" 2>/dev/null | sed -E "s/ ${_u}  staff / user  staff /g" || echo "(missing)"
    echo '```'
    echo
  done

  shopt -s nullglob
  rbis=(artifacts/firmware/*.rbi)
  if ((${#rbis[@]} > 0)); then
    echo "## RBI checksums"
    echo '```'
    shasum_rbi "${rbis[@]}"
    echo '```'
    echo
  fi

  lcm_logs=(artifacts/logs/lcm*.json)
  if ((${#lcm_logs[@]} > 0)); then
    echo "## LCM probe JSON"
    for f in "${lcm_logs[@]}"; do
      echo "### \`$(basename "$f")\`"
      echo '```json'
      cat "$f"
      echo '```'
      echo
    done
  fi

  echo "## Findings"
  for f in findings/*.md; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "latest.md" ]] && continue
    echo "- [\`$(basename "$f")\`]($f)"
  done
  echo

  if [[ -f artifacts/logs/decrypt-attempt-19x.txt ]] || [[ -f artifacts/logs/decrypt-attempt2.txt ]] || [[ -f artifacts/logs/decrypt-attempt3.txt ]]; then
    echo "## 19.x reference RBI (offline)"
    if [[ -f artifacts/logs/decrypt-attempt3.txt ]]; then
      echo "### attempt3 (boot-log derivations, latest)"
      echo '```'
      tail -n 12 artifacts/logs/decrypt-attempt3.txt
      echo '```'
      echo
    fi
    if [[ -f artifacts/logs/decrypt-attempt2.txt ]]; then
      echo "### attempt2"
      echo '```'
      tail -n 12 artifacts/logs/decrypt-attempt2.txt
      echo '```'
      echo
    fi
    if [[ -f artifacts/logs/decrypt-attempt-19x.txt ]]; then
      echo "### attempt1 (57-key baseline)"
      echo '```'
      tail -n 6 artifacts/logs/decrypt-attempt-19x.txt
      echo '```'
      echo
    fi
    echo 'Deep dive: `findings/gcnt-x-19x-deep.md` · Crypto: `findings/rbi-crypto-attempt3.md` · Root path (lab): `findings/gcnt-x-root-path.md`'
    echo
  fi

  if [[ -f "$USER_NOTE" ]]; then
    echo "## User note (last 20 lines)"
    echo '```'
    tail -n 20 "$USER_NOTE"
    echo '```'
    echo
  elif [[ ! -t 0 ]]; then
    stdin_tail="$(tail -n 20)"
    if [[ -n "${stdin_tail//[[:space:]]/}" ]]; then
      echo "## User stdin (last 20 lines)"
      echo '```'
      printf '%s\n' "$stdin_tail"
      echo '```'
      echo
    fi
  fi
} > "$OUT"

echo "Wrote $OUT"
