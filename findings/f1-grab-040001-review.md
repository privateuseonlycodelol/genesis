# F1 04:00:01 grab — what improved and what is worth pursuing

Date: 2026-10-12. Offline comparison of the user-supplied `f1-grab-2026-10-12T04-00-01-055Z.zip` against the earlier `03:38:53.121Z` archive and intact local references. Three GPT-6 Luna agents at xhigh independently reviewed fidelity, coverage, and runtime deltas. The parent checked the consequential results, corrected an attempted timestamp correlation, and added a tested reusable comparison tool. Embedded documents were treated as source evidence, not instructions. No router request or replay was performed during this pass.

**Superseded for coverage by:** [`f1-grab-045648-review.md`](f1-grab-045648-review.md) (finished 04:56:48Z grab with full modal set, GET JSON, and verbatim bytes). This 04:00 archive remains the paired reference when you need the script-repair delta against 03:38 without merging provenance.

## Decision

**Yes: this is a materially better JavaScript package, with a useful newer runtime window. It is not a more complete UI harvest or a new application-code version.** Keep both archives: the newer one restores all six damaged scripts; the older one retains seven page bodies that this package leaves queued. Combining them without preserving per-file provenance would obscure their different capture states.

The worthwhile work was a focused delta review: confirm the script repair, reconcile missing pages against the queue, inspect the changed runtime pages, and follow a concrete QR-handler traceback. Repeating all earlier cryptographic derivations or broad endpoint guesses would add little because every new JavaScript body exactly matches an intact reference already held locally.

## Evidence found

| Measurement | Earlier 03:38 package | New 04:00 package | Interpretation |
| --- | ---: | ---: | --- |
| ZIP members | 65 | 58 | New package is smaller |
| Saved response bodies | 62 | 55 | Seven earlier bodies absent; all seven are queued, not recorded as failures |
| HTML / JavaScript / CSS | 35 / 24 / 3 | 28 / 24 / 3 | HTML breadth decreased; JS/CSS count unchanged |
| JavaScript syntax passes | 18 of 24 | 24 of 24 | Six damaged scripts repaired |
| JS matching intact earlier Downloads copies | 18 of 24 | 24 of 24 | No unexplained new code changes |
| Recorded hits / misses | 63 / 80 | 56 / 24 | Does not establish number of actual network requests or improved server responses |
| Miss status distribution | 79 × 404; 1 × 500 | 23 × 404; 1 × 500 | No earlier miss became a hit; QR 500 persists |
| Queue entries already represented in results | 86 of 152 | 0 of 87 | New queue has cleaner accounting |
| Recorded hit hashes | All blank | All blank | Hashes still need computing from saved bytes |
| Saved log rows | 132 | 135 | Different, non-overlapping rolling windows |

**VERIFIED — code fidelity.** The changed scripts are `ethernet-min.js`, `internet-routed-settings-min.js`, `main-min.js`, `password.js`, `srp-min.js`, and `system-config-min.js`. Their new bytes equal the intact earlier references. The other 18 scripts are unchanged. Node syntax checks parse without executing application code. This validates the new saved code bytes; it does not identify the package's producer version, prove a new HTTP acquisition, or demonstrate a firmware change. Four saved HTML CSRF metas are still redacted, so the package is not wholly untouched wire evidence. See [fidelity checks](f1-grab-040001-fidelity.md).

**VERIFIED — coverage.** No new body member or newly completed route appears. All seven earlier missing bodies—the six guided Wi-Fi fragments and `internet-dhcp-routed.lp`—are explicitly queued with no new miss record. Fifty-six old 404 records are simply absent from the new result set; none changed to 200. All 24 retained miss routes retain their earlier status. The new ZIP has only the legacy INDEX/MISSES/LEADS reports: no HAR, traffic JSONL, response headers, backend source, or firmware image. See [coverage reconciliation](f1-grab-040001-coverage.md).

**VERIFIED — later runtime evidence.** The new log contains 135 timestamped rows for 05:48:55–05:58:47, compared with 05:17:14–05:27:01 previously. It contains 60 unauthorized session-status messages, recurring cron launches, one `ipping_helper` launch, and nginx errors. Absence of the earlier missing-CSRF messages in this different window does not establish that the checks disappeared. Changed HTML principally records diagnostics/network/time state; form/action and link-target fingerprints remain unchanged across all eight changed common HTML pages. See the log sections in [03:38:53 runtime](f1-grab-033853-runtime.md) and the newer window in [04:56:48 grab](f1-grab-045648-review.md) (log stamps 06:33–06:47, `wireless_qr.lua:48` traceback).

## The useful new lead: QR handler context and failure

**VERIFIED as saved log text:** the new log names `/www/lua/wireless_qr.lua:48`, reports `attempt to index local 'password' (a nil value)`, and shows a stack through `format`, the QR template's `content`, `/usr/lib/lua/web/web.lua:249` (`process`), and `content_by_lua(nginx.conf:123):4`. This is substantially more specific implementation evidence than a generic 500 body. It does not provide the Lua source, the value of a password, authentication bypass, or code execution.

**Important timing limit:** the error groups occur at 05:49:09 and 05:57:30. The new miss record's timestamp is `03:59:09.957Z`, or approximately 05:59:09 Stockholm time—after the saved log window ends. Thus those traces are earlier failures of the same QR route; they cannot be assigned as the traceback for this particular saved 500. A fitted 1-hour-50-minute offset was rejected during review because no independent clock evidence supported it.

**VERIFIED — caller mismatch:** the AP HTML's QR `data-remote` links supply query keys `band6gOnly`, `broadcastiface`, `iface`, `isCompatibility`, `ispremium`, and `splitState`. The new failed probe is the bare route without those keys. The collector did not demonstrate the browser's actual contextual request. Local related-source searches did not find `wireless_qr.lua` or its LP template.

**HYPOTHESIS A:** omitted interface/security context sends the handler down a path with no password object. **HYPOTHESIS B:** a legitimate missing configuration value, unsupported security mode, or independent template defect leaves that object nil even with normal context. The captured stack cannot choose between them. Query keys visible in the UI are not proof that every key is required. The discriminating test is the exact UI-generated contextual request versus the bare request, with contemporaneous response and log capture; inspection of matching handler source would be better if it becomes available. Neither request was sent in this pass.

## Work performed and validation

- Independently reconciled both ZIPs, raw body hashes, result ledgers, and queue states. Python ZIP CRC checks and system `unzip -t` pass; system `shasum` matches the new archive SHA-256 `4a341890d9cbddd55491ff2a127cb78995cb8ecc8569afbf95f1280919e9a675`.
- Parsed all 24 new scripts with Node; all pass and all match intact references. Re-ran the fidelity helper and checked its value-free output.
- Independently parsed the new log and reviewed the agent's second extraction. Counted the later window without treating traceback rows as separate independent failures.
- Reviewed the eight changed common HTML pages and contextual QR links without reproducing collected secrets.
- Added [archive comparison tool](../scripts/compare_f1_grabs.py) and [four regression tests](../scripts/test_compare_f1_grabs.py). The tests distinguish changed body bytes from changed HTTP outcomes; omitted-but-queued pages from 404s; miss-to-hit transitions from newly observed routes; and unchanged errors from new successes. All four pass. The earlier archive auditor's four tests also pass.

Reproduce the metadata-only archive comparison:

```sh
python3 scripts/compare_f1_grabs.py \
  ~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip \
  ~/Downloads/f1-grab-2026-10-12T04-00-01-055Z.zip \
  > artifacts/ui-grab-20261012T040001Z/comparison.private.json
python3 scripts/test_compare_f1_grabs.py
python3 scripts/test_audit_f1_grab.py
```

Original archives remain unchanged. Private extraction, parser outputs, and helper scripts are under ignored `artifacts/ui-grab-20261012T040001Z/` (directory mode 0700). Existing collector edits were preserved; this pass did not modify the collector or create a commit.

## What changed and next attack on the problem

Use the new ZIP's restored JavaScript for source analysis, with its recorded hashes. The seven HTML bodies that were queued here were later collected in the [04:56:48Z grab](f1-grab-045648-review.md); keep both archives if you care about provenance timestamps. The earlier client-crypto findings remain applicable because the source bytes match; no new OSCK, root access, firmware/update image, decrypted configuration, or exploit was demonstrated.

The next useful collection is a narrow faithful request/response capture of the actual contextual QR request—or matching server source—not another broad crawl of the same bundle. Preserve `data-remote` context and query parameters privately, and capture logs at the same time so a response can be tied to its own trace. More generally, actual action/refresh responses remain more valuable than additional guessed modal filenames now that the saved JS is intact. The separate [controlled TRACE/PING pass](f1-trace-path-2026-10-12.md) already addresses the basic PING/helper association; this archive does not justify repeating that experiment as though it were still untested.
