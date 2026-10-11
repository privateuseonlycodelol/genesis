#!/usr/bin/env bash
# Mirror-port WAN capture during F1 reboot; summarize telia/rbi/SNI traffic.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts/captures artifacts/logs

IFACE="${1:-}"
if [[ -z "$IFACE" ]]; then
  echo "Usage: $0 <interface>"
  echo "Pick an interface from tshark -D, then re-run with that name or number."
  tshark -D
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PCAP="artifacts/captures/wan-mirror-${STAMP}.pcapng"
SUMMARY="artifacts/logs/wan-summary.txt"

cat <<'EOF'
Reminder:
  1. Mirror F1 WAN on the SG108E to this capture port.
  2. Reboot the router (or trigger an update check).
  3. Let tshark run ~2 minutes, then press Ctrl+C to stop.
EOF

FINISHED=0
summarize_and_report() {
  [[ "$FINISHED" -eq 1 ]] && return
  FINISHED=1
  if [[ -f "$PCAP" ]] && [[ -s "$PCAP" ]]; then
    tshark -r "$PCAP" -Y 'dns.qry.name contains telia || http.host contains telia || tls.handshake.extensions_server_name contains telia || http.request.uri contains rbi || frame contains ".rbi"' -T fields -E header=y -e frame.time -e ip.src -e ip.dst -e dns.qry.name -e tls.handshake.extensions_server_name -e http.host -e http.request.uri 2>/dev/null | sort -u >"$SUMMARY"
    echo "Wrote $SUMMARY"
  else
    echo "No capture data in $PCAP — skipping summary." >&2
  fi
  "$ROOT/scripts/report.sh"
}

trap summarize_and_report EXIT INT TERM

echo "Writing $PCAP (interface: $IFACE)"
tshark -i "$IFACE" -w "$PCAP"
