# 23.1.b RBI URL hunt, deeper pass (2026-10-28)

**Result:** No 23.1.b firmware URL found. This pass made **no new live contact** with the F1 or any Telia host. It used saved artifacts, local captures, and public web reads only.

**Why no URL was found (DERIVED):** the UI upgrade path is a local file upload, and a Telia-pushed update is delivered through the ACS (CWMP) session, not stored as a URL in the web UI. The URL can only come from device logs, the ACS session, or a WAN capture that shows that session. None of the local artifacts contains a WAN-side capture of the 23.1.b unit.

## Offline checks (VERIFIED, local files only)

| Source | What was checked | Result |
| --- | --- | --- |
| `artifacts/hars/*.har` (3 files, 762 entries) | Hostnames and `upgradefw` / `.rbi` / `teliacompany` strings | Only `192.168.2.1` and one `api.github.com` request. No firmware or update host. |
| `artifacts/ui/logviewer-modal.lp.html` (2026-10-11 snapshot, 283 rows, per [f1-logviewer.md](f1-logviewer.md)) | Filter list and rows for `cwmp`, `inform`, `acs`, `rgw`, `download` | No CWMP rows. The process filter list has no `cwmpd` entry. |
| Saved `system-config-min.js` | Upgrade path | Firmware is selected by local file input `#file-upgradefw`. No URL field. |
| `artifacts/logs/lcm-23.1*.json` | LCM responses | `Apps was not found` for `GCNT-X 23.1` and `GCNT-X 23.1.b`. |
| `artifacts/captures/want.pcapng` | `tshark` DNS query, TLS SNI, and HTTP host names | 8 unique names, none Telia. Earlier notes place this capture on the LAN mirror ([want-pcap.md](want-pcap.md)). |
| `artifacts/captures/wan2-real.pcapng` | Same | 0 names. Mixed-link framing per [software-pass-capture-review.md](software-pass-capture-review.md). |
| `artifacts/bootp/2026-10-13/wan.pcapng` | Same, plus raw strings and DHCP options | 32 names, none Telia. Content is a BOOTP session on the LAN. DHCP option 43 holds a vendor blob with no URL. It contains a device identifier, which is not recorded here. |

**DERIVED from the table:** no local capture is a WAN-side view of the 23.1.b unit's CWMP or update traffic. The earlier WAN-capture work in [wan2-tagged-frames.md](wan2-tagged-frames.md) is still the blocker.

## Community record (REPORTED, not reproduced here)

Source: hack-technicolor issue #321, read in the browser pane. It is a community thread with no maintainer verification.

- The ACS endpoints listed by a contributor are `https://rgw.teliacompany.com:7575/ACS-server/ACS` (about FW 18.3–19.5) and `https://acs.telia.com:7575/ACS-server/ACS` (older). These are CWMP endpoints, not file hosts.
- A 19.4 contributor said the `acs.telia.lt` RBI URL came from `logviewer` requests on that unit. The URL reached the device's own log, not the UI.
- A contributor reported a 23.1.b build on an EWA1331 (F1x) unit, `23.1.b.0448-7241004-20250925120503`. That contributor also said 23.1.b can't be downgraded, even by BOOT-P or TFTP.
- Another contributor reports `23.1.b.0448-7241004` and `23.1.b.0448-7241016` returned `.rbi not found`. This matches our 404s for those names, which is VERIFIED only for the names we probed.
- Reported working 19.x names: `1940507x4581025`, `1951062-gcnt-x-4581001`, `1951062-gcnt-x-4581031`, `EWA1331_EWA1330_gcnt_x_19.5.1062_4581010_unified`, plus the 19.4.0856 names already in the repo.

## Unexplored device-side source

- The saved logviewer JS (`artifacts/ui-grab-20261012T040001Z/files/js__logviewer-min.js`) shows an **Export All** action that POSTs `action=export_log`. The saved table view (283 rows) has no CWMP lines. An exported log may hold more. This is **UNKNOWN** until run.
- Requires an authenticated session on the owned unit and a file download. Needs your approval.

## Not shown

- Any 23.1.b firmware URL, file, or response body.
- That `cwmpd` is active on the 23.1.b unit (no CWMP rows in the saved view).
- That the Telia ACS accepts connections from this network. Earlier probes in [acs-telia-8888-probe-2026-10-28.md](acs-telia-8888-probe-2026-10-28.md) got no HTTP response.

## Next step (each needs your approval)

1. **Authenticated `export_log` on the owned unit.** One logged-in POST to `logviewer`, plus one file download. Search the export for `cwmpd`, `Download`, `Inform`, and any `http(s)://` string. This is the most direct live check that doesn't touch Telia infrastructure. Respect the nginx 503 cooldown noted in [f1-ui-leads-23.1b.md](f1-ui-leads-23.1b.md).
2. **Passive WAN capture on the F1 uplink with no trigger.** Placement must be on the F1 side of the WAN, not the Mac's `en0`. The community config in #321 (18.3 era, unverified here) lists a 14-day periodic-inform interval, so a passive capture may need up to two weeks.
3. Low value: a single GET to the community-listed ACS endpoint. It is a third-party production service, and the expected reply is a CWMP or auth error, not a firmware URL. I don't recommend it without a specific reason.

## Reproduction

```bash
rg -a -n -i "cwmp|inform|acs\.|rgw\.|7575|7547|download" artifacts/ui/logviewer-modal.lp.html
for f in artifacts/hars/*.har; do python3 -I -c "import json,sys,collections,urllib.parse as u; h=json.load(open(sys.argv[1])); print(sys.argv[1], collections.Counter(u.urlsplit(e['request']['url']).netloc for e in h['log']['entries']))" "$f"; done
tshark -r artifacts/captures/want.pcapng -T fields -e dns.qry.name -e tls.handshake.extensions_server_name -e http.host | sort -u
```
