# F1 log viewer

**When:** 2026-10-11 ~21:30 (UTC+2)  
**Gateway:** `http://192.168.2.1`  
**Config changed:** none

The session cookie from the earlier login was gone. One new login (login page and two SRP posts, all **200**), then two GETs, 2 seconds apart. No HTTP 503.

## `/modals/logviewer-modal.lp`

**HTTP 200**, 68699 bytes. Not the login screen.

The body is **router log lines**, not only the viewer shell. The page also has the shell around the table: a process filter (Everything, crond, kernel, nginx, and others), an Export All button, and a log-level choice. Under that is a filled table with Date, Facility, Process, and Message.

**283 rows**, all dated Oct 11. Most of them are LAN link up/down, bridge port state, and DHCP. A few are nginx session notes from this login, and cron lines. One repeated cron message is `User root is connecting through Crontab` with command `/usr/share/transformer/scripts/obuspa_retriever.sh`. That is a log line. It is not a shell on this Mac.

### Firmware, update server, `.rbi`

**None.** No `.rbi` name, no firmware version string, and no update-server hostname in the messages. No `teliasmartrgw`, `rgw`, or `lcm` host.

Saved: `artifacts/ui/logviewer-modal.lp.html` (MAC addresses redacted).

## Network diagnostics tab

The Connection diagnostics page only links the Network tab to a separate URL, `/modals/diagnostics-network-modal.lp`, which was not already saved. **HTTP 200**, 6554 bytes. It is a port statistics form (link state, speed, byte and packet counts). Not log lines. No firmware version, update server, or `.rbi` name.

Saved: `artifacts/ui/diagnostics-network-modal.lp.html`.
