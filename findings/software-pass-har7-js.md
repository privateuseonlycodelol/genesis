# HAR 7 JavaScript comparison — 2026-10-12

**Scope:** offline inspection of the user's local `7.har` capture (444 entries). No HTTP requests were made, no JavaScript was executed, and the original HAR was left unchanged. This note contains no hosts, query strings, cookies, credentials, or response values.

## Body comparison

Parsed HAR response bodies identified as JavaScript by MIME type or `.js` path. Reconstructed the body bytes from HAR `content.text` (base64-decoded when marked, otherwise UTF-8 encoded), computed SHA-256, and compared each body's basename and hash against the four saved scripts in `artifacts/ui/`.

There were **123 JavaScript response occurrences** and **14 distinct basename/body-hash pairs**. Four distinct bodies exactly match the saved scripts: `login.js`, `main-min.js`, `srp-min.js`, and `system-config-min.js`. No response with one of those basenames had a different hash. Ten other distinct bodies were new relative to the saved JavaScript set and were extracted once each into ignored [`artifacts/ui/har7-js/`](../artifacts/ui/har7-js/) with mode `0600`; the directory is mode `0700`. The manifest records only static paths, SHA-256 hashes, sizes, and extracted filenames. It contains no request host or query string.

| Static response path | Bytes | Assessment |
|---|---:|---|
| `/js/004_wireless.js` | 1,602 | Feature script; explicit backend request below |
| `/js/asmcrypto-min.js` | 123,277 | Crypto-library bundle by name and `asmCrypto` identifier; no backend route found |
| `/js/chart-min.js` | 173,077 | Chart-library bundle by name and `Chart` identifier; no backend route found |
| `/js/diagnostics-ping-modal-min.js` | 285 | Diagnostics UI helper; no backend request path literal found |
| `/js/dmz-modal-min.js` | 528 | DMZ UI helper; contains a `SAVE` form-action field, but no backend method/path literal found |
| `/js/ethernet-min.js` | 4,434 | Ethernet UI helper; contains a `SAVE` form-action field, but no backend method/path literal found |
| `/js/firewall-min.js` | 2,840 | Firewall UI helper; no backend request path literal found |
| `/js/gateway.js` | 2,232 | Session poll and a conditional gateway POST below |
| `/js/jquery-eval-patch.js` | 324 | jQuery evaluation patch by name and jQuery identifiers; no backend route found |
| `/js/password.js` | 4,831 | Password UI; posts to the already-known password route below |

All ten extracted files and the manifest were read back and checked against their manifest sizes and SHA-256 hashes; the manifest paths are static `/js/...` paths with no query or host component. Raw script bodies remain only in the ignored artifact directory.

## Backend calls visible in newly observed scripts

These are **static client-code calls**, not evidence that the HAR contains a successful request or that the backend accepted an action.

- `gateway.js` calls `GET /gateway.lp` with the `getSessionStatus` query parameter. This repeats the previously documented session-role poll; it is not a new endpoint.
- `gateway.js` also contains a conditional `POST ./gateway.lp` with form field `action=URL`, a `urlVal` field, and the page CSRF token. The code is guarded by `if (showZwave)`. This action name was not found in the older saved JavaScript or the reviewed API notes. Its exact server meaning and reachability are **UNKNOWN**; it is not evidence of a usable new backend capability.
- `004_wireless.js` sends a `POST /ajax/wirelesscard.lua` with the page CSRF-token field. No action name is present in that request construction; its callback reads `listatus`, `ssid`, and `radio` fields. This is a newly observed frontend endpoint relative to the saved JS and API notes, but the server implementation, semantics, authorization, and response behavior are **UNKNOWN**.
- `password.js` posts to relative `password.lp` and constructs an `action=PasswordChanged` form field; it also has a `resetLegacySalt` submission field. The route is already documented as the change-password page. These code strings do not establish a separate privilege boundary or successful state change.

The DMZ and Ethernet scripts contain `SAVE` form-action fields, but the scripts themselves do not specify the destination path or HTTP method. Their containing HTML would be needed to attribute a backend request. No action was inferred for the diagnostics or firewall helpers from their filenames alone.

## Reproduction and limits

The comparison used local Python standard-library code to parse the HAR, select JavaScript response bodies, compute hashes, compare against saved `.js` files by basename, and write only nonmatching bodies plus a sanitized manifest. A separate readback check verified each extracted body and file mode. No script engine or browser was used to execute any response code.

The saved comparison set contained four `.js` files, so an absent basename means “not present in the local saved-script set,” not “never shipped by this router.” Static URL strings and form fields identify client behavior only; server routing, authentication, and effects remain unvalidated here.
