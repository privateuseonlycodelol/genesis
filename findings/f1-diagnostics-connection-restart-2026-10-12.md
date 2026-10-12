# Diagnostics Connection RESTART → ipping_helper — 2026-10-12

Target: owned F1 at `192.168.2.1`, build `23.1.b`. One `operation=RESTART` on the Connection tab, with transformer log before/after.

## Request

Authenticated POST `/modals/diagnostics-connection-modal.lp` (matches UI: `action=SAVE`, `operation=RESTART`, CSRF). No other fields. Paced run via `scripts/f1_diagnostics_connection_control.py`.

| Step | Result |
| --- | --- |
| POST at 08:54:52 local | HTTP **200**, 4,210 bytes, SHA-256 `0af7c338892865f6e04d5b813af5943c670e842f8f80cf4913816a69f454195b` (same as saved connection modal GET in earlier grabs) |
| Transformer log before | Quiet across two reads (SHA `5b37f4fae005b2c1c51d40b1cf71a2a8de853d442280afbb9d9da28e3ce67c17`) |
| Transformer log after | One **new** row: `Oct 12 08:54:52` `async run: /usr/bin/ipping_helper` (no arguments), same second as POST |

**VERIFIED:** Connection “Restart all tests” can launch `/usr/bin/ipping_helper` through the logged transformer path, like [diagnostics PING](f1-ipping-helper-2026-10-12.md). This POST carries **no** host or user string fields—only `operation=RESTART`.

## Exploit status

Not a new injection surface. It is another **trigger** for the same helper already tied to PING. Host-string abuse still depends on the ipping UCI worker, not this RESTART button.

Private artifacts: `artifacts/ui/diag-connection-20261012T065438Z/`.

```sh
cd scripts && python3 f1_diagnostics_connection_control.py --password-file ../artifacts/secrets/f1-admin.password
```
