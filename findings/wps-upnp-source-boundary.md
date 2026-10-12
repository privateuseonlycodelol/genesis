# WPS UPnP source boundary

Date: 2026-10-12

## Result and provenance

**VERIFIED: pinned Android upstream source snapshot.** The requested prefix `d7ff03d` resolves through Android Gitiles to commit `d7ff03d48f825360eec2a371e3361306f2fd721b` in `platform/external/wpa_supplicant_8` (tree `cab90712e598af945b8592dd4498e8bcfee77531`). Commit-log and root-tree JSON, the four initially requested files, and four supporting WPS source files are preserved under the ignored local directory `artifacts/management/wps-source/`. `manifest.json` records each retrieval URL, SHA-256, byte count, and Git blob ID.

The decoded files were re-hashed locally and matched the manifest. Running `git hash-object` independently reproduced the four initially fetched Git blob IDs, including `wps_upnp_web.c` blob `7548e8432a68fd5c85b598527fb27e0be0c5ff8e`. The files and manifest are covered by the repository's `artifacts/` ignore rule.

Initial normal-sandbox Gitiles requests failed DNS resolution, and the interim w1.fi documentation fallback did not provide the requested revision. After the parent authorized an escalated fetch of public source, the exact Gitiles snapshot was retrieved successfully. The interim fallback is superseded and is not used for the observations below.

## Observations in the pinned source

**GetDeviceInfo dispatch and AP-PIN prerequisite — VERIFIED in this source revision.** The HTTP POST handler accepts the `wps_control` path and obtains the action from `SOAPAction` (`wps_upnp_web.c:918-943`). It dispatches `GetDeviceInfo` to `web_process_get_device_info` (`:942-943`); HTTP POST requests reach this handler at `:1367-1373`. The action takes the first configured interface (`:431-432`) and returns an internal-server-error result when there is no interface or `iface->ctx->ap_pin` is null (`:436-437`). Thus this code has an explicit AP-PIN prerequisite for the action.

On the successful path it allocates a peer, zero-initializes `cfg`, sets `cfg.wps` to the interface's long-lived WPS context and sets `cfg.pin`/`cfg.pin_len` from the AP PIN (`wps_upnp_web.c:439-455`). It calls `wps_init`, then `wps_get_msg` on that per-peer context (`:455-468`). The handler's comment identifies DeviceInfo as M1 data and describes the AP acting as an Enrollee (`:443-448`). `wps_init` copies `cfg->registrar` and sets its initial state to `RECV_M1` only when that pointer is non-null; otherwise it sets `SEND_M1` (`wps.c:35-46,101`). Since the handler zero-initializes `cfg` and does not set `registrar`, this call starts in `SEND_M1`. `wps_enrollee_get_msg` builds M1 for that state (`wps_enrollee.c:447-455`); the builder emits its attributes and advances the state to `RECV_M2` on success (`:104-162`).

**M1 field values and lengths — VERIFIED in the pinned source.** `wps_defs.h` assigns `ATTR_VERSION=0x104a` (`:117`), `ATTR_MSG_TYPE=0x1022` (`:81`), `ATTR_ENROLLEE_NONCE=0x101a` (`:73`), and `ATTR_PUBLIC_KEY=0x1032` (`:94`); `WPS_M1=0x04` (`:166-172`) and `WPS_NONCE_LEN=16` (`:28-30`). The builder emits the legacy Version attribute with a one-byte value `0x10` (`wps_attr_build.c:188-201`), and emits Message Type with a one-byte value (`:264-270`). It emits the enrollee nonce with `WPS_NONCE_LEN` bytes (`:274-280`). For this GetDeviceInfo configuration, the zeroed config leaves `dev_pw_id` at its default zero value; the public-key builder therefore generates a DH5 public key, zero-pads it to 192 bytes, and records that value length in the Public Key attribute (`wps.c:35-41,48-56`; `wps_attr_build.c:21-23,65-82`; `wps_defs.h:25-29,155-163`). These four attributes have TLV wire sizes of 5, 5, 20, and 196 bytes respectively, counting the four-byte type/length header.

**HTTP Authorization/Cookie check — no explicit check found in the inspected files.** A case-insensitive search of all four preserved files found no `Authorization` or `Cookie` references. The POST-handler comment says other header lines are ignored (`wps_upnp_web.c:900-918`), and its action parser reads `SOAPAction` (`:861-897`). This supports the narrow conclusion that these WPS UPnP files show no explicit HTTP Authorization/Cookie gate on this handler path. The generic HTTP parser, other call layers, and the F1's shipped implementation were not inspected here, so this is not a complete claim about every layer or about the device.

**Per-peer state, expiry, and cleanup — VERIFIED in the inspected files.** A successful GetDeviceInfo action keeps the peer context in the interface's `peers` list (`wps_upnp_web.c:471-484`). If the list length is greater than three before insertion, it removes the oldest peer, deinitializes its WPS context, and frees it (`:413-419`, `:471-480`). The code at `:481` records a possible peer timeout as TODO; no per-peer timer is installed in this handler. `PutMessage` parses `NewInMessage`, looks for an active peer using the enrollee/registrar nonces, falls back to the first peer if no match is found, processes the WPS message, and gets the next WPS response (`:488-569`). A `WPS_FAILURE` removes the peer (`:557-564`). Interface/device deinitialization drains the peer list and deinitializes/frees each peer (`wps_upnp.c:1082-1122`). Therefore these files show cleanup on failure, list pressure, and teardown, but no individual peer-session expiry mechanism in the GetDeviceInfo path.

The subscription timeout is separate state: `wps_upnp_i.h:20-23` defines 1801 seconds; subscription start sets that expiry and ages expired subscriptions (`wps_upnp.c:692-722`), and renewal resets it (`:757-771`). This timer concerns UPnP event subscriptions, not the WPS peer contexts above.

**Other action entry points.** The POST dispatch also routes `PutMessage`, `PutWLANResponse`, and `SetSelectedRegistrar` (`wps_upnp_web.c:944-951`). SetSelectedRegistrar first resolves an external registrar from the client address and rejects an unknown registrar before decoding its message (`:687-718`). These observations are limited to direct source behavior; no action was invoked and no exploit chain was investigated.

**Static service-description comparison — byte-identical.** The `wps_scpd_xml` C string in `wps_upnp_web.c:45-149` was decoded by concatenating its C string literals. That result and the saved local `artifacts/logs/software-pass-ssdp/service-description.private.xml` are both 2,469 bytes with SHA-256 `093f458cc0f7bfa8998d7b052e133cbdf7bc3fdabeed9a2644723842afc54ed4`; a direct byte comparison returned equal. This establishes that the saved descriptor matches this pinned source's static descriptor bytes. It does not establish that the F1 runs this exact source revision or implementation.

## Primary-source links and local evidence

All links below pin the full commit:

- [Commit metadata](https://android.googlesource.com/platform/external/wpa_supplicant_8/+log/d7ff03d?format=JSON) and [root tree](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/?format=JSON).
- [`wps_upnp_web.c`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_upnp_web.c?format=TEXT): dispatch, GetDeviceInfo, peer lifecycle, and action handling.
- [`wps_upnp.c`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_upnp.c?format=TEXT): subscription lifetime and device/interface teardown.
- [`wps_upnp_i.h`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_upnp_i.h?format=TEXT): interface peer list and subscription structures.
- [`wps_enrollee.c`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_enrollee.c?format=TEXT): enrollee message selection and M1 construction.
- [`wps_defs.h`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_defs.h?format=TEXT): attribute identifiers, message-type values, and WPS length constants.
- [`wps.c`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps.c?format=TEXT): per-session state initialization.
- [`wps_attr_build.c`](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/d7ff03d48f825360eec2a371e3361306f2fd721b/src/wps/wps_attr_build.c?format=TEXT): M1 field encoding and lengths.
- Local snapshots and checksums: `artifacts/management/wps-source/manifest.json` and the four source files in that directory.

## Limitations

This is generic Android upstream source at the pinned commit, not proof that the Telia F1 firmware `23.1.b.0448-7241017-20260223134332` ships or reaches this exact code. No live-device requests, action invocations, tests, or test-design work were performed. The next source-side evidence needed before applying these observations to the F1 is confirmation that its firmware contains this revision or matching code; otherwise the findings remain upstream behavior only.
