# F1 grab 04:00:01 — fidelity and delta review

For the finished verbatim harvest (HTML, GET JSON, guest LAN, IPv6 DHCP modal), see [`f1-grab-045648-review.md`](f1-grab-045648-review.md). This note stays focused on script repair versus the damaged 03:38 package.

Date: 2026-10-12. Scope: offline comparison of the supplied ZIP with the 03:38 ZIP and previously saved JavaScript references. No router requests, page execution, or replay. ZIP originals were left unchanged; HTML field values were never printed.

## Result

The new ZIP is **better for JavaScript fidelity**: all 24 scripts parse with Node and match the separately saved unsuffixed Downloads copies byte-for-byte. This restores the six scripts corrupted in the prior ZIP. It contains no JavaScript change beyond that repair: 18 scripts are unchanged from the prior ZIP, and the six differences equal the intact references. This establishes archive-to-reference equality, not a new live acquisition, producer version, or firmware change.

The package has **less body coverage** than the 03:38 ZIP: 55 bodies versus 62, with zero added and seven removed. Among 28 HTML pages present in both packages, eight differ byte-for-byte. The new index still has 87 queued paths; queued entries are not evidence of completed requests.

## Integrity and inventory

- New original: `~/Downloads/f1-grab-2026-10-12T04-00-01-055Z.zip`; SHA-256 `4a341890d9cbddd55491ff2a127cb78995cb8ecc8569afbf95f1280919e9a675`.
- Prior original: `~/Downloads/f1-grab-2026-10-12T03-38-53-121Z.zip`; SHA-256 `cc7af29a6f59f08a9350d1ad14265bbff243be373af3b56ef7170198f0f3a525`.
- **VERIFIED:** new ZIP has 58 members (55 bodies plus three Markdown inventory files); Python ZIP CRC verification and `unzip -t` pass. Bodies comprise 24 JavaScript, 28 HTML, and 3 CSS files.
- **VERIFIED:** INDEX reports 56 hits, 24 misses (23 HTTP 404 and one HTTP 500), and 87 queued entries. All 56 hit hash cells are blank. One reported hit has length zero and no body; all other hits have a saved body whose JavaScript UTF-16 length equals the declared length.
- **VERIFIED:** seven old bodies are absent from the new package; no body is new. The `INDEX.md` and `MISSES.md` reports differ; `LEADS.md` does not.

## JavaScript repair

Node `v26.5.0 --check` passes for all 24 new scripts. The same check passes for only 18 scripts in the previous ZIP; the six prior failures are `ethernet-min.js`, `internet-routed-settings-min.js`, `main-min.js`, `password.js`, `srp-min.js`, and `system-config-min.js`. For every one of the 24 routes, new ZIP bytes equal the unsuffixed earlier Downloads file. All 18 previously intact ZIP scripts still match; the six changed ZIP members now match their raw earlier references. No unexplained script difference remains.

The new ZIP has no producer-version proof; the concurrently edited collector in the workspace cannot retroactively identify its producer. Four HTML CSRF meta values remain the literal redaction marker, so the package is not wholly verbatim. Its body hashes do not establish which collector version created it.

## HTML and sensitivity delta

Counts below are from a value-free parser; no HTML input or token values are included in this finding or its private machine output.

| Saved HTML property | 03:38 ZIP | 04:00 ZIP |
| --- | ---: | ---: |
| HTML pages | 35 | 28 |
| CSRF meta absent | 31 | 24 |
| CSRF meta redacted | 4 | 4 |
| CSRF meta populated | 0 | 0 |
| Password/key-like input fields detected by type/name | 18 | 12 |
| Such fields with a non-empty `value` attribute | 6 | 4 |

On the eight changed common HTML pages, form-action, script-source, and link-target fingerprints are unchanged on all eight. Six retain the same element/attribute-name sequence; six retain the same inline script bodies; seven retain the same input names, types, and value fingerprints. These comparisons narrow the changes to saved page state/markup but do not establish their server-side cause. The value-free scan found four non-empty values among password/key-like input fields in the new archive; their identity and meaning were not inspected or reproduced. Keep the archive private and ignored.

## Reproduction and next step

The reproducible helper and machine output are private under `artifacts/ui-grab-20261012T040001Z/fidelity-review/`. Run `python3 artifacts/ui-grab-20261012T040001Z/fidelity-review/review.py`; it reports hashes, counts, parse results, and value-free HTML fingerprints only. Environment: Python 3.14.7, Node v26.5.0. Additional archive check: `unzip -t ~/Downloads/f1-grab-2026-10-12T04-00-01-055Z.zip`.

**Follow-up assessment:** no broad subagent audit is justified by this ZIP alone: the repaired JavaScript exactly duplicates intact local references already used in the earlier auth/crypto finding, and endpoint/code coverage did not grow. If pursuing this package, first compare only the few HTML snapshots whose structure or inline-script fingerprints changed; delegate further work only if that reveals a new control or behavior. The largest evidence gap remains server handlers or a controlled server-side observation, not more parallel reads of the same client bundle.
