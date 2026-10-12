# Diagnostics PING launches ipping_helper — 2026-10-12

Target: owned Telia F1 / GCNT-X at `192.168.2.1`. Gateway HTML contained the label `23.1.b`. One ICMP echo was requested, to `127.0.0.1`, one repetition, 56-byte payload. No TRACE, export, reboot, `PINGSTOP`, or other host was sent.

## Result

**VERIFIED:** `action=PING` is what makes `transformer` log `async run: /usr/bin/ipping_helper`. The helper line has no arguments. Command injection is not demonstrated.

The transformer filter was empty on two reads four seconds apart (same body, SHA-256 `031800205ce5a28767accb75df8a2b11ac744f6b50aff3ce89877f51a51168b5`, 2,647 bytes). A full log read between them contained the substring `ipping_helper` zero times. At local `2026-10-12T08:18:56+0200` the client posted:

| Field | Value |
|---|---|
| `action` | `PING` |
| `ProtocolVersion` | `IPv4` |
| `ipAddress` | `127.0.0.1` |
| `NumberOfRepetitions` | `1` |
| `DataBlockSize` | `56` |
| `CSRFtoken` | present, 64 characters, value not recorded |

HTTP 200, 6,213 bytes, SHA-256 `c09ba6189bead97814cf539246526b7438e3d9a39311e280b562a3922ff35669`. The page said status `Ongoing`, success 0, failure 0, and the ping table was empty. The ping button had been replaced by `stop-config_PING` / `data-value="PINGSTOP"` (“Stop Ping Request”). That action was not sent. The hostname field echoed `127.0.0.1`.

Two seconds later the transformer-filtered log was 2,932 bytes, SHA-256 `bdc842c689fb03374196f23188fefe712a246d9dc77b0e58e4e12a85b3a7c522`, and its only row was:

`Oct 12 08:18:56` `transformer[12780]` `async run: /usr/bin/ipping_helper`

The device stamp and the POST wall time are the same second. The message is exactly that path. Nothing follows it.

At `08:20:38` a GET of the same modal (no second ping) showed success 1, failure 0, minimum/maximum/average `1 ms`, and one result row: 64 bytes, `127.0.0.1`, seq 0, ttl 64, time `0.212`. The send button was back. At `08:20:40` the transformer log was byte-identical to the `08:18:58` snapshot, so the GET did not launch the helper again.

Session status before the ping was 24 bytes, SHA-256 `ac77f908c17884c7352cf857a1304f0a28dedb9124cd5a0d60f5adc559cb9bed`, the same body previously recorded as `current_role` `admin`.

## What this does not show

The log does not contain the helper’s arguments, uid, or exit status. The echoed hostname shows the server accepted `127.0.0.1` and later reported one loopback reply. It does not show that the host string is concatenated into a shell command on this spawn path.

**Superseded for the web form:** same-day host-string probes (newline/`logger`, backtick label, duplicate `ipAddress`) did not reach the helper. See [host validation](f1-ipping-host-2026-10-12.md). Command injection via **this** modal is **not demonstrated**; a published unquoted `io.popen` host in `/usr/bin/ipping` remains a **HYPOTHESIS** for other UCI writers only.

The POST body also showed `ipAddressTrace=127.0.0.1` and one existing route row `localhost.lan` / error 0 / RTTs `0.026`, `0.015`, `0.009`, while the ping table was still empty. This request did not send TRACE fields. That route row matches retained diagnostics state from the earlier TRACE check, not this ping.

An `08:02:40` `GET /login.lp` returned the 190-byte nginx 503 stub (SHA-256 `b429e25e7813a9e2b90dcec11d9cb5287751246128dd6c76a7349774829c5554`). That was the already-open cooldown after the key-probe burst. No ping was sent. The run above started after 15 minutes, and this sequence itself did not return 503.

## Reproduction

Python 3.14.7. `scripts/f1_ipping_control.py --password-file artifacts/secrets/f1-admin.password`. Fifteen offline tests in `scripts/test_f1_ipping_control.py` cover the log diff, the fixed loopback form, and the Ongoing/stop-button page. Private bodies, the cookie jar, and `result.json` are under ignored `artifacts/ui/ipping-control-20261012T061839Z/` (the 503 attempt is `ipping-control-20261012T060240Z/`). The saved `result.json` conclusion was written before the completion GET and correctly says the POST body had no result row.

## Next attack on the problem

Follow-up the same day: the helper is started with no arguments, and the web form rejects a newline and a backtick host before that start. Duplicate `ipAddress` fields abort validation with HTTP 500. See [host check](f1-ipping-host-2026-10-12.md).
