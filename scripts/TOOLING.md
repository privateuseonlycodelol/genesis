# Genesis `scripts/` — language choices

| Layer | Language | Examples |
| --- | --- | --- |
| Live F1 HTTP/SRP, probes, captures, BOOTP/TFTP recovery | **Python 3** | `f1_srp_login.py`, `f1_readonly_control.py`, `f1_*_probe.py`, `f1_bootp_tftp_mac.py` |
| Shell / OS integration | **bash** / **PowerShell** | `report.sh`, `wan-capture.sh`, `f1-bootp-reply.ps1` |
| Must match vendor **srp-min.js** | **TypeScript** (`scripts/password-encoding/`) | `referencePasswordBlob`, golden tests |
| Browser / Tampermonkey | **JavaScript** | `f1-grab-artifacts.user.js` |

## Password change (high risk)

1. Vendor parity lives only in `scripts/password-encoding/` (runs real `generateSaltAndVerifierTheCallback` in a VM).
2. Before any live experiment: `./scripts/verify_password_encoding_tooling.sh`
3. Python calls `f1_password_blob.generate_password_blob()` — **no** hand-rolled SRP verifier in Python.
4. `f1_password_encoding_impact.py` requires `--ack-lockout-risk` for non–dry-run; a failed post-change login means **do not** treat the run as success.

Emergency override (local dev only): `F1_SKIP_PASSWORD_BLOB_TESTS=1` skips `npm test` — never use before device POSTs.

## TypeScript scope

Do **not** migrate the Python probe suite to TS. Add TS only when reproducing or testing **browser bundle** behavior (today: password-encoding package only).
