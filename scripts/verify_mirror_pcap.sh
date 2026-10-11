#!/usr/bin/env bash
# Analyze artifacts/captures/test.pcapng (mirror smoke test) and write findings.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PCAP="${1:-$ROOT/artifacts/captures/test.pcapng}"
OUT="$ROOT/findings/mirror-test.md"
F1_MAC="a0:b5:3c:c6:62:82"
F1_MAC_LC="$(printf '%s' "$F1_MAC" | tr '[:upper:]' '[:lower:]')"

if ! command -v tshark >/dev/null 2>&1; then
  echo "tshark not found — install Wireshark CLI." >&2
  exit 1
fi

if [[ ! -f "$PCAP" ]] || [[ ! -s "$PCAP" ]]; then
  echo "Missing or empty capture: $PCAP" >&2
  echo "On Windows, after mirror test: curl test.pcapng into ~/genesis/artifacts/captures/test.pcapng" >&2
  exit 1
fi

count_frames() {
  tshark -r "$PCAP" -q -z io,stat,0 2>/dev/null | awk -F'|' '/<>/ { gsub(/ /, "", $3); print $3; exit }'
}

frame_count="$(count_frames)"
if [[ -z "$frame_count" ]] || [[ "$frame_count" == "0" ]]; then
  frame_count="$(tshark -r "$PCAP" -T fields -e frame.number 2>/dev/null | tail -1)"
fi

t_first="$(tshark -r "$PCAP" -T fields -e frame.time_epoch -c 1 2>/dev/null | head -1)"
t_last="$(tshark -r "$PCAP" -T fields -e frame.time_epoch 2>/dev/null | tail -1)"
duration_s="0"
if [[ -n "$t_first" && -n "$t_last" ]]; then
  duration_s="$(awk -v a="$t_first" -v b="$t_last" 'BEGIN { printf "%.1f", b - a }')"
fi

tshark_count() {
  tshark -r "$PCAP" -Y "$1" -T fields -e frame.number 2>/dev/null | wc -l | tr -d ' '
}

f1_src="$(tshark_count "eth.src==$F1_MAC_LC")"
f1_dst="$(tshark_count "eth.dst==$F1_MAC_LC")"
f1_any=$((f1_src + f1_dst))

ip_total="$(tshark_count ip)"
lan_192="$(tshark_count 'ip && (ip.src==192.168.0.0/24 || ip.dst==192.168.0.0/24)')"
public_both="$(tshark_count 'ip && !(ip.src==10.0.0.0/8 || ip.dst==10.0.0.0/8 || ip.src==172.16.0.0/12 || ip.dst==172.16.0.0/12 || ip.src==192.168.0.0/16 || ip.dst==192.168.0.0/16 || ip.src==127.0.0.0/8 || ip.dst==127.0.0.0/8 || ip.src==169.254.0.0/16 || ip.dst==169.254.0.0/16)')"
dns_resp="$(tshark_count 'dns.flags.response==1')"
dns_to_1111="$(tshark_count 'dns && ip.dst==1.1.1.1')"
f1_ip="$(tshark_count "ip && (eth.src==$F1_MAC_LC || eth.dst==$F1_MAC_LC)")"
syn_ack="$(tshark_count 'tcp.flags.syn==1 && tcp.flags.ack==1')"

lan_pct="0"
if [[ "$ip_total" -gt 0 ]]; then
  lan_pct="$(awk -v l="$lan_192" -v t="$ip_total" 'BEGIN { printf "%.0f", 100 * l / t }')"
fi

verdict="MIRROR BROKEN"
reason="insufficient WAN signal"
if [[ "$frame_count" -lt 10 ]]; then
  reason="capture too short (${frame_count} frames)"
elif [[ "$f1_any" -eq 0 ]]; then
  reason="Telia F1 MAC $F1_MAC never seen on Ethernet"
elif [[ "$lan_pct" -ge 85 && "$public_both" -lt 20 && "$dns_resp" -eq 0 && "$syn_ack" -lt 5 ]]; then
  reason="mostly 192.168.0.x LAN/PC traffic (${lan_pct}% of IP), little public IP/DNS/TCP reply"
elif [[ "$f1_ip" -lt 10 && "$public_both" -lt 50 ]]; then
  reason="F1 MAC only DHCP/ARP-ish (${f1_ip} IP frames), not sustained WAN path"
elif [[ "$public_both" -ge 20 || "$dns_resp" -ge 5 || "$syn_ack" -ge 10 || "$f1_ip" -ge 50 ]]; then
  verdict="MIRROR OK"
  reason="public/non-LAN IP traffic (${public_both} frames), F1 MAC in ${f1_ip} IP frames, DNS responses ${dns_resp}, SYN-ACKs ${syn_ack}"
else
  reason="mixed signals — review counts below"
fi

rel_pcap="${PCAP#"$ROOT"/}"
pcap_name="$(basename "$PCAP")"

{
  echo "# Mirror test — \`$pcap_name\`"
  echo
  echo "**File:** \`$rel_pcap\`"
  echo "**Analyzed:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Capture"
  echo
  echo "| Metric | Value |"
  echo "| --- | --- |"
  echo "| Frames | $frame_count |"
  echo "| Duration (s) | $duration_s |"
  echo
  echo "## Telia F1 WAN MAC (\`$F1_MAC\`)"
  echo
  echo "| Role | Frames |"
  echo "| --- | ---: |"
  echo "| \`eth.src\` | $f1_src |"
  echo "| \`eth.dst\` | $f1_dst |"
  echo "| IP frames with F1 on L2 | $f1_ip |"
  echo
  echo "## LAN vs WAN"
  echo
  echo "| Metric | Count |"
  echo "| --- | ---: |"
  echo "| IPv4 frames | $ip_total |"
  echo "| Involving 192.168.0.0/24 | $lan_192 (${lan_pct}%) |"
  echo "| Non–RFC1918 (either end) | $public_both |"
  echo "| DNS to 1.1.1.1 | $dns_to_1111 |"
  echo "| DNS responses | $dns_resp |"
  echo "| TCP SYN-ACK | $syn_ack |"
  echo
  echo "## Verdict"
  echo
  echo "**$verdict** — $reason"
} >"$OUT"

echo "Wrote $OUT"
echo "$verdict — $reason"

"$ROOT/scripts/report.sh" >/dev/null

{
  echo
  echo "## Mirror test (\`$pcap_name\`)"
  echo
  echo "**$verdict** — $reason"
  echo
  echo "Frames: $frame_count, duration: ${duration_s}s. F1 MAC src/dst: $f1_src / $f1_dst. 192.168.0.x share: ${lan_pct}% of IP."
  echo
  echo "Full write-up: \`findings/mirror-test.md\`"
} >>"$ROOT/findings/latest.md"

echo "Updated findings/latest.md"
