# Related-source comparison — 2026-10-12

Scope: offline study of related public code and an extracted-function harness. No code was installed on the F1 and no router settings were changed. This repository contains modified community GUI code; equivalence to Telia 23.1.b is UNKNOWN.

## Provenance

Five files from [Ansuel/tch-nginx-gui](https://github.com/Ansuel/tch-nginx-gui/tree/ecd493c591afd7de47e624245bd1ac1bd9a526a2) were retrieved at commit `ecd493c591afd7de47e624245bd1ac1bd9a526a2` using Python urllib. The public GitHub tree API returned `truncated: false`. Exact URLs, sizes, and SHA-256 hashes are in ignored `artifacts/source-review/manifest.json`; the original downloaded files remain unchanged there. A local check confirmed each file's manifest byte count and SHA-256 and its Git blob SHA-1/size against the pinned tree entry.

## Evidence

**VERIFIED in related source:** [web.lua](https://github.com/Ansuel/tch-nginx-gui/blob/ecd493c591afd7de47e624245bd1ac1bd9a526a2/decompressed/gui_file/usr/lib/lua/web/web.lua#L128) wraps `ngx.req.get_post_args` and invokes the session's CSRF check when a session exists. [session.lua](https://github.com/Ansuel/tch-nginx-gui/blob/ecd493c591afd7de47e624245bd1ac1bd9a526a2/decompressed/gui_file/usr/lib/lua/web/session.lua#L215) calls `ngx.exit(403)` on a mismatched token. This provides a concrete alternative explanation for a rejected POST; it does not diagnose the F1's recorded 403 responses. In the related `web.lua`, the `ngx.exit` wrapper sets `ngx.status=403`, requests `error.lp`, then calls its captured native `ngx.exit(200)`. That source and the mock below do not establish the final wire status or exact response body on the F1.

**VERIFIED by isolated execution:** `lua scripts/test_related_csrf.lua` extracts the actual `checkCSRFtoken` function from the pinned file and runs it with a mocked `ngx`. A matching dummy token succeeds; wrong, missing, boolean, and table tokens call mocked `ngx.exit(403)`. The same harness separately extracts the exact `ngx.exit` wrapper from pinned `web.lua`; for a 403 input it observes `ngx.status=403`, an `error.lp` include request, and a call to captured native `ngx.exit(200)`. Lua version: 5.5.1. The mocks do not determine nginx's final wire status. The harness does not run OpenResty, the surrounding session manager, or a network request, and establishes no live F1 behavior.

**VERIFIED in related source:** [gateway-modal.lp](https://github.com/Ansuel/tch-nginx-gui/blob/ecd493c591afd7de47e624245bd1ac1bd9a526a2/decompressed/gui_file/www/docroot/modals/gateway-modal.lp#L299) dispatches ordinary export through POST body `action=export_config`, and bank size/status through GET query actions. The URI-level multipart `import_config` and `upgradefw` branches return before this handler calls `ngx.req.get_post_args`; the wrapper's CSRF check therefore does not by itself establish CSRF coverage for those branches. Other authorization controls were not assessed. The route is `gateway-modal.lp`, whereas the saved F1 JavaScript targets `system-config-modal.lp`. Similar action names are implementation leads, not interchangeable routes.

**VERIFIED in related source:** the status implementation at lines 250–270 calls `os.remove` on the stored upgrade filename when state is not `Requested`. Export at lines 68–106 sets temporary RPC filename/state, waits for completion, emits a download and clears filename state. Consequently HTTP GET is not sufficient proof of absence of side effects, and export is a user-data read with server-side processing rather than a literally zero-write operation.

**DERIVED:** the safest first live control remains an ordinary authenticated session-status GET observed in the deployed browser flow. Before exercising hidden status/export actions, confirm the current session and the exact intended request semantics. Avoid upgrade-status requests during a pending upgrade; the related source makes cleanup effects a plausible concern. No hidden action was exercised in this pass because tool-side router reachability failed.

## Public management-stack lead

The saved log analysis `findings/f1-logviewer.md` records the path `obuspa_retriever.sh`. The [Broadband Forum OB-USP-Agent repository](https://github.com/BroadbandForum/obuspa) provides public reference implementation source for a USP agent and vendor integration APIs. **REPORTED:** this is a public reference project. **UNKNOWN:** whether the F1 uses that implementation, which version or transports it enables, or whether any management listener is reachable. The script basename alone establishes none of those facts. No USP controller was contacted or simulated.

## Reproduce

```sh
lua scripts/test_related_csrf.lua
python3 -m json.tool artifacts/source-review/manifest.json
```

The first command prints only synthetic control outcomes. The second prints public-source provenance. No credentials, cookies, private keys, or device identifiers are included in these artifacts.
