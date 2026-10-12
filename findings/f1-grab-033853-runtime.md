# F1 UI grab — runtime and log review (2026-10-12T03:38:53Z)

**Scope:** Offline review of the saved UI-grab archive only. No gateway requests, button presses, exports, reboot/reset actions, or other live actions were performed. The raw grab and inventory remain under ignored `artifacts/`; this report omits serial/MAC values, SSIDs, addresses, and tokens.

## Input and row-count validation

**VERIFIED:** `artifacts/ui-grab-20261012T033853Z/files/modals__logviewer-modal.lp.html` is 55,275 bytes, SHA-256 `34d37fdf91086a1e1998f4b477e31557380cfdd42f2df53b59256e9c6047d836`, equal to the matching entry in `inventory.private.json`. The table is at source line 27. A stdlib `HTMLParser` and a separate regex-based row extractor both produced 132 timestamped four-column log rows and identical row dictionaries. There are also two non-log table rows: one three-cell UI row and one four-cell filter/form row. The parser helper checks the inventory byte count/hash and reports whether every log row received a message class.

Reproduce the sanitized aggregate from the repository root:

```sh
python3 artifacts/ui-grab-20261012T033853Z/log-review/analyze_logs.py
```

The table spans **Oct 12 05:17:14–05:27:01** by its Date column. The table’s source order is not chronological, so event ordering below is reconstructed from the Date values, not from row placement. The process column counts are:

| Process | Rows |
| --- | ---: |
| `nginx` (`nginx` 44 + PID-suffixed worker label 41) | 85 |
| `crond` | 10 |
| `kernel` | 10 |
| `mcsnooper` | 10 |
| `restricted_shell` | 10 |
| `dnsmasq-dhcp` | 2 |
| `netifd` | 2 |
| `wansensing` | 2 |
| `transformer` | 1 |
| **Total** | **132** |

The facility totals are `daemon.err` 81, `daemon.warn` 14, `cron.info` 10, `kern.err` 10, `daemon.notice` 4, `daemon.info` 3, and `user.notice` 10.

The independently classified message rows account for all 132 log rows:

| Message family | Rows |
| --- | ---: |
| Unauthorized session-status GET | 65 |
| Root `obuspa_retriever.sh` cron command | 10 |
| `restricted_shell` root crontab launcher | 10 |
| Kernel WAN statistics error | 10 |
| `mcsnooper` ignored MLD packet | 10 |
| POST without CSRF token | 6 |
| Missing `asmcrypto.js.map` | 4 |
| New default session | 3 |
| Unauthorized system-configuration POST | 2 |
| `wansensing` debug-interface check | 2 |
| WAN DHCP request / acknowledgement | 2 |
| Missing `/js/login.lp` | 2 |
| Missing `/js/password.lp` | 2 |
| `netifd` WAN state change | 2 |
| Session user-change record | 1 |
| Transformer `ipping_helper` launch | 1 |

## Session and CSRF records

**VERIFIED:** The log text contains 65 `nginx` error rows for `GET /gateway.lp?auto_update=true&getSessionStatus=true`, all naming `sessionmgr.lua:264` and `redirectIfNotAuthorized()`. They cover 33 timestamps: 32 timestamps have two rows each and one has a single row. Most adjacent timestamp groups are 20–21 seconds apart. The saved `js__gateway.js:20-22` sets this polling interval to 20,000 ms. The doubled log rows are compatible with two pollers, duplicate requests, or another logging/session artifact; these rows do not identify which explanation applies, and they do not show a bypass. `auto_update=true` is part of this session-status request and is not an observed firmware-update request.

The same table records six `session.lua:223` messages saying a POST lacked a CSRF token, all for `/modals/system-config-modal.lp`, followed by two `sessionmgr.lua:264` unauthorized POST messages for that path. It also records three `session.lua:354` default-session creations and one `session.lua:103` `changeUser()` event. These are log messages about server-side checks and state transitions. The table contains no HTTP response status/body, request action field, or proof of handler side effects, so it does not establish which client produced the requests, whether the UI or a stale/background request caused them, or whether configuration changed. The `.lua` stack names and line numbers are quoted by nginx; their source code is not part of this archive.

Other nginx misses are four requests for `/js/asmcrypto.js.map`, two for `/js/login.lp`, and two for `/js/password.lp`; the saved error strings identify missing files under `/www/docroot/`. These are path/error observations, not evidence that a source map or executable endpoint was exposed.

## Runtime, WAN, and diagnostics correlation

**VERIFIED:** The saved System Information HTML identifies Vantiva / Telia F1, software `23.1.b`, firmware `23.1.b.0448-7241017-20260223134332`, and hardware `GCNT-X`. It renders uptime `8 hours 10 minutes 23 seconds`, memory `77%`, CPU `5%`, and reboot cause `Power` (`modals__system-info-modal.lp.html:22,25-28`). These agree with the project’s stated target. The page embeds the firmware and hardware values in its advanced/hidden section; this is page data, not a firmware image or boot log.

The Internet modal renders DHCP as connected, with a lease obtained at `05:17:30` and expiring at `05:47:30` (`modals__internet-modal.lp.html:28`). The log contains a WAN transition to renewing at `05:17:28` and to bound at `05:17:29` (`modals__logviewer-modal.lp.html:27`), which closely agrees with the rendered lease time. The dashboard reports Ethernet connected, DHCP on, and IPv6 connected (`gateway.lp.html:84,115,144,147`). The connection diagnostics page renders WAN operational state `Up` and configuration available `True`; its next-hop result says not all pings were answered or the connection was unavailable, while the DNS/IPv6 checks are still marked `Ongoing` (`modals__diagnostics-connection-modal.lp.html:25`). These are saved UI states; this review did not run those tests.

The Network Statistics page renders ports 1–2 disconnected, ports 3–4 connected at 100 Mbps, port 5 connected at 1 Gbps, and both Wi-Fi radios connected; all displayed error counters are zero (`modals__diagnostics-network-modal.lp.html:23-26`). The Ping page contains a saved three-success, zero-failure result with 9 ms minimum, maximum, and average (`modals__diagnostics-ping-modal.lp.html:30`), and its button sends `action=PING` (`:25`). At `05:26:57`, one `transformer` row says `async run: /usr/bin/ipping_helper` (`modals__logviewer-modal.lp.html:27`). **HYPOTHESIS:** that helper run may correspond to the saved ping result because the action, helper name, and timing are compatible. The log has no arguments, initiating request, or result, and the HTML does not timestamp the ping snapshot, so causation is unverified. A single controlled ping with a before/after log read would discriminate this.

**HYPOTHESIS only — approximate boot-time alignment:** the adjacent Configuration page has `system_time = 2026-10-12 05:27:19` (`modals__system-config-modal.lp.html:34`). If the System Information uptime was sampled close to that time, subtracting the displayed uptime implies a start near Oct 11 21:16:56. The existing older log table covers Oct 11 21:22:24–21:30:26 and contains repeated Ethernet link transitions plus DHCP/WLAN activity (`artifacts/ui/logviewer-modal.lp.html:27`). This is temporally compatible with post-start network settling, but the capture times are not tied to the uptime sample and those logs contain no bootloader, partition, flash, or explicit reboot record. The page’s `Power` reboot-cause value does not establish why power was interrupted or provide a serial boot observation.

## Scheduled process and update/provisioning leads

**VERIFIED:** This 132-row window contains ten `crond` entries, one per minute from 05:18 through 05:27, naming root and `/usr/share/transformer/scripts/obuspa_retriever.sh`; it also contains ten matching `restricted_shell` messages saying root is connecting through Crontab. This supports a recurring root-scheduled launcher in this slice. It does not show the script contents, its exit status, a usable shell for the researcher, USP/CWMP traffic, or any key access. The only other explicit executable path is `/usr/bin/ipping_helper`, in the single transformer message above. No executable or firmware binary was retrieved.

A bounded search of surviving HTML and log rows found no concrete `.rbi`/RGW image host, firmware-download event, ACS URL, CWMP/TR-069 exchange, USP exchange, OSCK/OSIK value, `eripv2`, bootloader, partition, flash, MTD, or UBI evidence. `OBUSPA` occurs in the cron command path. In `js__main-min.js:331`, the saved code has field-name filters for `cwmpAcsPass` and `connectionrequestPass`; those names show that the UI code filters such form fields, but they are not credential values or proof of a management exchange. The separate software pass reports a WFA service description on TCP 49152; live work outside this archive now includes [session/WPS](auth-session-and-wps-2026-10-12.md) (`GetDeviceInfo`/M1) and [bounded 49152 probes](f1-wfa-wlanconfig-49152-2026-10-12.md) (SOAP, events, peer/NACK behavior). The WFA interface is distinct from OBUSPA. **No provisioning action was invoked during this UI-archive review.** The saved `js__main-min.js` and `js__system-config-min.js` are among the redaction-damaged scripts described in the [collection-integrity review](f1-grab-033853-integrity.md#six-javascript-bodies-were-damaged-by-collection-redaction). The field-filter snippet survives identically in the earlier intact local copy, but other surrounding code in the ZIP script is damaged, so do not infer complete client behavior or absence of endpoints from it. The log’s `auto_update=true` is the session poll described above. The System Configuration HTML has upgrade/LAN-upgrade strings, and the saved JavaScript bytes contain selectors for `#file-upgradefw` and `#btn-system-bootp`, but the captured HTML renders only Restart, Factory Defaults, and Semi-Reset controls (`modals__system-config-modal.lp.html:25,36-39`; `js__system-config-min.js:2,16-17`). This does not establish a reachable upload/BOOTP handler. CSRF-token names appear in UI script and page markup, with values redacted; the missing-token log messages show checks were logged, not the POST result.

## Coverage checklist

| Area | Result from this archive | Limit |
| --- | --- | --- |
| Build and board | **VERIFIED:** software `23.1.b`, firmware build label, hardware `GCNT-X` | No firmware image or binary |
| Boot/runtime | **VERIFIED:** UI reports uptime, reboot cause, memory, and CPU; **HYPOTHESIS:** approximate time aligns with older network startup logs | No UART, bootloader, partition, or root-shell evidence |
| Authentication boundary | **VERIFIED:** repeated `redirectIfNotAuthorized()` logs and missing-CSRF messages on the system-config path | No request status/body, actor attribution, or effect evidence |
| Scheduled execution | **VERIFIED:** recurring root cron wrapper path and paired crontab-launcher messages | No script source, exit status, network traffic, shell, or key access |
| Network state | **VERIFIED:** rendered DHCP lease and port/link counters; DHCP renew/bound log aligns to lease | Addresses and client identifiers omitted; saved states may be sampled at different times |
| Diagnostics | **VERIFIED:** saved ping results and connection-state fields; one nearby helper launch | **HYPOTHESIS:** relationship to that ping; no action performed in this review |
| Update/provisioning | No concrete image host, `.rbi`, ACS URL, update event, or management-protocol exchange | Generic damaged-script field/selector strings only; WFA on 49152 exercised in separate live passes ([f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md)) |
| Cryptographic material | No OSCK/OSIK or device key value | No device firmware/config key recovered |

## Comparison and limitations

The next local Downloads snapshot (`f1-grab_modals_logviewer-modal.lp (1).html`) independently parses to 138 timestamped log rows for 05:04:36–05:17:29; it overlaps this archive’s beginning by 15 seconds. The earlier manifest’s log file parses to 156 timestamped log rows for 04:58:10–05:08:17, plus one three-cell UI row. Thus the prior finding’s “157 rows” is the total including that UI row, not 157 log entries; its stated upper bound also differs from the last row actually present. The older Oct 11 file contains 283 timestamped log rows. The overlapping snapshots are different rolling log windows, not duplicate complete captures.

The UI-grab index records 63 hit rows, 80 misses, and 152 queued entries (`artifacts/ui-grab-20261012T033853Z/INDEX.md:3-5`); one hit is a zero-byte AJAX response. The [collection-integrity review](f1-grab-033853-integrity.md#crawl-coverage-and-misleading-negatives) found 86 queue entries already represented in results and only 66 paths without a recorded result; 65 are heuristic JavaScript-name guesses and one is a duplicated-directory artifact. Thus queue size is not the count of meaningful, unseen routes. This report describes the saved pages and their log snapshot, not the full UI or firmware. It adds runtime/session/CSRF and DHCP timing evidence, but no root shell, boot chain, update event/image, provisioning exchange, key material, exploit, or 23.1.b image.

**Highest-value follow-up:** on the authorized device, one deliberate diagnostics Ping action with contemporaneous before/after log and request/response capture would test the `ipping_helper` correlation and establish the POST result. Until then, keep the CSRF entries as logged checks without attributing them or claiming a blocked/successful configuration change.
