# Capture instrumentation and management-source review

**Reviewed:** 2026-10-12 (offline; no router, switch, or network interface touched)

## Evidence status and files inspected

I read `README.md`, `AGENTS.md`, `findings/mirror-test.md`, `findings/wan2-tagged-frames.md`, `findings/want-pcap.md`, `scripts/wan-capture.sh`, and `scripts/verify_mirror_pcap.sh`.

**VERIFIED in the current workspace:** Wireshark CLI `tshark`/`capinfos` 4.6.9 and Python 3.14.7 are installed. Current capture hashes and metadata are:

| File | SHA-256 | Current inspection |
| --- | --- | --- |
| `artifacts/captures/want.pcapng` | `24bc5df77a81dc7bd25926e817e4e6e8a6c3f308ee598bccc8cddccdd55ec646` | Valid pcapng, one Ethernet interface, 49,846 packets, 266.703 s. |
| `artifacts/captures/wan2-real.pcapng` | `ecd14d04048cea2a3a853e829e6f0095a91ad20f8cd837da2f467584af516ba9` | Valid pcapng, one Ethernet interface, 8,729 packets, 303.126 s. Hash matches the one recorded in `wan2-tagged-frames.md`. |
| `artifacts/captures/f1-reboot.pcapng` | `b90ca7aebc19c0c0f40ba9e4233a4bf90e2cf4f492fec5b4f3873cd2f5a6f362` | Valid pcapng, but its interface is `en0` described as Wi-Fi and its recorded capture filter is `udp port 53`; it has 8 DNS packets over 0.136 s. The filename does not make it a WAN capture. |
| `artifacts/captures/wan.pcapng` | `860b53ed6ea6a0cf602fae632cfcd28dbcf637f85a8bee28d2ee9c6cc9081669` | 335-byte HTML error response, not a pcapng capture. |
| `artifacts/captures/wan2.pcapng` | `f2456c0f55eaf16ce69177567d37f65225811e006fed9695a2d5b9e09bdbd0f0` | 9,635,526-byte UTF-16LE text export, not a pcapng capture. |

The two larger valid captures declare Ethernet link type. `capinfos` reports a capture length of zero in their interface metadata, so those IDB records do not state a nonzero snap-length limit. That field alone does not establish truncation; packet captured/original lengths should be checked for the specific frames used as evidence.

## Fresh byte-level result: `wan2-real.pcapng` is mixed-link content

**VERIFIED:** I independently walked the pcapng Section Header, Interface Description, and Enhanced Packet blocks with a short, non-persistent Python standard-library parser. The file has one interface with link type 1 (Ethernet) and 8,729 packet blocks. At byte offset zero, 4,982 packets have IPv4 version nibbles and 1,788 have IPv6 version nibbles. All 4,982 IPv4 headers pass the one's-complement header checksum and have total length equal to captured packet length; all 1,788 IPv6 packets have `40 + payload length` equal to captured packet length.

At Ethernet header offset 12, the same file has 4,946 apparent types `0x6466`, 36 `0x6464`, 1,788 `0xa1e0`, 1,764 `0x8899`, 189 `0x0800`, and 6 `0x0806` (sum: 8,729). The raw IP bytes at offset zero overlap the putative Ethernet header. This reproduces the core mis-encapsulation observation in `wan2-tagged-frames.md`: the pcapng says Ethernet while many packet records are internally valid raw IP packets. Current `tshark -q -z io,phs` likewise classifies 6,770 frames as `eth:data`, not dissected IP, alongside 189 IPv4, 6 ARP, and 1,764 Realtek frames. Do not read absent `ip.*` fields, apparent MACs, or apparent ethertypes from those 6,770 as ordinary Ethernet/WAN evidence.

The byte checks establish framing and IP-header validity, not which machine originated every raw-IP record. The recorded `wan2-tagged-frames.md` attribution of those packets to a Windows/Tailscale host is a prior analysis; it is not inferred from this byte check alone.

**Fresh result for `want.pcapng`:** the same parser finds 6,112 IPv4 records with a valid header checksum and exact length, plus 2,334 IPv6 records with exact length, starting at byte zero under its declared Ethernet link type. The sum, 8,446, matches the file's previously reported count of apparent non-IP `0x6466`/`0x6464`/`0xa1e0` frames. This capture also has mixed Ethernet/raw-IP framing and must be rejected as a positive mirror validation input until its encapsulation is resolved. The other 39,480 IPv4, ARP, and Realtek Ethernet records remain separately classifiable.

## False-positive found in the prior mirror verifier

**VERIFIED by a read-only reproduction of the original display filters and boolean thresholds:** before this pass's edits, `want.pcapng` would reach `MIRROR OK` in `verify_mirror_pcap.sh` even though `findings/want-pcap.md` records it as ASUS-host LAN traffic plus switch traffic, with the F1 present only in DHCP and ARP. The current script has been changed so this aggregate path cannot return that verdict.

The reproduction extracted the F1 link-layer address in memory from the capture's DHCP hostname and did not print or save it. The verifier predicates produced:

| Verifier metric | Read-only value |
| --- | ---: |
| Frames / IPv4 | 49,846 / 39,480 |
| Frames involving `192.168.0.0/24` | 39,448 (rounds to 100% of IPv4) |
| “Non-RFC1918” IPv4 frames | 24 |
| DNS responses / TCP SYN-ACK | 0 / 0 |
| F1-associated IPv4 frames / verifier's L2 `src + dst` sum | 24 / 28 |

All 24 frames that the script labels “Non-RFC1918” are DHCP frames sent from the detected F1 MAC; all 24 have source `0.0.0.0` and destination `255.255.255.255`. There are zero non-DHCP frames in that bucket. Those unspecified and limited-broadcast addresses are not public Internet endpoints, but the script's exclusion list does not remove them. Since the LAN-share rejection requires `public_both < 20`, these 24 DHCP broadcasts bypass that rejection; the final condition at lines 77–79 then accepts `public_both >= 20`. The reported `MIRROR OK` signal would therefore be produced by DHCP discovery alone.

I did not invoke `verify_mirror_pcap.sh`: it overwrites `findings/mirror-test.md` and appends to generated `findings/latest.md`. The result above is a read-only reproduction of its filters and decision tree against the ignored capture artifact.

The old classification failed because:

- `public_both` was “not in this short list of IPv4 ranges,” not “public.” It missed unspecified/broadcast, shared CGNAT (`100.64.0.0/10`), multicast, documentation, benchmarking, and other special-use ranges; it ignored IPv6.
- `dns_resp` and `syn_ack` counted any matching frame anywhere in the capture, without correlating it to a request or the F1 MAC. Unrelated host traffic could satisfy those thresholds.
- `f1_ip` counted every IPv4 frame with the F1 MAC at L2, including DHCP broadcasts. Enough boot-time DHCP packets alone could satisfy its `>=50` acceptance branch.
- `f1_any` added source and destination counts, so a frame containing the same MAC on both sides counted twice. MAC validation checked length but not that all characters were hexadecimal.
- The `192.168.0.0/24` share is a local-network hint, not a general mirror test. A correct WAN capture can carry private/shared addressing, and a bad mirror can carry unrelated non-private-looking traffic.

**VERIFIED read-only after the edit:** the replacement aggregate filters on `want.pcapng` produce zero frames outside the selected excluded IPv4 ranges, zero DNS responses, zero SYN-ACKs, and zero F1-associated non-DHCP IPv4 frames. Under the new decision tree this would be `UNVALIDATED`; I did not invoke the report-writing script.

`wan-capture.sh` only starts an unfiltered live `tshark -i` capture. It cannot establish from its interface argument that the selected interface receives the configured mirror, that both directions are mirrored, or that link-layer encapsulation is decoded correctly. Its exit summary searches for selected text fields (`telia`, `.rbi`, HTTP host/URI, TLS SNI) and de-duplicates matching rows; an empty summary means only that those selected visible strings were not found. It does not prove no update flow occurred, especially when TLS hides application data, SNI is unavailable, the protocol differs, or packets were mis-encapsulated. The script prints reboot/update-check instructions but was not run for this audit.

## Offline preflight added

`scripts/capture_preflight.py` now provides a read-only positive-control check. It reads pcapng interface metadata and packet blocks, refuses mixed raw-IP/Ethernet framing, and requires a caller-designated IPv4/TCP tuple plus target WAN MAC. A positive capture must contain the target-MAC outbound SYN, matching reverse SYN/ACK, a non-RST final ACK, contiguous outbound payload after the handshake, and reverse payload whose sequence begins after the SYN/ACK and whose ACK matches a captured outbound payload end (including 32-bit sequence wrap). It does not accept aggregate public-looking IP, DHCP, DNS response, or SYN-ACK counts. It reports `UNVALIDATED` when those flow details are missing or do not match.

Run it with the tuple as it appears at the capture point (after NAT if the tap is on the WAN side), for example: `python3 scripts/capture_preflight.py <capture.pcapng> --wan-mac <router-wan-mac> --client-ip <observed-client-ip> --client-port <observed-client-port> --server-ip <test-server-ip> --server-port 443`.

The capture check currently supports Ethernet, optional VLAN tags, and a bounded simple IPv4/TCP flow in Enhanced Packet Blocks. It follows contiguous captured client data sequence ranges but does not perform general TCP stream reassembly, normalize retransmissions, or validate arbitrary out-of-order traffic. It reports section/interface IDs, link type, snap length, frame counts, truncation count, and raw-IP signatures; it does not parse interface-description/filter options or validate IPv6 flows, UDP, CoAP, or MQTT sessions. A positive result validates only the supplied tuple and MAC within the file; the operator must establish those identities and the physical mirror configuration separately.

`verify_mirror_pcap.sh` now reports only `WAN SIGNAL ONLY` or `UNVALIDATED`. Its old “public” field is narrowed to an explicitly heuristic IPv4 count outside selected special ranges and excludes DHCP; its F1 IPv4 count also excludes DHCP. Aggregate DNS, SYN-ACK, or candidate-global counts can prompt review but cannot validate a mirror. It no longer emits `MIRROR OK` or `MIRROR BROKEN`.

**VERIFIED local controls:** `python3 scripts/capture_preflight.py --self-test` passed. It accepted a synthetic five-frame HTTP request/response, including client sequence wrap at 2^32, rejected a one-way SYN, wrong L2 MAC, unrelated tuple, response with an incorrect ACK, response with an incorrect sequence, and an RST|ACK substituted for the final handshake ACK. It returned `UNVALIDATED` for both existing captures due their mixed framing. Installed `tshark` 4.6.9 independently decoded the synthetic fixture as five frames and recognized its HTTP GET and 200 response. The printed synthetic `VALIDATED` result is a parser control only, not physical mirror evidence. `bash -n scripts/verify_mirror_pcap.sh` and Python bytecode compilation also completed without errors. I did not run the legacy verifier because it rewrites `findings/mirror-test.md` and appends to `findings/latest.md`.

## Capture acceptance criteria for future authorized collection

Classify a capture as a usable WAN mirror only after all of these checks pass:

1. **File and interface integrity:** `capinfos` and a packet parser agree on the number of interfaces, link type per interface, time span, captured length, and original length. Retain interface descriptions, capture filters, and tool versions. Reject text/error files regardless of suffix. Decode each link type according to its actual interface metadata, not by guessing a tag length from an ethertype-looking payload.
2. **Mirror-path positive control:** identify the F1 WAN-side L2 address or the expected access encapsulation in both directions during a deliberately generated, recognizable transaction. Record the switch mirror source/destination configuration as separate setup evidence. A switch's own frames, a router DHCP Discover, an ARP probe, or traffic from an unrelated client do not meet this check.
3. **Bidirectional flow correlation:** require a request and its matching response from the same flow, not global counts. Examples are a DNS question and answer matching transaction ID and question, a TCP SYN followed by the reverse-flow SYN-ACK, or a known UDP request and response matched by protocol identifier and endpoint tuple. Confirm both directions are visible at L2 when the chosen mirror topology should expose them.
4. **Target attribution:** for firmware-management claims, correlate the flow with a documented F1-originated event and timestamp, and distinguish the F1's own management flow from NATed client traffic. A client browsing through the router can prove the mirror path, but cannot prove that the router contacted its ACS or fetched firmware.
5. **Protocol-safe negative claims:** record visible DNS, HTTP, TLS, MQTT/USP, and other relevant handshakes with their limits. “No SNI,” “no `.rbi` string,” or “no HTTP” is a statement about visible decoded bytes, not proof that no management session or encrypted transfer occurred.

One known transaction with a fully correlated reply is a higher-quality positive control than aggregate thresholds such as “20 public-looking frames.” If it is absent, preserve the capture but classify mirror validity as **UNKNOWN/BLOCKED**, not OK. Repeat only after changing a specific instrumentation uncertainty, such as selecting a different tap/interface or correcting encapsulation.

## Local and public management-source opportunities

**VERIFIED as local reference material, not target implementation source:** the checked-in `tools/hack-technicolor` tree contains community documentation naming Homeware CWMP components and paths:

- `docs/Hardening.md` names `cwmpd`, `cwmpdboot`, the `cwmpd.cwmpd_config` object, and example ACS/interface/HTTPS settings. Treat these as search terms and a model for other Homeware versions, not as evidence that the Telia F1 has these exact values or services enabled.
- `docs/Repository.md` describes `cwmpd.db` and a `tidkv` row with key `URL` as a way to recover past firmware URLs from a rooted device's banks. This is a concrete offline lead if a lawful, exact-version filesystem/config dump becomes available; it does not establish an ACS URL for this unit.
- `docs/Resources.md` names `/rom/usr/lib/cwmpd/transfers/switchover.sh` and documents that Homeware RBI upgrades may be transferred by Web UI, CWMP, SSH/SCP, or USB. These are generic platform notes, not verified GCNT-X 23.1.b behavior.
- `findings/f1-logviewer.md` records a router log line naming `/usr/share/transformer/scripts/obuspa_retriever.sh`. This makes `obuspa`, `transformer`, and the retriever script useful exact search strings for any future matching firmware image or authorized filesystem collection. **It does not prove** the script ran successfully, that a USP Agent is enabled, or what controller/URL it contacts.

The project notes identify Vantiva's public EWA1330TCS 19.4 COSP PDF as a GPL component report, not a source archive or firmware image. It is a module-name lead for an older generation, not a 23.1.b binary source. No local `cwmpd` or `obuspa_retriever.sh` implementation was found in the searched documentation/scripts.

The official Broadband Forum references are useful for decoding expectations, not for attributing behavior to this device:

- [TR-069 Amendment 6](https://www.broadband-forum.org/pdfs/tr-069-1-6-0.pdf) says a CWMP session starts with a CPE `Inform` in an HTTP POST, describes the CPE as HTTP client for ACS sessions, and allows firmware-file transfer on the established connection or a separate connection. Therefore, a transfer can use a host different from the ACS, and a short boot capture may see the session without the file or vice versa. The BBF [TR-069 technical-library entry](https://www.broadband-forum.org/technical-library/?number=TR-069) identifies Amendment 6 Corrigendum 1 as the in-force version.
- [TR-369 Amendment 5](https://www.broadband-forum.org/pdfs/tr-369-1-5-0.pdf) defines USP message transfer protocols; its MQTT binding describes sessions expected to be long-lived and reused. If USP is active, an MQTT/TLS flow may be more relevant than searching only for HTTP or a `.rbi` string. The F1 log line is not proof that this path is active.
- [TR-181 Device:2](https://device-data-model.broadband-forum.org/index.htm) provides the model for network-interface and protocol-stack management objects used by CWMP endpoints and USP agents. Its page reflects a 2026 revision; use the model version actually implemented by the firmware when interpreting parameter names.

## Result and highest-value next step

**What changed:** the previous capture-mirror conclusion for `want.pcapng` remains supported by its packet contents, but the original verifier could contradict it because DHCP broadcasts counted as public IPv4. Both `want.pcapng` and `wan2-real.pcapng` are now independently confirmed to contain raw-IP records under Ethernet metadata, and the new preflight refuses both. The valid capture artifacts reviewed do not establish a firmware download or a specific 23.1.b management endpoint.

**Next:** when an authorized controlled capture is available, generate one known bidirectional TCP transaction through the intended WAN mirror and run `scripts/capture_preflight.py` with the observed tuple and router WAN MAC. That resolves whether the selected capture interface receives the expected two-way traffic with usable Ethernet framing; it still will not attribute later management traffic to the router. Use a separate F1-originated event and timestamp to make that attribution.
