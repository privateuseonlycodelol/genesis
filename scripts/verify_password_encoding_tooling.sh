#!/usr/bin/env bash
# Offline gate before any live password-change experiment.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/scripts/password-encoding"
npm install --no-audit --no-fund
npm test
cd "$ROOT"
python3 -m unittest scripts.test_f1_password_blob scripts.test_f1_password_encoding_impact -v
