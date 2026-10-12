# F1 grab 03:38:53 — collection integrity and evidence inventory

Date: 2026-10-12. Scope: offline inspection of the user-supplied archive; no router requests or captured-request replay. The original ZIP and Downloads files were left unchanged. Archive documents were treated as evidence, not instructions.

## Provenance and reconciliation

- Original: `~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip`.
- SHA-256: `cc7af29a6f59f08a9350d1ad14265bbff243be373af3b56ef7170198f0f3a525`. Independently matched Python hashlib and macOS shasum.
- Ignored private extraction and machine-readable audit: `artifacts/ui-grab-20261012T033853Z/`.
- **VERIFIED:** 65 ZIP members: 62 body files (24 JavaScript, 35 HTML, 3 CSS) and three generated Markdown reports. Python ZIP CRC and independent `unzip -t` both pass. No duplicate or traversal member names.
- **VERIFIED:** INDEX has 63 hit rows and MISSES has 80 miss rows: 79 HTTP 404 and one HTTP 500. The 63rd hit is `/ajax/wirelesscard.lua`, declared length zero, omitted from ZIP bodies. Current collector `downloadPackage()` skips falsy bodies; this is consistent with an empty recorded response, not a lost nonempty file. The original HTTP exchange was not independently captured here. The [04:56:48Z grab](f1-grab-045648-review.md) later saved `GET /ajax/wirelesscard.lua?auto_update=true` as 127 bytes of JSON; bare `/ajax/wirelesscard.lua` remained 0 bytes there too.
- **VERIFIED:** every saved body matches the INDEX length. Collector lengths are JavaScript UTF-16 string units (`body.length`), not generally wire bytes; for these files UTF-8 byte lengths equal those counts.
- **VERIFIED:** all 63 INDEX hash cells are blank. The inventory below supplies hashes of the actual ZIP member bytes; it cannot retroactively verify the original wire response or pre-redaction body.
- INDEX generation time is `2026-10-12T03:38:53.086Z` (05:38:53 Stockholm). This is package metadata, not proof that every cached response was collected then. Cache reuse and different runtime timestamps prevent treating all pages as a simultaneous snapshot.

## Six JavaScript bodies were damaged by collection redaction

**VERIFIED:** six ZIP JavaScript files differ from their separately saved, unsuffixed earlier Downloads counterparts. Each difference is explained completely by applying the collector’s broad `CSRFtoken` redaction regex to the earlier file. This is a reproducible transformation, not an inference based on similar lengths. All 24 earlier scripts pass Node syntax checking. In the ZIP, these six fail syntax checking, and the remaining 18 pass. Node v26.5.0 `--check` parses without executing application code.

The damaging replacement is the second regex in `scripts/f1-grab-artifacts.user.js:redact()`: it treats code following `CSRFtoken:` or a name ending in `CSRFtoken=` as a secret. For example, the source expression `CSRFtoken:$(...)` becomes invalid `CSRFtoken:REDACTED"meta...`. In `main-min.js`, the match starts at `b.elementCSRFtoken=A;...` and consumes later assignments through the next whitespace. Consequently code absent from this ZIP cannot be treated as absent from the served bundle.

| Script | ZIP bytes | Earlier bytes | ZIP Node result |
| --- | ---: | ---: | --- |
| `/js/ethernet-min.js` | 4440 | 4434 | Syntax error; earlier file passes |
| `/js/internet-routed-settings-min.js` | 405 | 399 | Syntax error; earlier file passes |
| `/js/main-min.js` | 262687 | 262770 | Syntax error; earlier file passes |
| `/js/password.js` | 4837 | 4831 | Syntax error; earlier file passes |
| `/js/srp-min.js` | 51220 | 51202 | Syntax error; earlier file passes |
| `/js/system-config-min.js` | 6846 | 6816 | Syntax error; earlier file passes |

**DERIVED:** the ZIP is useful for surviving static code and rendered HTML, but the six altered scripts are not executable copies of the deployed application. Exact request/encryption semantics must be anchored to intact prior files, with both hashes recorded. None of these differences establishes a firmware change. The earlier files are a separate local evidence source, not silently repaired ZIP members.

**Recommended collection correction:** preserve original JavaScript bytes in ignored private storage. Redact only narrowly identified literal HTML token values in an explicitly labeled derivative; never run a general assignment regex over source. Keep the raw-byte hash separate from the sanitized derivative hash. The collector currently edited in the workspace was not changed during this documentation pass.

## Crawl coverage and misleading negatives

**VERIFIED:** 152 queue entries represent 152 distinct paths, but 86 already occur among the recorded results (85 terminal 200/404 results and the 500 QR result). Only 66 have no recorded result. Of those 66, 65 are heuristic script-name guesses (47 `guess-modal-to-js`, 18 `guess-modal-stem-min`) and one is `/modals/modals/internet-dhcp-routed.lp`, a duplicated-directory artifact. There is no evidence here that another 152 meaningful, unseen routes remain. A queued path is not a failed request.

| Miss-selection method | Count | Meaning |
| --- | ---: | --- |
| `chase-html-attr` | 17 | Discovery reason, not HTTP verb or server handler |
| `chase-regex-lp` | 7 | Discovery reason, not HTTP verb or server handler |
| `guess-js-to-modal` | 35 | Discovery reason, not HTTP verb or server handler |
| `guess-modal-stem-min` | 3 | Discovery reason, not HTTP verb or server handler |
| `guess-modal-to-js` | 10 | Discovery reason, not HTTP verb or server handler |
| `probe-homeware-name` | 3 | Discovery reason, not HTTP verb or server handler |
| `probe-wellknown` | 5 | Discovery reason, not HTTP verb or server handler |

All probes are **reported GETs** by MISSES; no HAR/headers/cookies accompany these records. The 48 name-guess misses do not establish that the corresponding feature is missing. The `/js/gateway.lp`, `/js/login.lp`, `/js/password.lp`, `/js/modals/device-modal.lp`, and 17 `/modals/modals/...` misses reflect the collector resolving references against source-file locations. Actual AJAX-loaded modal forms execute within the dashboard document; source-file location is not automatically the browser document base. Related intact UI paths are separately present. These negatives must not be reused as application-route exclusions.

**REPORTED by the saved collector record:** GET `/modals/wireless-qrcode-modal.lp` at `2026-10-12T03:37:24.008Z` returned 500, declared 572 bytes. The saved excerpt is a generic nginx Internal Server Error page; no QR HTML was retained. The request was selected from the AP modal (`chase-regex-lp`). Possible explanations include missing required query/context or a backend failure. This does not establish that the route is absent, that authentication succeeded, or that any secret was disclosed. Avoid automatically retrying it merely because it is still queued.

`LEADS.md` is a lossy regex index: CSS `action:hover`, JavaScript `action:function`, and HTML `action="modals` are included, while variable-based and whitespace-separated actions can be omitted. It is not an endpoint inventory or an authorization result. The reviewed surface report uses actual form markup and handler code instead.

## Comparison with earlier evidence

**VERIFIED:** the earlier `03:08:46.410Z` manifest has 54 HTTP-200 records. All 54 paths remain in this index. Nine paths are added: the empty AJAX GET, `font-awesome-ie7.css`, six guided Wi-Fi modals, and `internet-dhcp-routed.lp`. Against existing unsuffixed Downloads body files, 48 of the ZIP’s 62 bodies are byte-identical, 13 differ, and one has no counterpart (`internet-dhcp-routed.lp`). The 13 differences consist of the six redaction-damaged scripts and seven runtime HTML pages. The comparison does not assign an acquisition time to files merely from their filenames.

Runtime differences occur in device, diagnostics-network, Internet, logviewer, system-config, system-info, and time-management HTML. These can reflect changing device state/time and log windows; differing bytes alone are not a build change. Guided modal bodies were already independently available in Downloads, although they were not in the earlier 54-row manifest.

## Auxiliary libraries and CSS coverage

These assets are included to close the static coverage inventory; labels identify bundled source strings rather than independently authenticated upstream versions or vulnerable builds.

| Asset | Direct observation | Research implication |
| --- | --- | --- |
| `js__main-min.js:21,24` | `f.fn.jquery` / expando include `1.11.1` | jQuery version label. A library label alone does not prove an exploitable application path. The intact earlier bundle is required for precise surrounding code. |
| `js__main-min.js:346` | Knockout exports `a.version="3.4.2"` | Client template/binding dependency; no server version implication. |
| `js__chart-min.js:1–6` | Header labels Chart.js v2.9.4; wrapper optionally resolves `moment` | Source header observation; not proof that Moment is loaded or any chart path is attacker-controlled. |
| `js__media-min.js:1–25` | Browser/media-query and CSS helper code, including reading style `innerHTML` | No `.lp`, `.lua`, `$.get`, `$.post`, `$.ajax`, or `.load` literal matched in this file. This is a bounded static negative, not proof no indirect network call is possible. |
| `css__gw.css` | Local image/font URLs; font resource query includes `v=3.2.1` | Font label and local asset references, not executable/server identification. Image/font bytes are outside this ZIP. |
| `css__responsive.css` | Responsive layout rules; no `url(...)` match | Presentation evidence; no additional collected endpoint. |
| `css__font-awesome-ie7.css:7 onward` | 378 `expression(...)` occurrences assign fixed icon entities through old IE `runtimeStyle` / `innerHTML` | Compatibility code is present. Those fixed glyph assignments do not establish an attacker-controlled HTML sink or execution in the current browser. |

The library/CSS checks inspected headers and bounded source contexts and searched exact route/network-call tokens. No library was fetched from the Internet or matched against an advisory database, and no CVE applicability is asserted.

## Reproduction and limits

Actual commands run:

```sh
python3 scripts/test_audit_f1_grab.py
python3 scripts/audit_f1_grab.py \
  ~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip \
  --baseline-downloads ~/Downloads \
  > artifacts/ui-grab-20261012T033853Z/audit.private.json
unzip -t ~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip
shasum -a 256 ~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip
python3 artifacts/ui-grab-20261012T033853Z/verify-js-integrity.private.py \
  > artifacts/ui-grab-20261012T033853Z/redaction-crosscheck.private.json
```

The private cross-check invokes Node `--check` on every ZIP script and earlier counterpart, with per-file exit codes, hashes and concise errors saved in its output. No application script was executed by `--check`. The redaction-equivalence comparison uses Python `re.sub` implementing the collector’s second regex; all 24 earlier JavaScript bodies transform exactly to their ZIP counterparts (18 unchanged, six damaged). Python 3.14.7, Node v26.5.0, Apple Info-ZIP 6.00.

Four auditor regression tests pass: literal independently known SHA-256 of `abc`; UTF-16 versus UTF-8 lengths using a supplementary Unicode character; empty hit bodies and queued/completed overlap; both miss-table layouts; mismatched size/hash and unexpected member; unsafe paths; invalid UTF-8. These fixtures validate the tool, not the router. The separate ZIP CRC/shasum checks validate archive handling.

No new HTTP exchanges, root access, firmware extraction/decryption, configuration decryption, or exploit was demonstrated. Sensitive HTML remains under ignored `artifacts/`; the inventory emits file metadata only. No credentials, cookie values, SSIDs, device MAC/serial, or real WAN/client addresses are reproduced.

## Full saved-body inventory

Hashes below identify **the ZIP’s saved bytes**, including any redaction damage. They do not identify firmware executable binaries. “Same” means exact byte equality with the separately saved unsuffixed Downloads counterpart.

| Route | ZIP bytes | Earlier body comparison | SHA-256 |
| --- | ---: | --- | --- |
| `/css/font-awesome-ie7.css` | 37783 | Same | `90eeaab49e46dce7ee154d82ab2649587942942d3a76dda14b4fc92688ce4ec5` |
| `/css/gw.css` | 184579 | Same | `3f3c178044869f3fe254edd0d35f013fd571ca53dbd73fc5ba7cfd16f3d04534` |
| `/css/responsive.css` | 21578 | Same | `11030dbb1dc22b41850000e827a0053b1b5079e21ce9e9196fe725856ab2428e` |
| `/gateway.lp` | 17211 | Same | `ee66fdea211378e7e473a1cd920d25e7efeefb3b0e11c70eacf6e19f85419d5e` |
| `/home.lp` | 2231 | Same | `ea0dcea7592bb51bec88436e79c3afa68b6d088723e79fa90e7f7161a36b7866` |
| `/js/004_wireless.js` | 1602 | Same | `f3a34ae85d1488a341ffc997480476c32ce9300a5007f0a6c2bf5bd931993ee7` |
| `/js/asmcrypto-min.js` | 123277 | Same | `255ad7191b3c6f18f4ef1b1221edb3db37a2f34e5a930a3e8e0f1b7a7749a2ef` |
| `/js/chart-min.js` | 173077 | Same | `b7d5093eb11205e1b6a2329321c14b3c617b9c78b6bc473b7f90362a91ff5015` |
| `/js/device-min.js` | 4059 | Same | `1383417bea802a4582676174aa7d84d1e6fd3edfbbcbace1b7f605ec16f6404c` |
| `/js/diagnostics-ping-modal-min.js` | 285 | Same | `7eb317ae28f5e940ed2783233c1337fc402c1e85a4d5a5fe66a38cc8fc27b443` |
| `/js/dmz-modal-min.js` | 528 | Same | `57227d7936dc8acfd1ac5bb0385abec060f1dc614d19b6b7ee99094d18a885f1` |
| `/js/ethernet-min.js` | 4440 | Different | `3deede424608823ee2fdf78bfe17060a44712f2692a7a2f9f111c2200ca19a37` |
| `/js/firewall-min.js` | 2840 | Same | `86dde0b04e6649a6525c368209794745930d6894bfa19a21fd2b7aaaa852be83` |
| `/js/gateway.js` | 2232 | Same | `2f40a12cb2be25f42ead29a58f7a88558d954d95a7b5ac60b0efbc59d9001588` |
| `/js/internet-dns-min.js` | 2522 | Same | `eef862079330246806db640854d99472ab7aa7f501855668b5c64c230912b5b2` |
| `/js/internet-routed-settings-min.js` | 405 | Different | `588ac997f64a7a20a0e54da1ffdf0b648b46f14e9148fa16747dfcddd543e60b` |
| `/js/jquery-eval-patch.js` | 324 | Same | `c503d3bfff9637c0ca206e6d9833545ef995069b8e3406766888de6a0c9de9a5` |
| `/js/login.js` | 6608 | Same | `56580889444e98af3f348f2e4f52326b2b9d74ad01ace7df6d76c9c25d3b6c76` |
| `/js/logviewer-min.js` | 1531 | Same | `b64a16f3b9a60b26e5629453c648d06d25a7d827e7bd50ce645f0988e2ff27cd` |
| `/js/main-min.js` | 262687 | Different | `30432db26894bd86d3c90f7d3c7100d4ae2b984aa8d45565028f1f488fd5141e` |
| `/js/media-min.js` | 13111 | Same | `76a416f858b708e15eed72c50bcb5b54adfebac7649c8cf99d0484b083bae654` |
| `/js/password.js` | 4837 | Different | `27e3a99fa90b49f63c9bbc40e53f85979d8b62a70b3a810f6e4221f483249c9a` |
| `/js/srp-min.js` | 51220 | Different | `5f3a65a90a09f003f094ea0574964cd213eb1232c6099d164b2cca07403d2dac` |
| `/js/system-config-min.js` | 6846 | Different | `630beee67cef6637cb730341caf91eb89666cbfe4f8c4bac6706a56c9ab3b327` |
| `/js/tod-modal-min.js` | 900 | Same | `31a0087c475e2acfc94dc627afbec8a7bac5d622d2feb5baaa6d8ff2d9257105` |
| `/js/wanservices-min.js` | 3841 | Same | `d52e10425c5e92f5847b2438c9377a74e5e75a221fd58d3eb9e5393d9efd4dcd` |
| `/js/wireless-ap-modal-newEM.js` | 10814 | Same | `f535c693300dcb1273c1c75e3df933d0712204313ee0f0bde9dd7988afddcd83` |
| `/js/wireless-qrcode-modal-min.js` | 1461 | Same | `79b62225c0600b1f40ee7186c2335313c5f52ec7c813b09178425a5d69abac28` |
| `/js/wireless-radio-modal-newEM.js` | 4387 | Same | `5c8031f4f24bbc376429fcfcb504a8c27cf52d25f4f8a707d30783c7c34babca` |
| `/login.lp` | 5728 | Same | `72b816006a79b646dbf701dee77300039916f96a97a9955dce41627ed55a4817` |
| `/modals/basicview-accesscode-modal.lp` | 5986 | Same | `17917011c4c4847ec520327d216d457977325110424889ddc2437e7fc013b425` |
| `/modals/basicview-wifiguest-modal.lp` | 3465 | Same | `093f057e8a47e77aeba44c54b900d4c5f02dfcdd69e2670becad0578c08ec23d` |
| `/modals/basicview-wifiguest5GHz-modal.lp` | 3460 | Same | `243730dfef4e83e33977f962a39d45993ff9dd89ab15f71b67a604500cbf9459` |
| `/modals/basicview-wifipsk-modal.lp` | 3824 | Same | `bfee9a0eda1f88592ce4c81635b09e473715a74eebd18ae7c1ff4ba3ea07a2d8` |
| `/modals/basicview-wifipsk5GHz-modal.lp` | 3817 | Same | `91609e29da874ebd9da238609ea186983f58a5428f9fa0553b62cae77f4192b8` |
| `/modals/basicview-wifissid-modal.lp` | 3400 | Same | `74a5ea62861cf2f1bf0700e41f20c208c447c10885b4ab85ef37c43c2026257a` |
| `/modals/basicview-wifissid5GHz-modal.lp` | 3412 | Same | `682e9edbef4f0be1d044316f87f7ed7d35df5863d4ae6374197e5d90bd343724` |
| `/modals/broadband-modal.lp` | 1534 | Same | `326db7ab99fab4ef70785d2e343fcd03503c0fee8ca6b27fc1ba036dd35ca9ee` |
| `/modals/contentsharing-modal.lp` | 8873 | Same | `3fcf1d8e1bdbe417f66a75a56d250ee77cb5b64cc51f99bf9fdeb10337aafa89` |
| `/modals/device-modal.lp` | 41950 | Different | `098f868e4b881289de25c46109903aa2a4891dbc5147d3cfd34bc44cb168cb8a` |
| `/modals/diagnostics-connection-modal.lp` | 4210 | Same | `0af7c338892865f6e04d5b813af5943c670e842f8f80cf4913816a69f454195b` |
| `/modals/diagnostics-igmpproxy-modal.lp` | 2345 | Same | `22cec702741e0e47ba3c71167b31ec93a4d41478bb247547ad8b139c2e600994` |
| `/modals/diagnostics-network-modal.lp` | 6560 | Different | `ec98b0c2c6c12168a46bafa948bc312f74e4966d9e9e21f8857a074a2caf4dd7` |
| `/modals/diagnostics-ping-modal.lp` | 6401 | Same | `0ae633faa904bcffbb513d1275c0ecbca8504abc93e63d510d12abf252e0618c` |
| `/modals/dmz-modal.lp` | 1995 | Same | `9d4cf08000c7d260530b2f3021771a3e90603cb59742f7afe03e98d60aefc89f` |
| `/modals/dyndns-wanservices-modal.lp` | 10711 | Same | `ba8f3d2b33875e4a6f485f955f17a168a973f0456b2fe93f9a14d394f1178c77` |
| `/modals/ethernet-modal.lp` | 6220 | Same | `7035b44c34ddd2129685b840487a6977a8398bbc89f97c3b5b38685f00a56255` |
| `/modals/firewall-modal.lp` | 10256 | Same | `3646a60836305caf2bb265f8fc96db84b9b2bdfaad95b27798c2e83559d809a9` |
| `/modals/internet-dhcp-routed.lp` | 6660 | No counterpart | `f8c7baf0155de1c6b05824c0f64df2914f5f9cf17429d40b6a5a525811b62383` |
| `/modals/internet-modal.lp` | 6755 | Different | `bd0f33abbcef30ec6d109f20c65c71e568fabfcb9d707a5b831f0cf3b2860bc6` |
| `/modals/l2tp-ipsec-server-modal.lp` | 3061 | Same | `afe90e5701f0b8ae6d8ffd4bb4a69606ba9a12d89dcdd69ae7fa40a1cfa41e13` |
| `/modals/logviewer-modal.lp` | 55275 | Different | `34d37fdf91086a1e1998f4b477e31557380cfdd42f2df53b59256e9c6047d836` |
| `/modals/parental-modal.lp` | 4379 | Same | `3efd05b29f89eec3bcf159c44c69b14dabaafea79ec1c5f0be9dcedb03d5e954` |
| `/modals/system-config-modal.lp` | 3950 | Different | `b49674db33f01d216bad823b69e1a87bc1d432c34923bbdbb29a11ea3d01d776` |
| `/modals/system-info-modal.lp` | 6090 | Different | `2d9baea4a09f759bfe7e902ba5872d73c4cc257cf7f4ec47e1be17e1f96c2e23` |
| `/modals/time-management-modal.lp` | 3235 | Different | `c3baa0c4a5add8c7452a4f7ad80088063462a3b40b4bcaa1ad6dc42d6e22a11e` |
| `/modals/tod-modal.lp` | 1818 | Same | `a6c207cd7c03b8d5c6064b48ff5885489850bfaa976b425a2e400091130de32c` |
| `/modals/wanservices-modal.lp` | 13146 | Same | `317d4230169c0fb3f6163ba038e280f6f416ec17b7503272ecdf8ab91a8fd2e9` |
| `/modals/wireless-ap-modal-newEM.lp` | 13602 | Same | `a3fb3b1cc563f7b5ccd7e41cd6c0df7ef764e540514384e89e32bdbfa58ae8d2` |
| `/modals/wireless-radio-modal-newEM.lp` | 8270 | Same | `1515669d3c433607f2957f51e6c4291298f714cfbaf61612d208d6487a7ca8f4` |
| `/modals/wireless-wps-modal-newEM.lp` | 4553 | Same | `42b9675f4b48e16a74c93bcaf97a8aa6bde80f69411a7f7a2c0e17051733d5d2` |
| `/password.lp` | 5987 | Same | `f1e2f50e225f0ca93f1c43cb84ae4f9fc85cc72a737441d6761072fa136210f0` |

## Next attack on the problem

Fix and independently test collection fidelity before any fresh acquisition. On the current evidence, inspect exact rendered diagnostics input names and the intact helper request path, then use a single benign authorized action with pre/post logs to distinguish frontend intent from backend execution. For firmware/upload and WPS, first identify the actual server implementation/configuration; retained client strings and M1/descriptor evidence do not resolve those trust boundaries.
