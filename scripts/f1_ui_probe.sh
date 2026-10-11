#!/usr/bin/env bash
# Gentle F1 UI probe: curl-only HTTP, 2s between requests. Password in F1_PASSWORD env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${F1_BASE:-http://192.168.2.1}"
COOKIE="${F1_COOKIE_JAR:-artifacts/ui/f1-cookies.txt}"
UI_DIR="artifacts/ui"
mkdir -p "$UI_DIR"

pause() { sleep 2; }

http_code() {
  curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$1"
}

CODE="$(http_code "$BASE/login.lp")"
if [[ "$CODE" == "503" ]]; then
  echo "still cooling down, user should wait or reboot once"
  exit 0
fi
if [[ "$CODE" != "200" ]]; then
  echo "login.lp HTTP $CODE — stopped"
  exit 1
fi

pause
curl -s -c "$COOKIE" -b "$COOKIE" -o "$UI_DIR/login.lp.html" "$BASE/login.lp"
CSRF="$(python3 -c "import re, pathlib; h=pathlib.Path('$UI_DIR/login.lp.html').read_text(); m=re.search(r'CSRFtoken\"\\s+content\\s*=\\s*\"([^\"]+)\"', h, re.I); print(m.group(1) if m else '')")"
if [[ -z "$CSRF" ]]; then
  echo "no CSRF — stopped"
  exit 1
fi
python3 -c "import re, pathlib; p=pathlib.Path('$UI_DIR/login.lp.html'); t=p.read_text(); p.write_text(re.sub(r'(CSRFtoken\"\\s+content\\s*=\\s*\")[^\"]+(\")', r'\\1REDACTED\\2', t, flags=re.I))"

STATE="$(python3 scripts/f1_srp_login.py prepare)"
A_HEX="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['A_hex'])" "$STATE")"

pause
curl -s -c "$COOKIE" -b "$COOKIE" -o "$UI_DIR/auth-identify.json" -w "%{http_code}" \
  -X POST "$BASE/authenticate" \
  --data-urlencode "CSRFtoken=$CSRF" \
  --data-urlencode "I=${F1_USER:-User}" \
  --data-urlencode "A=$A_HEX" > "$UI_DIR/auth-identify.http"

IDENT_HTTP="$(cat "$UI_DIR/auth-identify.http")"
if [[ "$IDENT_HTTP" == "503" ]]; then
  echo "503 on identify — stopped"
  exit 1
fi

PROOF="$(printf '%s' "$STATE" | F1_PASSWORD="${F1_PASSWORD:?}" python3 scripts/f1_srp_login.py proof "$UI_DIR/auth-identify.json")"
M_HEX="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['M'])" "$PROOF")"

pause
curl -s -c "$COOKIE" -b "$COOKIE" -o "$UI_DIR/auth-verify.json" -w "%{http_code}" \
  -X POST "$BASE/authenticate" \
  --data-urlencode "CSRFtoken=$CSRF" \
  --data-urlencode "M=$M_HEX" > "$UI_DIR/auth-verify.http"

VERIFY_HTTP="$(cat "$UI_DIR/auth-verify.http")"
if [[ "$VERIFY_HTTP" == "503" ]]; then
  echo "503 on verify — stopped"
  exit 1
fi

V_EXPECT="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['v'])" "$PROOF")"
V_GOT="$(python3 -c "import json; d=json.load(open('$UI_DIR/auth-verify.json')); print(d.get('M',''))")"
if ! python3 -c "import sys; exit(0 if sys.argv[1].upper()==sys.argv[2].upper() else 1)" "$V_GOT" "$V_EXPECT"; then
  echo "login failed HTTP $VERIFY_HTTP — stopped"
  exit 1
fi

echo "login ok"

for path in modals/logviewer-modal.lp overview.lp; do
  pause
  safe="${path//\//-}"
  curl -s -c "$COOKIE" -b "$COOKIE" -o "$UI_DIR/$safe.body" -w "%{http_code}" "$BASE/$path" > "$UI_DIR/$safe.http"
done

KEYWORDS='teliasmartrgw|rgw\.telia|\.rbi|lcm|7577|firmware'
grep -iE "$KEYWORDS" "$UI_DIR"/*.body 2>/dev/null | sed 's/[A-Za-z0-9]{20,}/[REDACTED]/g' > "$UI_DIR/keyword-snippets.txt" || true

python3 -c "
import json
paths=['modals-logviewer-modal.lp','overview.lp']
for p in paths:
    try:
        open(f'artifacts/ui/{p}.http').read().strip()
    except FileNotFoundError:
        pass
"

echo "done"
