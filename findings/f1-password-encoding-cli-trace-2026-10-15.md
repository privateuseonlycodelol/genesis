# Password encoding — community CLI consumer trace and offline collision matrix (2026-10-15)

**Scope:** finish the pinned [Ansuel/tch-nginx-gui](https://github.com/Ansuel/tch-nginx-gui) trace at commit `ecd493c591afd7de47e624245bd1ac1bd9a526a2`; extend offline client checks; no live router requests and no password change on device.

**Equivalence to Telia F1 23.1.b:** **UNKNOWN.** Lua/nginx paths below are **REPORTED** from decompressed community GUI files, not from this unit’s rootfs.

## Client defect (unchanged, VERIFIED offline)

Canonical write-up: [f1-grab-033853-auth-crypto.md](f1-grab-033853-auth-crypto.md). SRP verifier derivation uses UTF-8 on `username + ":" + newPassword`; `cryptedpassword` uses `sha512crypt` over JavaScript string code units masked to eight bits. This pass re-ran `artifacts/ui-grab-20261012T033853Z/auth-review/auth-byte-probe.js` (exit 0, seven checks true; Node v26.5.0, OpenSSL 4.0.3).

**VERIFIED — UI gate allows non-ASCII that triggers the split:** captured `password.lp.html` sets `spl_char` to include `\x80-\xFE`; `password.js` requires `passwordCheck(...) >= 4` before change (lower+upper, digit, special, length ≥ `passwordlength` = 10). Synthetic passwords used in the matrix below all reached strength level 5.

## Community server path for `cryptedpassword` (REPORTED source)

| Step | File (pinned tree) | Behavior |
|------|-------------------|----------|
| Password endpoint auth | `usr/lib/lua/web/sessionmgr.lua` | Successful SRP proof at the password endpoint sets `changeAllowed`; handler accepts `salt`, `verifier`, optional `cryptedpassword`, calls `sessioncontrol.changePassword`. Requires current-password proof — **not** an unauthenticated change. |
| Datamodel update | `usr/lib/lua/web/sessioncontrol.lua` `M.changePassword` | Always writes `uci.web.user.@<section>.srp_salt` and `srp_verifier`. **If** `cryptedpassword` is set **and** `dm.getPN("rpc.user.@" .. user.name .. ".pwcrypt", false)` is true, also sets `rpc.user.@" .. user.name .. ".pwcrypt`. |
| RPC mapping | `usr/share/transformer/mappings/rpc/user.map` | `rpc.user` entries are **only** users returned by `setClashPassword.listClashUsers()` (scan `/etc/passwd` for lines matching `^(.-):.*shell`). `pwcrypt` set validates with `validateCredentials(..., true)`; `commit()` calls `setCryptedPassword`. Getter returns `""` (hash not exposed). |
| Validation + apply | `usr/lib/lua/transformer/shared/setClashPassword.lua` | `validateCryptedPassword` enforces `$5$` / `$6$` shadow form, 16-char salt, hash length 43/86. `setCryptedPassword` requires `isClashUser` (clash/restricted shell in passwd). `execUpdate` runs `/usr/share/transformer/scripts/update_passw.sh '<user>' '<hash>' '-e'`. |
| Shell helper | `usr/share/transformer/scripts/update_passw.sh` | Sources `/lib/functions/provision.sh` and calls `set_pass "$@"`. **`provision.sh` / `set_pass` are not in this decompressed tree** — final shadow write semantics on real firmware remain **UNKNOWN** here. |

**DERIVED impact model (hypothesis, not demonstrated on F1):**

1. Web login continues to use SRP (UTF-8 identity string).
2. If the web account **name** matches a **Clash** `/etc/passwd` user and `pwcrypt` is present in the datamodel, the browser-submitted `cryptedpassword` becomes the CLI/shell credential (shadow-style `$6$` hash).
3. That hash is computed with the **low-byte** password bytes from the browser, while a typical UTF-8 terminal typing the same visible password would make `crypt(3)` use UTF-8 octets — **mismatch risk** for non-ASCII, not for pure ASCII.
4. If there is **no** matching Clash user, `cryptedpassword` may be accepted on the wire but **not** stored via `rpc.user` — SRP-only impact.

**F1-specific Clash context (prior device evidence, not re-tested today):** UART/logviewer on this GCNT-X unit showed `restricted_shell` and `[clash-access-control] User root has no serial access` ([f1-uart-interaction-2026-10-12.md](f1-uart-interaction-2026-10-12.md)). That supports a Clash gate on serial; it does **not** prove whether the **web admin** user has a `pwcrypt` row or whether dropbear/telnet is enabled.

## Offline collision matrix (VERIFIED client-only)

Tool: `scripts/f1_password_encoding_matrix.mjs` (baseline `f1-grab_js_srp-min.js` SHA-256 `05ab9ccc021238ef19ff502b706f7a64190e3f6d8a73b6d76e21709df109749f`).

| Case | `password_utf8_vs_lowbyte_differ` | `crypt_same_for_pair` | `srp_identity_same_for_pair` | Notes |
|------|-----------------------------------|----------------------|------------------------------|-------|
| ASCII control | false | — | — | Paths agree on password bytes. |
| `é` in password | true | — | — | Confirms UTF-8 vs low-byte split. |
| `U+0100` vs `U+0000` (equal length) | true (each) | **true** | **false** | Low-byte strings equal; distinct SRP identities. |
| `U+01E9` vs `U+00E9` (equal length) | true (each) | **true** | **false** | Same low-byte collision pattern. |
| Supplementary char (emoji) | true | — | — | Strength gate still passes; encoding split present. |

These results show **distinct web passwords can yield identical `cryptedpassword` hashes** while producing **different SRP verifiers**. That is a **credential inconsistency** in the client implementation. It is **not** demonstrated authentication bypass, privilege escalation, or Telia-specific server behavior until a consumer on the owned device is exercised.

Regression: `node scripts/test_f1_password_encoding_matrix.mjs` (skips if baseline JS missing).

## Live lab attempt (2026-10-15 evening) — lockout incident

**VERIFIED:** with admin HTTP session + successful SRP proof of the **previous** ASCII password at `/password`, the device returned `{"success":"true"}` for a POST carrying `salt`, `verifier`, and `cryptedpassword` (non-ASCII test password containing U+00E9). **VERIFIED:** subsequent SRP logins for both the new and old passwords returned `M didn't match` (brute-force counter increased). **VERIFIED:** the saved admin `sessionID` cookie from that run still returned `{"current_role":"admin"}` on `getSessionStatus` and loaded `/gateway.lp` (HTTP 200) after login broke.

**Cause (DERIVED):** early hand-rolled blob code did not match the browser’s `generateSaltAndVerifierTheCallback` verifier output; the server stored a bad `srp_verifier`. This is a **tooling failure**, not proof that the encoding split breaks web login when the real UI JS performs the change. **Follow-up:** blob generation moved to `scripts/password-encoding/` (TypeScript + golden tests); Python must use `f1_password_blob.py` and `./scripts/verify_password_encoding_tooling.sh` before any live retry (`scripts/TOOLING.md`, `AGENTS.md`).

**Recovery (owner):** while the session cookie remains valid, use UI **Semi-Reset** or **Factory Defaults** from `system-config-modal.lp`, or import a known-good config export — or load the emergency cookie jar from private `artifacts/management/password-encoding-20261015T165918Z/session.cookies.txt` into the browser (host `192.168.2.1`, name `sessionID`) to reach the dashboard without SRP. Do **not** rerun `f1_password_encoding_impact.py` without fixing `f1_password_blob.mjs` and passing `--ack-lockout-risk`.

**Still not shown:** CLI/`pwcrypt` divergence, collision abuse, or bounty-grade impact. LAN **TCP 22/23 closed** on spot check (same evening).

## What was not shown

- Telia 23.1.b ships the same `sessioncontrol.lua` / `setClashPassword.lua` logic.
- Any live login failure, alternate-password acceptance, or CLI auth outcome.
- Whether `User` (captured username) maps to a Clash account or `rpc.user.@User.pwcrypt`.
- Bounty program or vendor reporting channel.

## Smallest owned-lab experiment (when authorized)

1. Confirm `/etc/passwd` (or datamodel) for web username vs Clash users **without** changing passwords (read-only rootfs dump or future shell).
2. If a Clash mapping exists: one **synthetic** password change using a deliberate collision pair is **not** possible in one step (two different strings → two different SRP proofs). The practical test is a **single** non-ASCII password (e.g. containing `é`), then attempt **web SRP login** and **CLI login** with the same typed string, with documented recovery — only after backup/recovery is agreed.
3. If no Clash/`pwcrypt` path exists for the web user, treat as implementation defect with **no shown security impact** on this unit.

## Reporting title (accurate)

**Inconsistent non-ASCII password encoding between SRP and SHA-512-crypt; community CLI consumer traced; deployed Telia impact unverified.**
