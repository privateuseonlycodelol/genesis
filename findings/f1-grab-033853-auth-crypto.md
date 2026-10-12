# Offline auth, crypto, and request-path audit of the 2026-10-12 UI grab

**Scope:** supplied archive `artifacts/ui-grab-20261012T033853Z/`; authentication, password change, SRP/SHA-512 crypt, AES save handling, and `main-min.js` request/render behavior. This pass was offline. It sent no requests, did not execute a complete page or bundle, and did not change the device.

## Evidence basis and limits

The archive JavaScript has collector redactions that alter source syntax. The 24 archived JS members were matched byte-for-byte to the corresponding `~/Downloads/f1-grab_js_*.js` files after applying the collector's known CSRF-token redaction; the parent independently found that the affected archived bundles fail `node --check`, while the originals parse. Thus, archive HTML and metadata below are archive evidence, but source semantics use the matching unredacted local baseline. For redacted lines, line numbering remains aligned; short identifiers are included to make each reference findable. Do not execute the archived JS as captured.

The local baseline source anchors used here have these SHA-256 values (obtained with `shasum -a 256`):

| Baseline source | SHA-256 |
|---|---|
| `~/Downloads/f1-grab_js_srp-min.js` | `05ab9ccc021238ef19ff502b706f7a64190e3f6d8a73b6d76e21709df109749f` |
| `~/Downloads/f1-grab_js_main-min.js` | `69dc210d4d827d4c35988bed4c3784a40915ef1c8574b07a9c7258ec222a7e5b` |
| `~/Downloads/f1-grab_js_password.js` | `56eee50c6e2a91b2c92c59601231b6d16491a25d23a059e0eec4a34bc40b7412` |
| `~/Downloads/f1-grab_js_asmcrypto-min.js` | `255ad7191b3c6f18f4ef1b1221edb3db37a2f34e5a930a3e8e0f1b7a7749a2ef` |
| `~/Downloads/f1-grab_js_login.js` | `56580889444e98af3f348f2e4f52326b2b9d74ad01ace7df6d76c9c25d3b6c76` |

No server handler source was present in this material. Every claim about what the browser calculates or sends is **client-code VERIFIED**; the server's interpretation, storage, authentication outcome, and authorization behavior remain **UNKNOWN** unless explicitly marked otherwise. No password, token, SSID, address, MAC, serial, or cryptographic output is reproduced here.

## Corrections and verified crypto behavior

### Odd SRP salt hex is rejected by the browser parser

The prior [JavaScript deep pass](f1-js-deep-2026-10-12.md) said that an odd-length challenge salt would alter `x` and the client proof. That is too strong and is corrected here.

In `artifacts/ui-grab-20261012T033853Z/files/js__srp-min.js:60`, jsSHA's `function d(b)` throws when a `HEX` string has an odd number of characters. At line 86, the SRP `function f(b,c)` passes `salt || inner_SHA256_hex` to that parser. The digest contributes 64 hex characters, so the combined length has the salt's parity. An odd-length server salt therefore rejects the calculation before the modular exponentiation and before the proof POST. The paired Python helper's `even_hex` behavior pads a different byte representation; it does not model this browser path. This is **VERIFIED client behavior**, not evidence that the server emits an odd salt or that a server login fails.

`function h(a)` at `js__srp-min.js:87` makes `4*a` random bits, converts to hex, and prepends one `0` only if that string has odd length. It does **not** left-pad to a fixed width. Password-change salt outputs are even-length and at most 8 hex digits for `h(8)` and 16 for `h(16)`, but can be shorter. This corrects the earlier report's fixed-width wording. In `generateSaltAndVerifierTheCallback` at lines 90–91, the first salt feeds the SRP verifier; a separate `h(16)` salt feeds `sha512crypt`.

### Password-change paths use two encodings for non-ASCII input

`generateSaltAndVerifierTheCallback` at `js__srp-min.js:90` hashes `UTF8(username + ":" + newPassword)` when deriving the SRP verifier. Its local helper `function a(a)` at line 84 encodes BMP values and valid surrogate pairs as UTF-8. The same callback calculates `cryptedpassword` with `sha512crypt(newPassword, salt)` at lines 90–94. The offline check below confirms the BMP U+00E9 case; lone-surrogate handling and supplementary-plane inputs were not independently tested.

The SHA-512-crypt path does not call that UTF-8 helper. `rstr_sha512` at line 98 hashes an input as a raw string, and `rstr2binb` at line 103 packs each JavaScript code unit as `charCodeAt(...) & 255`. Therefore U+00E9 becomes byte `e9` on the `cryptedpassword` path but bytes `c3 a9` on the SRP-verifier path. For code units above U+00FF, the low-byte behavior follows directly from the same mask; surrogate pairs are processed as two code units in the SHA-512-crypt path. This proves a client-side encoding divergence, not a server-side authentication failure.

The captured password strength rules allow characters in `\x80-\xFE` alongside ASCII classes (`files/password.lp.html:153–163`), so U+00E9 is within the UI's special-character class. That only shows the client gate permits such a character; it does not establish server acceptance.

An independent narrow test supports these source readings. `artifacts/ui-grab-20261012T033853Z/auth-review/auth-byte-probe.js` extracts only the HEX parser, SRP UTF-8 helper, and SHA-512-crypt round functions from the matching baseline. It does not evaluate the page or bundle. For literal synthetic inputs, it verified odd HEX rejection/even HEX acceptance, the SRP helper's UTF-8 bytes against Node `Buffer`, and SHA-512-crypt outputs against system OpenSSL for ASCII, Latin-1 raw-byte, and UTF-8 cases. The raw-byte and UTF-8 non-ASCII hashes differed. The harness supplies Node's SHA-512 primitive to the extracted SHA-512-crypt functions; it does not independently validate the bundle's own SHA-512 compression implementation. The source-level mask and helper are the evidence for the encoding paths.

**Competing explanations for server impact:** (1) the server may store/use `cryptedpassword` as a separate Linux-crypt or compatibility credential, making the byte difference relevant to that credential; (2) the server may ignore or normalize that field and use only the SRP verifier, leaving ordinary SRP login unaffected. Discriminate with the exact `/password` handler if obtained; otherwise use a controlled owned-lab change with a synthetic non-ASCII password, then check SRP login and any separate credential consumer. Neither server-side explanation was tested here.

### Login key availability is gated on proof verification

In `js__srp-min.js:87`, `function g(a)` sets the internal verified flag only when the server's `M` equals the expected proof. `key()` at line 91 returns the derived hex key only if that flag is set. `files/js__login.js:87–95` uses `srp.key()`, converts its hex to a binary string, and stores that in `sessionStorage.session_key` only in the success callback. The login initiation path is `/authenticate` at `js__login.js:161–165`; the proof flow uses the supplied endpoint at `js__srp-min.js:89–90`. This is client control flow only. It neither proves how the server rotates sessions nor guarantees what other tabs hold.

The proof flow remains the same one documented in the earlier pass: 2048-bit group, `g=2`, 256-byte padding, SHA-256 for the SRP intermediates, `I`/`A` plus CSRF for identify, then `M` plus CSRF for the client proof (`js__srp-min.js:85–91`). `login.js:112–125` treats an HTTP 403 callback as a reason to reload the login page for a fresh CSRF token and retry identify; that is only the UI's response to status 403, not evidence that the server uses 403 exclusively for CSRF expiry.

## AES and password-field coverage

### Exact client transform

In `files/js__main-min.js:313–315`, table-row edits encrypt only a field whose name is exactly `password`. The call uses `asmCrypto.AES_CBC.encrypt(value, ca, c, iv)`. At line 325, `ca` is read once from `sessionStorage.session_key` during main-script initialization and `c` is the string `"a"`. In the matching `asmcrypto-min.js:2` implementation, `function U(data,key,padding,iv)` treats the third argument as padding; a truthy value enables PKCS padding. The IV is 16 random bytes from `crypto.getRandomValues`; the submitted string is hex(IV) followed by hex(ciphertext), with no separator or authentication tag in this client format. The call and emitted representation are **VERIFIED client behavior**. Server decryption, integrity checks, key lifetime, and transport protections are **UNKNOWN**.

The generic `#save-config` handler at `js__main-min.js:331` serializes the modal form and encrypts only names matching the case-sensitive regex family `wpa_psk`, `passWord`, `passwordcred`, `wep_key`, `ddns_password`, `ddnsv6_password`, `cwmpAcsPass`, `connectionrequestPass`, `wpa3`, `password@cred`, or `password\.\d+`. The last pattern has a literal dot: it matches `password.` followed by digits, not any name beginning with `password` and digits. After that loop, it prepends `action=SAVE`, `fromModal=YES`, and CSRF, then posts to the form action. No source path here authenticates the ciphertext itself.

The archive contains credential-like field names outside that matcher: `wifi_pswd`, `wifi_pswd_new1`, `wifi_pswd_new2` in `artifacts/ui-grab-20261012T033853Z/files/modals__basicview-wifipsk-modal.lp.html:28`; `pswd` in `.../modals__basicview-wifiguest-modal.lp.html:26`; and `ipsec_psk` in `.../modals__l2tp-ipsec-server-modal.lp.html:18`. Each page's save button uses the global `#save-config` handler (`:32`, `:30`, and `:38`, respectively). The captured generic transform leaves those names' values unchanged. The captured HTML's inline scripts for the Wi-Fi forms do not add an AES transform, and no matching name appears in the captured JS files. This is **VERIFIED coverage of the captured client code**, not proof of wire plaintext or a server weakness: an omitted script, transport layer, or server-side handling could change the consequence.

**Competing explanations for the excluded names:** (1) the generic handler submits the unchanged field values and the endpoint relies on another boundary or receives them as ordinary form values; (2) the endpoint expects client plaintext and hashes/encrypts server-side, or an omitted route-specific client script transforms them. The archive's captured JS and those modal inline scripts did not reveal such a transform, but server source is absent. Discriminate by locating route handlers or capturing a synthetic request in an authorized isolated lab; do not infer server-side storage from the name filter.

The absence of a MAC/tag in the AES-CBC output is likewise a **client-format fact**, not demonstrated malleability or exploitability. TLS, CSRF, server-side validation, and the exact endpoint may provide other controls; their effect was not tested in this offline pass.

## Password-change sequencing lead

`files/js__password.js:97–111` starts `srp.generateSaltAndVerifier("/password", ...)`. In the legacy branch it immediately issues a separate `resetLegacySalt` POST at line 105. The SRP verifier calculation reaches asynchronous `modPowPromise` (`js__srp-min.js:42–43`) and does not issue its `/password` POST until the callback at lines 90–91. Thus the reset POST is initiated before the verifier POST in that branch. This is **VERIFIED client dispatch ordering**. The captured `password.lp.html:161–162` has empty legacy username/salt lists, so this branch is not active for the captured page state.

Two server outcomes remain plausible: (1) reset clears only a legacy wrapper independently, so ordering is intentional and harmless; (2) reset alters state required by the new verifier, so order or asynchronous failure could leave a partially changed credential. Inspect both endpoint handlers or test in an emulator/owned lab with a synthetic account and captured request ordering. No live password change was attempted and no server consequence is claimed.

## Generic `main-min.js` requests and rendering

- `q(a,b,c)` at `files/js__main-min.js:304–305` wraps modal loads, clears pending refresh timers, calls `.load`, then handles the completion. A 403 or returned sign-in marker redirects to `/login.lp`; ordinary error/timeout responses display an HTTP error message; normal completion refreshes bindings and invokes the caller callback. The source verifies this client behavior, not whether a particular 200 response represents an authenticated page.
- The timed modal refresh `m()` at lines 306–307 posts `operation=REFRESH` and CSRF to the form action. The separate auto-refresh `l()` begins one second after modal setup (`:306`) and ticks every second. It includes `action=AJAX-GET`, CSRF, `auto_update=true` in the body and `?auto_update=true` in the URL; it adds repeated `requested_params` for due `[data-ajaxrefresh]` fields (`:307`).
- A string response is parsed as JSON. For each returned key that maps to a requested DOM element, `l()` uses `.val()` when the element's `name` matches the key and otherwise uses `.html()` (`:307–308`). Current captured modal refresh targets are ID-based, including status elements; the initial HTML is not evidence of the later JSON body. Because the failure callback is empty and a JSON parse exception returns before scheduling another timer, an unsuccessful/malformed refresh stops that poll until the UI reinitializes. This is a derived UI consequence of `:307–308`, not a denial-of-service finding.
- **Rendering lead, not XSS claim:** the `.html(response)` branch at `:308` is a client-side HTML sink. One explanation is that the server returns fixed, escaped status markup; another is that it interpolates names or other variable device state without escaping. Static initial pages cannot distinguish them. Inspect the server-side `AJAX-GET` renderer or test a controlled inert marker in an isolated authorized environment before assigning exploitability.
- `D(a,b)` at line 316 inserts a modal response into a wrapper string and loads it into the modal. The trigger is a same-page `data-remote` link (`:318`). This is expected modal plumbing; the source reviewed here did not establish attacker control over the response or wrapper ID.

## Coverage and reproducible checks

- Reviewed the prior JS/auth findings named above; `login.js`, `password.js`, `srp-min.js`, `main-min.js`, `asmcrypto-min.js`; password/login and relevant Wi-Fi/VPN modal HTML; and the auth-sensitive captured form names. Used the baseline copies for altered JS, not the redacted archive bytes.
- **Commands actually run:** `node artifacts/ui-grab-20261012T033853Z/auth-review/auth-byte-probe.js` → exit 0; all seven reported checks `true`. Versions printed by that command: Node `v26.5.0`, OpenSSL `4.0.3`.
- The helper invokes OpenSSL with argv `openssl passwd -6 -salt 1a2b3c4d -stdin`, sending only synthetic bytes over stdin. It reports booleans and tool versions, never test hashes or inputs. It reads `~/Downloads/f1-grab_js_srp-min.js`; it extracts selected functions only.
- Static checks were also performed with `rg` for function identifiers and with a Python `HTMLParser` that printed only input names/types and script-presence flags, never input values. The relevant fields and call sites are cited above. No live network, device mutation, page execution, or server experiment was performed.

## Next prioritized experiment

First obtain or reconstruct the server handlers for `/authenticate`, `/password`, the generic `action=SAVE` routes, and modal `action=AJAX-GET`. That would resolve the three highest-impact unknowns at once: server salt format/encoding, use of the separate `cryptedpassword`, and treatment of client-unencrypted field names and returned HTML. If those handlers are unavailable, the best follow-up is a bounded emulator or owned-lab test using only synthetic ASCII/non-ASCII credentials and inert field/markup markers; observe request bytes and resulting login/render behavior without reusing a real password or changing the production device.
