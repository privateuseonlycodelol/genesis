# Hidden-action boundary — 2026-10-12

Target: the owned F1 at `192.168.2.1`. A configuration export was taken first. No reboot, factory reset, semi-reset, BOOTP, import, scheduled-reboot write, or firmware upload was sent. `GET action=upgradefwstatus` was also skipped: the related public GUI source deletes upgrade state on that GET when no upgrade is in progress, and that source is not proven to match this build.

## Password storage

The admin password is in `artifacts/secrets/f1-admin.password`, mode `0600`. `artifacts/` is gitignored (`git check-ignore` matches that file). `scripts/f1_readonly_control.py --password-file` reads it. The value is not in this note, the command line, or the test suite.

## Backup

**VERIFIED:** `scripts/f1_readonly_control.py --export --password-file artifacts/secrets/f1-admin.password` completed SRP login (server proof matched), then:

| Step | Result |
| --- | --- |
| `GET /gateway.lp` | 200, 17,267 bytes, no login form |
| `GET /gateway.lp?auto_update=true&getSessionStatus=true` | 200, 24 bytes, JSON key `current_role`, value `admin`. SHA-256 `ac77f908c17884c7352cf857a1304f0a28dedb9124cd5a0d60f5adc559cb9bed` (same body as the 04:56:48 grab) |
| `GET /modals/system-config-modal.lp?action=getbanksize` | 200, 44 bytes. SHA-256 `9e96c830d9644552e74abc8797b4fa6914f15f62e2d581d85a212f0ed9b2dd3c` (same body as the earlier live control and the 04:56:48 grab: success string `true`, bank size 134217728) |
| `POST /modals/system-config-modal.lp` `action=export_config` | 200, 181,137 bytes. SHA-256 `61dee5c7b4511afb0b2dababea162be3cd6a0e2a50b561fda056ccdeeb7fed3f` |

Header field names, in order: `PREAMBLE`, `BACKUPVERSION`, `BOARDMNEMONIC`, `PRODUCTNAME`, `SERIALNUMBER`, `MAC`, `BUILDVERSION`, `CIPHERKEY`, `SIGNATUREKEY`. Same names as the two earlier exports (181,057 and 181,089 bytes). Field values were not printed. The body was not decrypted. This is a configuration envelope, not a firmware image, a root shell, or an OSCK.

Private files: `artifacts/ui/readonly-control-20261012T051406Z/` (mode 0700).

## Unauthenticated boundary

Six requests, 2 seconds apart, no HTTP 503. No admin cookie was reused.

| Request | Authentication | Result |
| --- | --- | --- |
| `GET …?action=getbanksize` | no cookie | 200, 5,784-byte login HTML |
| `GET /gateway.lp?action=scheduleReboot` | no cookie | same 5,784 bytes, SHA-256 `3e6b7d64a4967895b5b4863232dd8c9a3cba97d6440137ce9d73f6fddfcdaae5` |
| `POST export_config` | no cookie, dummy CSRF | same body as those two GETs |
| `GET /login.lp` | fresh anonymous cookie | 200, 5,784-byte login HTML, different hash (CSRF differs per session) |
| `POST export_config` | that anonymous cookie and its login-page CSRF | byte-identical to that session’s login page. Not an export |
| `GET` session-status poll | same anonymous cookie | byte-identical to that login page. Not `current_role` JSON |

**VERIFIED:** without an admin session, the hidden export and the two metadata GETs return the login page. They do not return bank-size JSON, schedule JSON, or the config envelope. An earlier authenticated export that used a stale CSRF token returned HTTP 403; that is a different failure from “no session.”

**DERIVED:** Tampermonkey archives that still show `current_role` JSON (e.g. `notloggedin.zip`, 2026-10-12) used the **browser admin cookie**, not an unauthenticated client. Offline diff: [`f1-grab-notloggedin-2026-10-12.md`](f1-grab-notloggedin-2026-10-12.md).

Private files: `artifacts/management/boundary-20261012T051446Z/`.

## What this does not show

No root access, firmware image, decrypted configuration, or upload handler was obtained. State-changing action names were not sent, so their server behavior remains untested. The next useful step is still offline: match this export’s header and trailer to a 23.1.b producer before attempting decryption. Do not send reboot, reset, import, or an RBI upload on this unit.
