# F1 TRACE action and command-input check — 2026-10-12

## Scope

Target: Telia F1 / GCNT-X. The live authenticated page advertised build `23.1.b.0448-7241017-20260223134332-1bc56e11012dfec7d96d5c28eb498c16c196a568`. Requests were made only to the owner gateway at `192.168.2.1`; diagnostic destinations were loopback (`127.0.0.1`). No configuration was changed and no third-party host was contacted.

## Verified client request path

- The rendered form is `POST modals/diagnostics-ping-modal.lp`. The Trace Route button sets `action=TRACE`. Its fields are `ProtocolVersionTrace`, `ipAddressTrace`, `MaxHopCount`, and `MaxSize` ([saved modal HTML](../artifacts/ui/modals-diagnostics-ping-modal.lp.html), lines 40–46).
- `ipAddressTrace` is a plain text input with no `pattern`, `maxlength`, or `required` attribute. `MaxHopCount` has `pattern="[0-9]{1,2}"` and `maxlength="2"`; `MaxSize` has no visible input constraint.
- **VERIFIED static behavior:** the shared handler in `main-min.js` adds the button's `action` value and CSRF token, serializes all modal inputs whose `data-for` includes `TRACE`, and passes them to the modal form action. The helper uses jQuery `.load(url, data, callback)`; with a data object, this sends a form POST. The handler does not validate or rewrite the destination string ([`main-min.js`](../artifacts/ui/main-min.js), lines 304 and 322).
- Thus the browser submits `ipAddressTrace` as a URL-encoded form field alongside `action=TRACE`, `ProtocolVersionTrace`, `MaxHopCount`, `MaxSize`, and the CSRF token. There is no destination allowlist or escaping step in the saved client code.

## Live checks

The request used the saved local session cookie and a fresh CSRF value read from the authenticated gateway page. Values of cookies and tokens were not recorded. Python 3.14.7's standard-library HTTP client was used. The authenticated baseline GET returned the gateway page and CSRF meta. All diagnostic POSTs returned HTTP 200 from `/modals/diagnostics-ping-modal.lp`; the first TRACE and shell-substitution responses were also checked and did not contain a login form.

| Request | Response | Transformer log observation |
|---|---|---|
| `TRACE`, `ipAddressTrace=127.0.0.1`, IPv4, max hops 1, size 46 | HTTP 200, diagnostics modal HTML; no login page | Existing helper event remained unchanged |
| `TRACE`, `ipAddressTrace=$(printf 127.0.0.1)`, IPv4, max hops 1, size 46 (two submissions) | HTTP 200, diagnostics modal HTML; the trace field displayed `Please enter valid ipv4/domain address` and retained the submitted string | No new helper event |
| Valid control: `TRACE`, `ipAddressTrace=127.0.0.1`, IPv4, max hops 1, size 46 | HTTP 200; the validation message was absent | No new helper event |
| Routine control: `TRACE`, `ipAddressTrace=127.0.0.1`, IPv4, max hops 30, size 46 | HTTP 200, 6611-byte response | No new helper event |
| Positive control: `PING`, `ipAddress=127.0.0.1`, IPv4, one repetition, size 56 | HTTP 200, 6263-byte response | A new `transformer[12780]` log row appeared: `async run: /usr/bin/ipping_helper` at device-log time `Oct 12 05:46:16` |

Immediately before the TRACE attempts, the logviewer showed one pre-existing helper row at `Oct 12 05:40:01`. After the TRACE requests it still showed only that row. The one-packet PING then added the `05:46:16` row. This positive control shows that the same authenticated session and log path expose the helper launch for PING.

The substitution response also contained a `localhost.lan` route row, but a subsequent **GET-only** read of the modal showed that row as retained diagnostics state. It therefore cannot be attributed to the substitution input and is not evidence of shell expansion.

## Assessment

- **VERIFIED:** On this 23.1.b build, controlled TRACE requests did not add an `ipping_helper` event; a one-packet PING did. The evidence supports that TRACE does not invoke `/usr/bin/ipping_helper` through the logged transformer async path, while PING does. This is stronger than the earlier uncorrelated `05:08:06` helper line, which did not identify an action.
- **VERIFIED, limited:** the direct form POST containing shell command substitution received the IPv4/domain validation message; the valid loopback control did not. This indicates server-side validation for that input. The validator's implementation and exact ordering relative to backend execution are not available in the saved artifacts.
- **Not demonstrated:** command execution or command injection. The tested substitution string was rejected visibly, and no output was tied to it. This does **not** prove the entire TRACE path safe: only one metacharacter form and a small set of loopback inputs were tested; server source, process tracing, and the active backend binary were unavailable. Other encodings, fields, or parser paths remain untested.

## Reproduction identifiers and limits

- UI artifact SHA-256: `main-min.js` `69dc210d4d827d4c35988bed4c3784a40915ef1c8574b07a9c7258ec222a7e5b`; diagnostics modal HTML `c5b3e5ef0970783be1ad931b0b2fad4e0c92d6b70ea2441029d316ce6fcadcb6`.
- Live experiment input was restricted to the form fields and values in the table. The session cookie and CSRF token were read dynamically and intentionally omitted. Device log timestamps are as rendered by the gateway; timezone metadata was not present in the log HTML.
- No backend `.lp`/Lua implementation for this action or executable-level trace was available in the local artifact set.
