# F1 bypass and crypto options — 23.1.b (owner box)

**Later-pass update (2026-10-12):** normal admin login plus the authenticated-page CSRF token successfully exercised hidden `getbanksize` and configuration export. The exported binary is preserved privately; no decryption or root is claimed. The earlier pass below is historical, and its negative UI conclusions are superseded by `software-pass-live-access.md` and `software-pass-config-export.md`.

**When:** 2026-10-12  
**Gateway:** `http://192.168.2.1`  
**Config changed:** none. No reboot, reset, upload, or exploit payloads were sent.

This note separates what was tried from what is only a guess.

## Web UI — verified this session

| Request | Status | Result |
|---------|--------|--------|
| `GET /gateway.lp?action=scheduleReboot` | 200 | JSON: `systemTime`, `rebootTime` sentinel `0001-01-01…`, reboot alert strings. Not a firmware URL. |
| `GET /gateway.lp?auto_update=true&getSessionStatus=true` | 200 | `{"current_role":"admin"}` |
| `GET /modals/parental-modal.lp?action=smartwifi` | 200 | `{"current_state":"1","current_phase":""}` |
| `GET /modals/system-config-modal.lp?action=upgradefwstatus` | 200 | **HTML configuration modal**, not JSON upgrade status |
| `POST …/system-config-modal.lp` `action=upgradefwstatus` | 403 | nginx forbidden (plain POST, browser-like headers, and CSRF in body) |

**CORRECTION (2026-10-12):** These observations establish the listed response bodies and statuses only. They do not identify why the POSTs were rejected or establish a general restriction on requests outside the in-page flow. The saved frontend uses **GET** for `upgradefwstatus`; a valid ordinary browser-request control is needed before attributing 403 to feature permissions rather than session/CSRF/request differences. Related public framework code has a CSRF rejection path, but equivalence to this device is unverified. See `software-pass-request-review.md` and `software-pass-source-comparison.md`.

Saved under `artifacts/ui/` (`gateway-scheduleReboot.json`, `gateway-session.json`, `parental-smartwifi.json`, etc.).

## Web UI — pages inventoried earlier; backend coverage incomplete

- Full Advanced dashboard and essentially all card modals (see `findings/tried.md`).
- Log viewer: no `.rbi` or update host in 283 rows.
- `system-config-min.js` upgrade/import/export/reboot actions exist in script but controls are not on the 23.1.b configuration page.

**CORRECTION (2026-10-12):** Fetching these pages does not exhaust the backend surface. Hidden read/export handlers and a successful ordinary browser-request replay were not established by this inventory. No absence of a software-only path follows from this list.

## Classic Homeware “exploits” (reported, not re-run on 23.1.b)

From issue #321 and `docs/gcnt-x-public-hardware.md` on Telia **23.1.b**:

- tch-exploit, Samba, ping/DDNS tricks, fake ACS, `tchroot` SSH — reported **patched or unavailable** on production Telia builds.
- No verified root path from the web UI on this firmware.

**Hypothesis only:** a second-hand **19.x lab** unit might still match old modal tricks; that does not apply to this **23.1.b** subscription router without new evidence.

## Cryptographic options (offline)

| Option | Status |
|--------|--------|
| Decrypt GCNT-X `.rbi` with community `GCNT-R` / `GCNT-N` OSCK | **Failed** (`bad_osck`) — documented in `findings/rbi-crypto-attempt2.md` |
| Derive OSCK from RBI header / LCM JSON alone | **Failed** — same logs |
| `Decrypt_RBI_Firmware_Utility` board keys | **No GCNT-X** entry |
| Guess OSCK or brute-force AES wrap | Impractical; not attempted |
| **Device-backed `GCNT-X.osck`** via eripv2 + ECK (UART/root) | **Open** — one acquisition route; not established as the only possible source |
| On-device `bli_unseal` after root | **Open** — needs shell first |
| WAN mirror during reboot / FOTA | **Open** — capture `.rbi` URL or TLS SNI without decrypting sealed file |

Do **not** loop `attempt_rbi_decrypt.py` again without a **new** key or RBI bytes.

## Hardware / boot (fits owner permission, not done tonight)

- **UART boot log** (Tuesday): partitions, bank names, CFE messages — read-only.
- **NAND dump + TSOP48** (issue #321): needs tools and a spare or accepted risk; extracts OSCK / layout, not a “bypass.”
- **JTAG**: unfinished pinout in community notes; high skill, no published unlock for 23.1.b.

## Single next action

**UART boot log, read-only, no flash.**  
Then decide between **WAN capture for 23.1.b RBI URL** and **eripv2 OSCK extraction** if UART or a lab root path ever appears.
