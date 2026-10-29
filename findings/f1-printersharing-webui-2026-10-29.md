# printersharing webui toggle on 23.1.b (2026-10-29): INCONCLUSIVE, device state not restored

## Question

Does POSTing `printersharing_webui` to `/modals/printersharing-modal.lp` enable the CUPS web interface on :631, which is currently 403 to the LAN?

## Result

**INCONCLUSIVE.** One live POST returned HTTP 200. The :631 response did not change. Neither the modal nor the :631 body exposes the webui state, so the test cannot say whether the setting took effect. The device's prior `printersharing_webui` value was never recorded, so the device may not be back in its original state.

## Evidence

Scripts: `scripts/f1_printersharing_webui_toggle.py` (uncommitted until this pass). Evidence folders under `artifacts/management/printersharing-webui-*` (private, not committed).

| Run | Mode | Outcome (from record.json) |
| --- | --- | --- |
| `…T190504Z` | POST attempt | No `record.json`. Per [tried.md](tried.md), login.lp then returned 503; no POST sent. |
| `…T190515Z` | dry run, `--value 1` | login.lp 200, session reused, no CSRF, `cups_before` 403 / 343 B. Would post `enabled=1`, `webui=1`. |
| `…T190528Z` | attempt | No `record.json`. Outcome not recorded here. |
| `…T191204Z` | live POST, `--value 1` | login.lp 200, session srp_login, no CSRF. POST returned 200, body 2340 B. `cups_after` 403 / 343 B. |

- **VERIFIED:** `:631` GET / returned 403 / 343 B before and after the live POST (`record.json`, `cups_before`, `cups_after`).
- **VERIFIED:** the POST response was 2340 B. Only its first 300 B are saved in `record.json`, so the full re-rendered modal is not in the evidence folder.
- **VERIFIED:** the saved preview of the POST response contains the modal header and no webui control. This does not show the webui state.

## Read-back (2026-10-29 20:35Z, GET only)

Script: `scripts/f1_printersharing_read.py`. One login (session `srp_login`), one `login.lp` (200), one modal GET (200, 2340 B). No POST. Evidence: `artifacts/management/printersharing-read-20261029T203540Z/modal.html` (private).

- **VERIFIED:** the modal's Enabled control is `<input type="hidden" name="printersharingEnabled" id="printersharingEnabled" value="1">` inside a switch with `switchOn`. Current Enabled = **1 (ON)**.
- **VERIFIED:** the form has no webui control. The modal's only printersharing control is Enabled. The name `printersharing_webui` does not appear in the served modal.
- **VERIFIED:** the form field is `printersharingEnabled` (camelCase). The 2026-10-29 script POST used `printersharing_enabled` (snake_case), so **the POST did not name the real Enabled field**.
- **DERIVED:** because the POST's field names did not match the form, it most likely did not write Enabled or webui. This is an inference from the field names, not a before/after comparison. The prior Enabled value is still not recorded.
- **Not shown:** the webui state. The modal does not expose it, and the :631 response does not expose it either.

## Defect found in the script (fixed in this pass)

- **VERIFIED (source, before this pass):** the script hardcoded `printersharing_enabled=1` in both the dry run and the POST. Its docstring said the value was "re-sent at its current value". Those two statements conflicted.
- **Consequence:** the 191204 POST set Enabled to `1` whatever its prior value was. If Enabled was `0` before, the live POST may have turned printer sharing on. The prior value is not recorded anywhere in `artifacts/`, so this cannot be checked offline.
- **Fix (this pass):** `--enabled {0,1}` is now required. `build_post_fields()` sends the value passed in and rejects anything other than `0` or `1`. `scripts/test_printersharing_webui_toggle.py` covers the regression (4 tests, passing). The script does not parse the modal's current Enabled value; the operator reads it first.

## Not shown

- Whether `printersharing_webui=1` changed anything on the device. The :631 response did not change and the modal does not show the state.
- The device's original `printersharing_webui` value and original `printersharing_enabled` value. Neither was recorded.
- Whether the 191204 POST changed the Enabled switch.

## Reproduction (read-only reasoning, no device contact in this pass)

```bash
rg -n "enabled|webui" artifacts/management/printersharing-webui-1-20261029T191204Z/record.json
cd scripts && python3 -m unittest test_printersharing_webui_toggle -v
```

## Next

1. **Do not POST with `scripts/f1_printersharing_webui_toggle.py` as written.** Its field names do not match the served form (`printersharing_enabled` vs `printersharingEnabled`), and no webui field is known. Any future write needs the real field names first, from a source the device serves, and a before/after read.
2. The webui flag has no visible control in the 23.1.b modal. Testing it further needs the Homeware or CUPS source (rootfs or GPL request), not more POSTs.
3. If the modal exposes no state, the webui test is parked. The offline reading in [tried.md](tried.md) (CUPS `client.c` order: `cupsdAuthorize` runs before the WebInterface check) and the deny-by-default model in [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md) suggest the 403 is the Location ACL, which would hide the webui flag from the LAN. This is DERIVED from upstream source; the device's `cupsd.conf` was not obtained.
