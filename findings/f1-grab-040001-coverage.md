# F1 grab 04:00:01 — coverage delta and collector evidence

Date: 2026-10-12. Scope: offline comparison of `artifacts/ui-grab-20261012T040001Z/` with `artifacts/ui-grab-20261012T033853Z/`, the earlier integrity finding, the UI-surfaces finding, the grabber documentation, and the current userscript source. No router requests or HAR replay were performed.

## Evidence found

- **VERIFIED:** the 04:00 archive audit records 58 ZIP members: 55 non-empty bodies, three Markdown reports, and one 200 hit with an empty body (`/ajax/wirelesscard.lua`). The 03:38 archive has 65 members: 62 non-empty bodies, three reports, and the same empty hit. Both audits report matching declared body lengths, no unexpected bodies, and passing CRC checks. The 04:00 INDEX has 56 hit rows, 24 miss rows, and 87 unique queued paths; its queue has no path that also has a terminal result in that archive. All 56 hit hash cells are blank, so the package does not independently tie its saved bytes to response hashes.
- **VERIFIED:** there are no new successful routes among the old archive’s 80 miss identities. The 24 new miss rows are the same 24 route/status pairs already recorded before: 23 HTTP 404s and the QR modal’s HTTP 500. Thus the drop from 80 misses to 24 is not a set of 56 newly successful requests.
- **VERIFIED:** 35 old HTTP 404 identities now appear in the queue with no result row. Their queue methods are 21 `guess-js-to-modal`, 10 `guess-modal-to-js`, three `guess-modal-stem-min`, and one `chase-regex-lp`. Another 21 old 404 identities appear neither as a new hit, miss, nor queued route: four `/js/*.lp` source-location artifacts and 17 `/modals/modals/*.lp` duplicate-directory artifacts. These absences remove known noisy negatives from this package, but they are not successful route observations.
- **VERIFIED:** all seven bodies that were 200 in the 03:38 archive but are missing from the 04:00 `files/` directory are explicitly queued, not recorded as failed:

  | Previously successful route | 04:00 queue provenance |
  | --- | --- |
  | `/modals/basicview-wifiguest-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/basicview-wifiguest5GHz-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/basicview-wifipsk-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/basicview-wifipsk5GHz-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/basicview-wifissid-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/basicview-wifissid5GHz-modal.lp` | `chase-regex-modal` from `/modals/basicview-accesscode-modal.lp` |
  | `/modals/internet-dhcp-routed.lp` | `chase-regex-lp` from `/modals/internet-modal.lp` |

- **VERIFIED:** `/modals/wireless-qrcode-modal.lp` remains an HTTP 500 miss in both archives. The new report calls it `seed-known-modal`; the older report called it `chase-regex-lp`. Both rows record 572 bytes and `http-500`. The saved AP modal in each archive has two `data-remote` references to the QR route with the same six query-key names: `band6gOnly`, `broadcastiface`, `iface`, `isCompatibility`, `ispremium`, and `splitState`. The miss row is for the bare seeded path, with no query string. No parameter values are reproduced here.
- **DERIVED:** the bare-path 500 does not test the AP UI’s contextual URL. In the current userscript, the HTML chase selector omits `data-remote`, the `.lp` regex resolves only the path portion, and `requestKeyFromString()` preserves only a small allowlist of action/session query keys. That is consistent with a missing-context explanation for the QR error, but no query-bearing GET or normal QR body was captured, so the cause remains **HYPOTHESIS**.
- **UNKNOWN:** a recursive filename search found no local `wireless_qr.lua` or other QR-named source/template in this checkout; it found only the two archived QR JavaScript files. The reported runtime source location therefore remains an external-to-this-checkout lead, not evidence from local firmware/source. The AP modal HTML is the only local server-template evidence related to the QR route.
- **VERIFIED:** the new package contains only `INDEX.md`, `MISSES.md`, `LEADS.md`, and body files. It has no `TRAFFIC.md`, `TRAFFIC.jsonl`, HAR, `OUTCOMES.md`, `FORMS.md`, or `PATH-LITERALS.md`. It therefore adds no browser request/response trace evidence. “Trace Route” and action name `TRACE` appear in the diagnostics UI source, but there is no recorded traceroute operation or result.
- **VERIFIED:** `/js/asmcrypto-min.js` contains the directive `//# sourceMappingURL=asmcrypto.js.map`. No `.map` body or `.map` hit, miss, or queued row is present in the archive. The current collector’s `isWanted()` and path-literal extractor do not accept `.map`, so this is a concrete undiscovered static-artifact lead, not a collected map.

## Work performed

Compared the two INDEX and MISSES route identities and statuses against their queue sections and audit summaries; checked the seven missing body filenames against the new queue; reviewed the relevant source functions (`resolveLp`, `requestKeyFromString`, `isWanted`, `isTerminalCached`, `pruneQueue`, `ensureCacheGeneration`, `processQueue`, and `downloadPackage`); and searched the 04:00 saved bodies for source-map and trace evidence. The existing audit and comparison summaries are in `artifacts/ui-grab-20261012T040001Z/audit.private.json` and `artifacts/ui-grab-20261012T040001Z/comparison.private.json`. These are offline archive checks, not live-device verification.

## What changed

- **DERIVED:** the seven omitted old bodies are pending collection, not failed routes. The new archive is less complete on these known surfaces even though it has fewer miss rows.
- **DERIVED:** the remaining 56 old miss identities divide into 35 still queued and 21 dropped from the report entirely. The four `/js/*.lp` false paths are consistent with the current `resolveLp()` site-root correction. The current parser still resolves HTML attributes with `requestKeyFromString()` against the source file path, however, so the absence of the 17 doubled `/modals/modals/` paths cannot be credited to a generally fixed relative-attribute resolver from this archive alone.
- **UNKNOWN:** the archive does not identify which userscript version produced it. The current worktree has an uncommitted v1.6.1 grabber with a 250-new-GET per-run limit; the checked-in base is v1.3.0 with an 80-new-GET limit. The 04:00 package has the older three-report shape, while current `downloadPackage()` emits additional reports. Its 80 stored outcomes (56 hits + 24 misses) happen to equal the old per-run cap, but INDEX/MISSES package persistent cache rows, not a per-run request log; the count cannot prove that exactly 80 GETs occurred. The archive also has no `lastSession` record or code fingerprint to connect it to the current source.
- **HYPOTHESIS:** the current source’s `CAPTURE_FORMAT` migration clears cached records but retains the IndexedDB queue. That can leave paths queued after a format change; it is one plausible explanation for queue/cache differences, but the archive does not establish that this migration produced the 04:00 package.

## Next attack on the problem

The historical collection gaps should be checked against subsequent evidence before more requests are made. All seven queued pages were recovered in the later package below. The source-map directive is a collector-discovery limitation, but earlier saved nginx logs already record missing `/js/asmcrypto.js.map` files ([03:38 runtime](f1-grab-033853-runtime.md)); repeating the same URL without a changed source or acquisition hypothesis has low value. The parent independently parsed both AP bodies to confirm contextual `data-remote` query keys. Preserve a producer-version fingerprint and per-run request count in future packages. For a new backend question, a contemporaneous request/response trace or matching server source would add more than another broad crawl.

**Update (same day):** the [04:56:48Z finished grab](f1-grab-045648-review.md) retrieved all seven queued bodies plus `internet-dhcpv6-routed.lp`, `GET /ajax/wirelesscard.lua?auto_update=true` JSON, `GET …?intf=guest`, and `GET …?getNTP=true`. The seven-body gap described here is closed in that package; the bare QR route remains HTTP 500.


**Subsequent QR resolution:** [contextual QR controls](f1-wireless-qrcode-context-2026-10-12.md) record bare GET 500, contextual GET 200, and `iface=cred0` alone 200. The missing-context explanation is now supported by separate live controls; it was only a hypothesis in this archive. No device request was made during this comparison pass.
