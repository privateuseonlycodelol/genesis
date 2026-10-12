# Wireless QR modal — bare GET fails, contextual GET works — 2026-10-12

Target: owned F1 at `192.168.2.1`, build label `23.1.b`. **Authenticated GET only**; no Print button, no POST, no query fuzzing.

## Result

**VERIFIED:** `GET /modals/wireless-qrcode-modal.lp` with **no** query returns HTTP **500**, **170** bytes, SHA-256 `9e93ecf12d78a8c4c278708706bd249fe086983fb28f82eb880f5c7795043962` (same generic nginx stub as the duplicate-`ipAddress` ping abort).

**VERIFIED:** After `GET /modals/wireless-ap-modal-newEM.lp`, the two `data-remote` QR links from the saved UI pattern work when requested with full query strings:

| Query `iface` | HTTP | Bytes | SHA-256 (body) |
| --- | --- | --- | --- |
| `cred0` (+ `broadcastiface=cred0`, `ispremium=false`, `splitState=1`, `isCompatibility=nil`, `band6gOnly=1`) | 200 | 1,225 | `aad5c144bcb2aab6fe81919052c887f7eb353ba8279ff6a2506251c0e0cc0c4b` |
| `cred1` (same keys, `broadcastiface=cred1`) | 200 | 1,231 | `e08e45ba0db31cb6b013fef0a0420d45c20f03f1cbbbdcc897156698c0914d90` |

Neither response is a login page. Both contain QR modal markup (`modal-header`, `qrcode` identifiers) and **inline script variables** (PSK material is present in the private response bodies; not reproduced here).

**VERIFIED:** Prior grabber **bare-path** and **seed-known-modal** failures (572-byte or 170-byte **500** without query) are explained by **missing query context**, not by a dead route.

**VERIFIED:** `GET /modals/logviewer-modal.lp?process=transformer` immediately before and after (08:50:27 / 08:50:38 local) showed **no** new log rows whose message contains `wireless_qr` or `qrcode` (hashed hit list empty in `result.json`).

## Exploit assessment (this pass)

| Question | Answer |
| --- | --- |
| Unauthenticated QR / PSK leak? | **VERIFIED no:** without admin cookie, contextual and fuzzed GETs return the **5784-byte login HTML** (SHA unchanged across cases). See param pass below. |
| RCE from this GET? | **No** evidence. Failure mode for bare GET is nginx **500** stub, not a shown shell. |
| Parameter fuzz (follow-up same session) | **VERIFIED** — `scripts/f1_qrcode_param_probe.py`. |
| Client `session_key` / Save | Unrelated to this GET-only pass. |

### Parameter fuzz — 2026-10-12 08:52–08:54 local

Artifacts: `artifacts/ui/qrcode-param-20261012T065241Z/` (authenticated), `qrcode-param-20261012T065319Z/` (unauthenticated), `qrcode-xss-check-20261012T065400Z/` (breakout probes).

| Case | HTTP | Notes |
| --- | --- | --- |
| Baseline (six AP keys) | 200 | QR page ~1.2 KiB |
| Bare path | 500 | 170 B stub |
| `iface=cred0` only | 200 | Other keys **not** required on this build |
| `iface=cred99` | 500 | Invalid section |
| Newline / duplicate `iface` | 500 | |
| `isCompatibility=$(printf cred0)` | 200 | Not echoed in body |
| `isCompatibility=<probe>` | 200 | `<probe>` **not** in body |
| `splitState=1;logger genesis-qr-probe` | 200 | Marker echoed only inside `var split_ssid = "…"` as **literal text** (not executed) |
| `band6gOnly=1'` | 200 | QR page |
| `ap=0` (legacy Homeware key) | 200 | Same hash as baseline |
| JS breakout payloads (`";`, `</script>`, …) | 200 | Query values HTML-entity encoded inside JS strings (`&quot;`, `&lt;`, …) — **no** script breakout observed |

**VERIFIED:** admin-only; invalid `iface` → **500**; no shell metacharacter execution; no useful XSS from tested query keys. PSK still only in authenticated QR responses (private bodies).

**Dead end for offensive work on this modal** unless server Lua source for this 23.1.b fork is obtained or a new parameter semantics hypothesis appears. Public `Ansuel/tch-nginx-gui` `wireless-qrcode-modal.lp` uses `iface`+`ap` and builds `wlanconfstr` with escaping; this unit’s live template uses extra keys (`splitState`, `band6gOnly`, …) and inline `var password` — fork differs, but fuzz results still show encoding on reflection.

## Reproduction

```sh
cd scripts && python3 -m unittest test_f1_qrcode_context_probe -v
python3 f1_qrcode_context_probe.py --password-file ../artifacts/secrets/f1-admin.password
```

Private artifacts: `artifacts/ui/qrcode-context-20261012T065019Z/` (`response-*.private`, `result.json`, `summary.json`). Pace: 2 s between requests; no **503**.

## Supersedes

Earlier **HYPOTHESIS** that the QR route might be broken or unreachable: [f1-grab-040001-review.md](f1-grab-040001-review.md), [f1-grab-033853-integrity.md](f1-grab-033853-integrity.md) miss row, [f1-grab-045648-review.md](f1-grab-045648-review.md) bare **500** — those captures lacked the contextual query string.
