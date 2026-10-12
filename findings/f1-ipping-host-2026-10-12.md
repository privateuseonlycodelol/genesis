# PING host reaches a shell builder, and this web form blocks it — 2026-10-12

Target: owned F1 at `192.168.2.1`, build label `23.1.b`. Continuation of [the helper launch](f1-ipping-helper-2026-10-12.md).

## What the command is

**REPORTED** from published Homeware rootfs `raincoats/TG799vac-router` `usr/bin/ipping` (4,123 bytes) and the same pattern in `BoLaMN/VBNT-V`: the helper `/usr/bin/ipping_helper` is a short Lua script. Its commit rule is only `^ipping /usr/bin/ipping_helper` (`Ansuel/tch-nginx-gui` `dev2_ipping.ca`). On a requested UCI section it starts `/usr/bin/ipping` with the section name. That worker reads `host` from UCI and runs:

`ping -q <iface> -c <count> -s <size> -w <timeout> <host>`

through `io.popen`, with `host` unquoted. `count`, `size`, and `timeout` are passed through `tonumber` and `%d`. `usr/bin/igd_traceroute` does the same with an unquoted host. The public modal writes `uci.ipping.@diagping.Host` only after `validateStringIsIP` or `validateStringIsDomainName`.

**DERIVED for this unit:** the 08:18 loopback result of 0.212 ms was displayed as `1 ms`, which is what that parser does for a zero integer part. In the 08:33 transformer log, `async run:` prints the whole command when the command has arguments (`/etc/init.d/firewall reload;/etc/init.d/weburl restart;/etc/init.d/dnsfilter reload;` and `/etc/init.d/ipsec reload`). Every `ipping_helper` line is exactly `/usr/bin/ipping_helper` with nothing after it. The host is not an argument of that spawn. The same log names `/usr/bin/igd_traceroute_helper` once, at 08:30:53. Those extra lines were already present before the posts below.

The published domain check uses the Lua class `[a-zA-z0-9]`. In Lua 5.1 that range includes a leading backtick, so `` `logger.`x `` passes the published function (checked here with Lua 5.5.1 on the 5.1-interpreted pattern). A newline does not.

## Live checks

Authenticated `action=PING`, IPv4, one repetition, size 56. Python 3.14.7, `scripts/f1_ipping_host_probe.py`. Private bodies: `artifacts/ui/ipping-host-20261012T063344Z/` and `ipping-host-20261012T063655Z/`.

| Host | Result |
|---|---|
| `127.0.0.1`, newline, `logger genesis-ipping-marker` | HTTP 200, 6,416 bytes. Phrase `Please enter valid ipv4/domain address`. The field echoed all 38 characters, including the newline. Send button stayed. Transformer log SHA-256 unchanged (`4f2ac6ba46095354a45df9f741d624c2bcb96ee16ccd4b79dd3d7ed1ecd7ad41`). No marker. |
| `` `logger.`x `` | HTTP 200, 6,388 bytes. Same phrase, payload echoed (10 characters), same log hash, no marker. |

**VERIFIED:** both strings were rejected by the web validator before `ipping_helper`. The published `A-z` backtick bypass does not pass this build. The rejection page still showed success 0 and failure 10; no helper line was added, so those counters are not a result of these posts.

Duplicate `ipAddress` fields, clean loopback then the newline host, and the reverse order:

Both returned the 170-byte nginx HTTP 500 page, SHA-256 `9e93ecf12d78a8c4c278708706bd249fe086983fb28f82eb880f5c7795043962`. No marker. The helper lines did not gain an entry; the 08:18:56 line aged out of the window. The log at 08:37:11 and 08:37:17 records the abort:

`diagnostics-ping-modal.lp:160` `content` → `:98` `restartTest` → `content_helper.lua:544` `validateObject` → `post_helper.lua:3152` → `post_helper.lua:830` `GetIPType` → `inet.lua:41` `isValidIPv4` → `inet_pton` (`string expected, got table`).

**VERIFIED:** a repeated `ipAddress` is a table by the time IP validation runs, and that call aborts the request. It does not start the helper and does not reach `io.popen`. Later log reads still returned HTTP 200.

## Exploit status

| Vector | Result |
| --- | --- |
| Web `action=PING` host → `io.popen` | **Not demonstrated.** Validator rejects metacharacters; helper starts with empty argv. |
| Duplicate `ipAddress` → skip validation | **Refuted.** HTTP 500 in `GetIPType` / `inet_pton`; no helper. |
| Published `A-z` backtick domain bypass | **Refuted on this build** (stricter gate than upstream pattern). |
| TR-069 / USP `IPPing.Host` without UI validator | **BLOCKED on LAN (2026-10-12).** CWMP **7547** and common USP/MQTT/STOMP/CoAP ports **closed**; no USP Set exercised. Cron `obuspa_retriever.sh` **VERIFIED** in logs. See [f1-usp-ipping-2026-10-12.md](f1-usp-ipping-2026-10-12.md). |

## Reproduction

```sh
python3 scripts/f1_ipping_host_probe.py --password-file artifacts/secrets/f1-admin.password
python3 scripts/f1_ipping_host_probe.py --password-file artifacts/secrets/f1-admin.password --pollution
python3 -m unittest scripts.test_f1_ipping_host_probe -v
```

Pace requests (script uses 2 s spacing). Stop on nginx **503** (documented cooldown after the key-probe burst). Do not send `ID_HOST` unless the marker appears in logs. Private artifacts: `artifacts/ui/ipping-host-20261012T063344Z/`, `ipping-host-20261012T063655Z/`.

Related: loopback causation control — `scripts/f1_ipping_control.py`, [f1-ipping-helper-2026-10-12.md](f1-ipping-helper-2026-10-12.md). TRACE substitution rejection on the same modal — [f1-trace-path-2026-10-12.md](f1-trace-path-2026-10-12.md).

## What is still open

Obtain **23.1.b** `/usr/bin/ipping` and `/usr/bin/ipping_helper` from rootfs or shell and confirm the `io.popen` host string. If a non-UI writer can set `uci.ipping.@diagping.Host` (USP/CWMP when ACS is reachable, or another transformer path), retest with a loopback-only marker there — not another spray on this form unless a new bypass is identified.
