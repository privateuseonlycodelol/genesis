# F1 grabber — CSRF redaction corrupted JavaScript (fixed)

**When:** 2026-10-12  
**Component:** `scripts/f1-grab-artifacts.user.js` (Tampermonkey), versions **≤ 1.3.3**  
**Firmware:** Not implicated — corruption is from client-side storage, not a router change.

## What happened

**VERIFIED (user analysis):** For HTTP 200 responses, the grabber applied CSRF redaction to **all** bodies, including `/js/*.js`. The HTML-only meta tag rule is safe on `.lp` pages. A second global rule matched `CSRFtoken` patterns inside minified JavaScript and replaced substrings with `REDACTED`, breaking expressions. At least **six** JS files in a grab zip match the pre-grab artifacts **only after** applying that same redaction rule; intact copies match earlier saves under `artifacts/ui/` (e.g. from HAR extraction).

**VERIFIED (code, pre-1.3.4):** `const body = res.status === 200 ? redact(res.body) : …` with no path check.

**Not a firmware claim:** Byte differences between a damaged grab zip and `artifacts/ui/*.js` are explained by this bug, not by a new 23.1.b build.

## Affected artifact types

| Type | Redaction in ≤1.3.3 | Should redact? |
|------|---------------------|----------------|
| `/modals/*.lp`, shell `.lp` HTML | Yes | Yes (CSRF meta only) |
| `/js/*.js` | Yes (bug) | **No** — store verbatim |
| `/css/*`, `/ajax/*.lua` | Yes if 200 (bug) | **No** |

`main-min.js` was especially visible (large file, many `CSRFtoken` string occurrences in bundled code).

## Fix history

| Version | Behavior |
|---------|----------|
| **1.3.4** | Redact CSRF **meta** on `.lp`/`.html` only; JS stored verbatim. |
| **1.5.1** | **No body tampering** — all GET bodies and traffic-tap POST bodies stored **verbatim** (integrity over sanitization). Zips may contain live CSRF tokens and form secrets; keep gitignored. The [04:56:48Z finished grab](f1-grab-045648-review.md) has `REDACTED` count 0 across all bodies and is the reference verbatim package after this fix. |

Intermediate **1.5.0** traffic tap still redacted POST bodies in `TRAFFIC.jsonl`; use **1.5.1+** for faithful traffic logs.

## Recovery

1. Update the userscript to **1.5.1** or newer.
2. **Delete saved results** in the grabber panel (or clear IndexedDB `genesis-f1-grab`) so corrupted or redacted copies are not re-exported.
3. Re-**Run** / download zip, **or** copy known-good JS from `artifacts/ui/` / earlier HAR extracts for audit work.

## Evidence to record (user)

Document per file when verifying:

| Path | SHA-256 (intact reference) | SHA-256 (corrupted grab) | Notes |
|------|---------------------------|--------------------------|--------|
| `/js/main-min.js` | (from `artifacts/ui/main-min.js`) | (from bad zip) | |
| (other five JS) | | | |

Recompute: `shasum -a 256` on both copies; optional confirm with `python3 -c` applying `redactHtmlCsrf` only vs old `redact` on intact file.

## Related

- [`docs/f1-artifact-grabber.md`](../docs/f1-artifact-grabber.md)
- [`docs/f1-javascript-audit.md`](../docs/f1-javascript-audit.md) — audit inputs must be uncorrupted JS
