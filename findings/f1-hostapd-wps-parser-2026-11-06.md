# hostapd WPS parsers, 23.1.b bank 1 — 2026-11-06

Offline read of the bank-1 `hostapd`. No packets were sent. The router was not logged into and was not changed.

## Binary

**VERIFIED:** `/tmp/f1-sq/bin/b1/usr/sbin/hostapd` is the same file as the previously recorded bank-1 binary. sha256 `875f3bad42fa1addf2d10bf4f466f2f520c4b5be8b9ab85e6c7e5c1b19adf00d`. ELF 32-bit ARM, EABI5, dynamically linked, stripped, 1377880 bytes. The copy under `/tmp/f1-sq/libc/usr/sbin/hostapd` has the same hash. The 19.x binary at `/tmp/f1-sq/bin/b19/usr/sbin/hostapd` is a different hash and was not used to name functions.

**DERIVED:** a C string `2.10` sits immediately before the format string `hostapd v%s`. That is the build's version text, not a string printed during this pass.

## What can send bytes before login

**VERIFIED (rootfs config, not the live box at the time):** `etc/config/wireless` sets `wps_state` on for the two main AP interfaces (`wl0`, `wl1`) and off for backhaul and guest. Nothing under the extracted bank-1 tree sets `upnp_iface` or `ctrl_interface`. **Superseded for the running process (2026-11-07):** the live configs set `ctrl_interface=/var/run/hostapd`. The directory is mode 750 and the sockets are mode 770, owner root. `sbin/wps_pbcd` talks to hostapd with `hostapd_cli` and binds a loopback socket. It is not a LAN listener. **Follow-up (2026-11-07):** `wps_pbcd` has 24 `system` call sites that run those `hostapd_cli` commands from MAP/DPP credential strings. Also 2026-11-07: the upstream advisories after 2.10 were checked against the live config — no RADIUS server is configured, SAE runs with hunting-and-pecking, and 2.10 predates MLO support, so advisories 2024-1, 2024-2, 2026-1, and 2026-5 do not apply. See [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md).

**VERIFIED (binary):** the WPS UPnP HTTP/SOAP service, its SSDP listener, the WPS attribute walker, the EAP-WSC fragment reassembly, the EAPOL-Key length check, and the 802.11 element walker are all compiled in. The control-interface strings are a filesystem directory (`mkdir`, `chmod`, `lchown`), which is the local socket, not a LAN port. `../src/wps/wps_upnp.c` is present. Port 49152 was already identified as this service; this pass did not re-probe it. See [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md).

Wi-Fi probe, association, and EAPOL WPS parsing run when `wps_state` is on. That is the pre-auth path this config actually turns on. The UPnP HTTP and SSDP parsers run only if `upnp_iface` is set at runtime. The static config does not set it.

## What was read

Hopper opened the binary (2755 procedures). It decompiled the PutWLANResponse handler and the subscription URL parser, then became unreachable. The rest was read with rizin. The binary was closed.

| Parser | What consumes attacker bytes | Result |
| --- | --- | --- |
| HTTP body reader (`httpread` logs) | TCP request headers and body, including chunked bodies | **Bounded.** Header accumulation stops at a fixed cap. Body growth is rejected against the configured maximum. Chunk size is rejected when it is larger than that maximum. Copies use the space left in the buffer. |
| XML item extract, then base64 | SOAP values such as `NewMessage` and `NewInMessage` | **Bounded.** The text between tags is copied into a zeroed allocation of that span. Base64 output is allocated from the count of valid characters and written inside that allocation. |
| PutWLANResponse | Those extracted values, then the WPS attribute walker | **Bounded.** Stack canary. No direct copy of its own. Invalid MAC text is rejected. |
| Subscription URL list | `SUBSCRIBE` callback list | **Bounded.** A callback longer than the fixed cap, or one that does not start with `http://`, is dropped. At most eight addresses are kept. Copies go into an allocation sized from the host and path that were just measured. |
| SSDP M-SEARCH | UDP discovery text | **Bounded.** `recvfrom` has an explicit maximum into a stack buffer, the terminator is written at the received length inside that buffer, and a stack canary follows it. |
| WPS attribute walker | WPS attributes inside SOAP, EAP-WSC, and WPS information elements | **Bounded.** A length past the bytes still in the message is rejected. Fixed-size attributes must match. Over-long device name and SSID are not stored. Vendor extension data past the fixed cap, or past a fixed count, is not stored. Nested vendor sub-elements are checked against the bytes left in that extension. The walker stores a pointer into the message. It does not copy. |
| EAP-WSC fragments | WPS over EAPOL | **Bounded.** The declared fragment length is rejected when it is past the frame or past a fixed ceiling. The copy is rejected when it would not fit the space left. A fragment-count cap drops the exchange. A failed buffer reserve aborts rather than returning into the copy. |
| EAPOL-Key | Key-data bytes in an EAPOL-Key frame | **Bounded.** The key-data length is compared with the bytes left after the fixed header, and the overflow path logs and returns. |
| 802.11 element walker | Probe and association information elements | **Bounded.** See the retry below for the fixed-field copies. |
| HTTP request dispatcher | Method, URL, headers, and body of a WPS UPnP request | **Bounded.** See the retry below. |

## Retry — the three gaps, same evening

Hopper was opened again and asked for the dispatcher. It died a second time during that decompile. The session switched to rizin and finished all three gaps there. No packets were sent.

**VERIFIED: the dispatcher does not copy past the HTTP reader's cap.** It loads the method, the URL, the header block, and the body as pointers into the object the reader already filled. The URL is compared with fixed names. Header lookup walks the already-capped header block and returns a pointer; it does not copy the value into a smaller buffer. POST checks the URL and the SOAP action against fixed text, then passes the body pointer to the NewMessage extractor and to PutWLANResponse. SUBSCRIBE and UNSUBSCRIBE compare header names at fixed lengths and call the subscription URL parser, which already drops an over-long callback. The one stack parse of a header value writes a fixed-size result and stops at that size. Copies that build the reply are either a constant string into a buffer reserved to that same length, or a measured string into a buffer grown to that measurement. A short numeric field is formatted with an explicit size. None of these copy request bytes past the reader's cap.

**VERIFIED: the DPP URI pointer is not copied into a fixed buffer.** The attribute walker still only stores a pointer and a length, and that length is already rejected when it runs past the message. The later function, the one named `wps_process_dpp_bootstrap_uri` in the binary, loads that pointer and that length. When the length is tiny, or a per-device flag is off, it logs and does not copy. When the flag is on it calls a callback pointer that was taken from the WPS config, passing the same pointer and length, then logs and moves on. The code after that call does not memcpy the URI into an array. No fixed-buffer overrun on this pointer.

**VERIFIED: the fixed-field element copies are bounded by the element length and the destination.**

- SSID. The walker drops the element when its length is past the SSID field, and logs that. A length that fits is stored as a pointer and a one-byte length. It is not copied past the field.
- Supported rates, including the extended-rates element. The walker stores a pointer and the element length. The later merge into the rate field copies only as many bytes as fit in that field. When the first rate list already fills the field, the extended list is not appended.
- Vendor IE and the WPS IE inside it. The walker checks the vendor header, then stores a pointer and the length for the WPS type. The probe path checks that header again against the element length before it reads those bytes. It does not memcpy the IE into a smaller fixed buffer.
- RSN. The walker stores a pointer and the length. It does not copy the element into a fixed RSN field. The later reader uses that stored length.

## Result

**VERIFIED:** no pre-auth memory-corruption bug showed up in the parsers above, including the three gaps closed on the retry. No unbounded copy, no length wrap that reaches a write, no bad allocation size, and no format string on attacker bytes.

**Not shown:** an exploit, a crash, or a live WPS message. **Superseded for the ovs-vsctl call (2026-11-07):** `sub_ab578` runs `execlp` of `ovs-vsctl` with the fixed argument `add-port` and the two names as separate arguments. It does not pass them through a shell. The live processes are this binary, started as `hostapd -B /tmp/wl0_hapd.conf` and `hostapd -B /tmp/wl1_hapd.conf`, and both listen on 49152. See [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md).
