# Mirror test — `wan2-real.pcapng`

**File:** `artifacts/captures/wan2-real.pcapng`
**Analyzed:** 2026-10-11T15:46:08Z

## Capture

| Metric | Value |
| --- | --- |
| Frames | 8729 |
| Duration (s) | 303,1 |

## Telia F1 WAN MAC (`a0:b5:3c:c6:62:82`)

| Role | Frames |
| --- | ---: |
| `eth.src` | 12 |
| `eth.dst` | 0 |
| IP frames with F1 on L2 | 6 |

## LAN vs WAN

| Metric | Count |
| --- | ---: |
| IPv4 frames | 189 |
| Involving 192.168.0.0/24 | 183 (97%) |
| Non–RFC1918 (either end) | 6 |
| DNS to 1.1.1.1 | 0 |
| DNS responses | 0 |
| TCP SYN-ACK | 0 |

## Verdict

**MIRROR BROKEN** — mostly 192.168.0.x LAN/PC traffic (97% of IP), little public IP/DNS/TCP reply
