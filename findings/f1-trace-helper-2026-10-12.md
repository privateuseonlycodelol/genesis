# Diagnostics TRACE launches igd_traceroute_helper — 2026-10-12

Target: owned F1 at `192.168.2.1`, build `23.1.b`.

## Why the first TRACE pass looked negative

The [05:46 TRACE/PING session](f1-trace-path-2026-10-12.md) only watched for **`async run: /usr/bin/ipping_helper`**. On published Homeware, **PING** uses `ipping_helper` → `/usr/bin/ipping` (`io.popen` with unquoted host). **TRACE** uses a separate chain: **`igd_traceroute_helper`** → `/usr/bin/igd_traceroute` (same unquoted-host pattern in public trees).

**VERIFIED correction (08:56:52 local):** one loopback `action=TRACE` (`ipAddressTrace=127.0.0.1`, `MaxHopCount=1`, `MaxSize=46`) added exactly:

`Oct 12 08:56:52` `transformer[…]` `async run: /usr/bin/igd_traceroute_helper`

No arguments after the path (same logging style as `ipping_helper`). HTTP **200**, 6,138 bytes. Quiet log before POST; new line only after POST. Tool: `scripts/f1_trace_control.py`. Artifacts: `artifacts/ui/trace-control-20261012T065639Z/`.

The earlier conclusion “TRACE did not launch a helper” was **wrong oracle**, not proof TRACE is inert.

## Host injection on `ipAddressTrace` (same day)

`scripts/f1_trace_host_probe.py` — mirror of the PING host suite:

| Case | HTTP | Helper launched? | Notes |
| --- | --- | --- | --- |
| Newline + `logger genesis-trace-marker` | 200 | **No** | `Please enter valid ipv4/domain address`; marker **echoed in HTML** only |
| `` `logger.`x `` | 200 | **No** | Same rejection phrase |
| Duplicate `ipAddressTrace` | **500** | **No** | 170-byte nginx stub (same class as duplicate `ipAddress` on PING) |

**VERIFIED:** web validator blocks metacharacter hosts before `igd_traceroute_helper`. No syslog marker, no new helper on rejected posts. Artifacts: `artifacts/ui/trace-host-20261012T065708Z/`.

## Exploit status

Same as PING: **REPORTED** unquoted host in `/usr/bin/igd_traceroute` is a shell sink **if** a writer stores the trace host without this validator. This form did not demonstrate injection. **UNKNOWN:** `MaxSize` (no `maxlength` in markup) was not fuzzed for numeric/shell edge cases.

## Reproduction

```sh
cd scripts
python3 f1_trace_control.py --password-file ../artifacts/secrets/f1-admin.password
python3 f1_trace_host_probe.py --password-file ../artifacts/secrets/f1-admin.password
```
