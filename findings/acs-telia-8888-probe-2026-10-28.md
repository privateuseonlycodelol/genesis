# ACS `/TCH/` probe on Telia :8888 and community repository check (2026-10-28)

**Result:** No 23.1.b RBI URL found. The probe is **inconclusive**: TCP connects on both hosts, but no HTTP response came back, so it can't tell "file absent" from "server not answering HTTP". The community repository page has no GCNT-X / EWA1330 entry.

## Scope

- Owner-approved in chat: paced read-only ranged GETs to the ACS hosts, and a read of the hack-technicolor repository page.
- No device contact. No LAN or router requests. Nothing downloaded or flashed.

## Hosts and names

Script: `scripts/f1_acs_name_probe.py` (base URLs `http://acs.telia.se:8888/TCH/` and `http://acs.telia.lt:8888/TCH/`, names from [decomp-kickoff.md](decomp-kickoff.md)).

| Host | Name | Method | Outcome |
| --- | --- | --- | --- |
| acs.telia.se:8888 | `EWA1330_F1_gcnt-x_19.4.0856-4581012.rbi` (control) | `Range: bytes=0-0`, 15 s timeout | `TimeoutError` |
| acs.telia.se:8888 | `EWA1330_F1_gcnt-x_23.1.b.0448-7241017.rbi` | same | `TimeoutError` |
| acs.telia.lt:8888 | `EWA1330_F1_gcnt-x_19.4.0856-4581012.rbi` (control) | same | `TimeoutError` |
| acs.telia.lt:8888 | `EWA1330_F1_gcnt-x_23.1.b.0448-7241017.rbi` | same | `TimeoutError` |

Follow-up, one HEAD each (`curl -I -m 15 http://<host>:8888/TCH/`, 5 s apart):

- Both hosts: `connect` about 0.03 s, then no HTTP status line in 15 s. curl exit 28.
- Control: the rgw host on `:7547` (`nc -z`) connects. Its earlier 19.x file returned 206 in the prior probe.

Classification:

- **VERIFIED:** `acs.telia.se:8888` and `acs.telia.lt:8888` accept TCP connections from this Mac.
- **VERIFIED:** neither returns an HTTP response to a ranged GET or HEAD within 15 s, including for the 19.4.0856 control named in the repo.
- **DERIVED:** the control failing means the probe can't separate a missing file from a non-HTTP or silent service on :8888. These 4 results are not evidence that the 23.1.b file is absent.
- **UNKNOWN:** whether the service speaks HTTP at all, and whether a different path or method gets a response. Earlier notes recorded `connection reset` on `.lt` from a different client. Not reproduced here.

## Community repository (hack-technicolor)

Read via the browser pane, `https://hack-technicolor.readthedocs.io/en/latest/Repository/`, full page text (33 008 characters).

- **VERIFIED:** the page has no `GCNT-X`, `EWA1330`, `EWA1331`, or `teliacompany` entry. The only GCNT entries are `GCNT-N` (OWA0131) and `GCNT-R` (FGA2233).
- **VERIFIED:** the Telia rows that do appear are other boards (for example TG799vn / VDNT-O, TG799vac / VANT-R, DNA0130 / VBNT-Z).
- **VERIFIED:** the guide's "OSCK Not Required" note is on the TG797n v3 / DANT-O row, not on the F1 board.

## What was not shown

- Any 23.1.b file URL, or a file body.
- That the Telia ACS hosts serve RBI files at all.
- Any reachable Telia RBI host for the 23.1.b build.

## Reproduction

```bash
python3 scripts/f1_acs_name_probe.py --list
python3 scripts/f1_acs_name_probe.py
nc -z -G 8 acs.telia.se 8888
curl -s -o /dev/null -w 'http=%{http_code}\n' -m 15 -I http://acs.telia.se:8888/TCH/
```

## Next step

- A passive WAN capture of the device's own update fetch, with no trigger, is still the most direct route. Needs owner approval.
- A different Telia host or path shape would need a new hypothesis. The current names are not enough.
