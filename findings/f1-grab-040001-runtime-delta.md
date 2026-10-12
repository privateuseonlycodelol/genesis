# F1 04:00:01 grab — verified runtime delta

2026-10-12. Offline comparison against the 03:38 package. A Luna subagent prepared the two-parser helper and intermediate results; it stopped at its usage limit before completing the finding. The parent reran the helper, independently parsed the log and QR links, corrected two mistaken interpretations, and completed this report. No device requests or page scripts were executed.

## Evidence and reproduction

Private inputs are `artifacts/ui-grab-20261012T033853Z/files/` and `artifacts/ui-grab-20261012T040001Z/files/`. The new log body is 55,904 bytes; its SHA-256 and length are checked against `audit.private.json` by the helper. The new archive SHA-256 is `4a341890d9cbddd55491ff2a127cb78995cb8ecc8569afbf95f1280919e9a675`.

```sh
python3 artifacts/ui-grab-20261012T040001Z/runtime-review/analyze_runtime_delta.py \
  > artifacts/ui-grab-20261012T040001Z/runtime-review/parent-verified.private.json
python3 artifacts/ui-grab-20261012T040001Z/runtime-review/qr_link_keys.py
```

The first helper compares HTMLParser and a separate regex extraction of all four-column timestamped records; both agree exactly for each archive. It emits aggregate counts, field names and schema comparisons, not message bodies or collected field values. A separate parent HTMLParser independently confirmed the 135 new records. The second helper parses actual `data-remote` attributes and emits only route names and query keys. Final parent rerun: Python 3.9.6; output saved as `runtime-review/parent-final.private.json`.

## What changed in the log

| Measurement | 03:38 package | 04:00 package |
| --- | ---: | ---: |
| Timestamped rows | 132 | 135 |
| First device-log timestamp | 05:17:14 | 05:48:55 |
| Last device-log timestamp | 05:27:01 | 05:58:47 |
| Unauthorized session-status messages | 65 | 60 |
| Missing-CSRF configuration POST messages | 6 | 0 |
| Root OBUSPA cron commands | 10 | 10 |
| Root crontab-launcher messages | 10 | 10 |
| Transformer `ipping_helper` launches | 1 | 1 |

**VERIFIED:** the windows do not overlap. The new nginx count is 89: 60 unauthorized session-status messages, 13 missing-JavaScript `open()` errors, and 16 QR traceback/context rows. Other process counts are crond 10, restricted_shell 10, mcsnooper 18, kernel 5, wansensing 2, transformer 1; total 135. The 60 session-status rows occupy 30 timestamps with two records each. These counts do not identify two distinct clients or establish a bypass. No missing-CSRF message in a later window is not evidence that the check was removed.

The 13 missing-JS records reference seven name variants: three `basicview-wifiguest5GHz` variants, two `basicview-wifipsk5GHz` variants, and two `internet-dhcp-routed` variants. They are missing-file observations, not failed underlying modal routes or recovered server code. The scheduled OBUSPA/root launcher observation adds another window of the previously recorded behavior; no script body, USP exchange, shell access, or key material follows from it.

## QR exception: concrete implementation evidence, limited attribution

**VERIFIED in saved log text:** two clusters at 05:49:09 and 05:57:30 each contain eight distinct nginx rows under one connection reference. These include request context and multi-line trace continuations; they are two failing request contexts, not sixteen independent crashes. The recorded error is `attempt to index local 'password' (a nil value)` at `/www/lua/wireless_qr.lua:48`. Frames name function `format`, the QR template's `content`, `/usr/lib/lua/web/web.lua:249` function `process`, and `content_by_lua(nginx.conf:123):4`. The source files themselves were not obtained.

The new MISSES entry records the bare QR GET as HTTP 500, 572 bytes, at `2026-10-12T03:59:09.957Z`. At Stockholm UTC+2 that is approximately 05:59:09, after the saved log ends at 05:58:47. Consequently neither earlier error cluster can be assigned as this specific GET's traceback. A draft attempted a 1-hour-50-minute offset; that was an arithmetic error and was rejected, rather than used to invent a matching event.

**VERIFIED caller distinction:** the two QR links in each archive's AP modal are `div[data-remote]` attributes with query keys `band6gOnly`, `broadcastiface`, `iface`, `isCompatibility`, `ispremium`, and `splitState`. The failed seeded probe is the bare path. A draft's regex extraction stopped at `.lp` and wrongly called the UI links bare; the parent corrected this with HTMLParser and URL parsing. Query values are deliberately omitted. This is a concrete collection-context difference; the archive alone cannot establish which parameter is necessary or prove the exception's cause.

**Subsequent result, separate evidence:** the later [authenticated contextual QR control](f1-wireless-qrcode-context-2026-10-12.md) records bare GET 500, contextual GET 200, and `iface=cred0` alone 200. This resolves route usability and supports the missing-interface-context explanation for bare requests. It does not retroactively associate this archive's miss with an earlier log cluster, or supply the missing Lua implementation. The same later report records no demonstrated XSS/RCE in its tested parameter cases. Do not repeat the basic contextual-versus-bare experiment as though it remained untested.

## Eight changed HTML snapshots

**VERIFIED:** device, diagnostics-network, diagnostics-ping, Internet, logviewer, system-config, system-info, and time-management bodies differ. All eight preserve field names, field schemas, and form actions. No added/removed named field was found. Only the ping form has changed collected value attributes: `NumberOfRepetitions`, `ipAddress`, `ipAddressTrace`. Their values are not reproduced. Other differences include rolling logs, display counters/time/status and markup around results; byte changes alone do not establish a new firmware build or server capability.

The new log contains a helper launch at 05:58:29. The new ping form's retained values are compatible with categories used by earlier loopback controls, but the page does not timestamp their assignment or identify the requester. This archive therefore adds a helper-path observation, not a new controlled action-to-process proof. Later [PING controls](f1-ipping-helper-2026-10-12.md) and [TRACE helper controls](f1-trace-helper-2026-10-12.md) already address those relationships with separate experiments.

A bounded message search found no concrete firmware-download event, RBI URL, ACS/CWMP provisioning exchange, or recovered key. Generic UI fields and the OBUSPA cron path are not such exchanges. This archive does not supply a current firmware image, decrypted configuration, interactive root shell, or exploit.

## Assessment

The newer log genuinely improves the historical evidence: it names the QR Lua failure and gives a later operational window. The repaired JavaScript and unchanged form schemas do not justify repeating the entire frontend audit. The useful continuation is to use this archive as the clean script reference, retain older extra pages separately, and keep the QR finding linked to the later controls that resolved its missing-context behavior. Matching backend source would add more than another broad crawl or another bare QR GET.
