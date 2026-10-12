# Offline service-description and related-source evidence

Status: **VERIFIED as local file contents only.** This records fields extracted from the named XML files and literal code behavior in the two source-review files. It does not establish that these files match a shipped F1 build or the live device.

## Inputs and provenance

| Input | SHA-256 |
|---|---|
| `artifacts/logs/software-pass-ssdp/device-description.private.xml` | `16c380ac7ffe8e5699b0bb1de6b9a9ee1b492fa58eaa98fedc91c116330508e2` |
| `artifacts/logs/software-pass-ssdp/service-description.private.xml` | `093f458cc0f7bfa8998d7b052e133cbdf7bc3fdabeed9a2644723842afc54ed4` |
| `artifacts/source-review/nginx.conf` | `2bdb60b4f544dc7c34304022eb47b53f052a38cd09e0d61713258b5fab235c60` |
| `artifacts/source-review/session.lua` | `9f5639c21c8f93d097e817e961a3462d2b29f1f19f4220d65dbf59135d5779ea` |

## XML fields

`device-description.private.xml` contains one service entry:

| Service type | controlURL | eventSubURL | SCPDURL |
|---|---|---|---|
| `urn:schemas-wifialliance-org:service:WFAWLANConfig:1` | `wps_control` | `wps_event` | `wps_scpd.xml` |

`service-description.private.xml` contains these actions and arguments:

| Action | Argument name | Direction | Related state variable |
|---|---|---|---|
| `GetDeviceInfo` | `NewDeviceInfo` | `out` | `DeviceInfo` |
| `PutMessage` | `NewInMessage` | `in` | `InMessage` |
| `PutMessage` | `NewOutMessage` | `out` | `OutMessage` |
| `PutWLANResponse` | `NewMessage` | `in` | `Message` |
| `PutWLANResponse` | `NewWLANEventType` | `in` | `WLANEventType` |
| `PutWLANResponse` | `NewWLANEventMAC` | `in` | `WLANEventMAC` |
| `SetSelectedRegistrar` | `NewMessage` | `in` | `Message` |

State variables and the `allowedValueRange` result from the XML:

| Name | dataType | sendEvents | allowed-value range |
|---|---|---|---|
| `Message` | `bin.base64` | `no` | none present |
| `InMessage` | `bin.base64` | `no` | none present |
| `OutMessage` | `bin.base64` | `no` | none present |
| `DeviceInfo` | `bin.base64` | `no` | none present |
| `APStatus` | `ui1` | `yes` | none present |
| `STAStatus` | `ui1` | `yes` | none present |
| `WLANEvent` | `bin.base64` | `yes` | none present |
| `WLANEventType` | `ui1` | `no` | none present |
| `WLANEventMAC` | `string` | `no` | none present |
| `WLANResponse` | `bin.base64` | `no` | none present |

No state variable in this file has an `allowedValueRange` element. This extraction omits `allowedValueList` contents and all other XML fields.

No action-argument or state-variable name in this XML explicitly names authentication, a user, a password, credentials, a token, or login. This is a name-only observation; it does not establish that the opaque message payloads contain no authentication semantics.

## Related-source inspection

These observations describe only the related-source snapshots in `artifacts/source-review/`, not F1 implementation or effective runtime configuration.

### `artifacts/source-review/nginx.conf`

- Literal listeners: IPv4 ports 80, 443 (SSL), and 8443 (SSL), lines 39–41; IPv6 equivalents, lines 43–45; loopback `127.0.0.1:55555`, line 129; and IPv4/IPv6 port 8080 with `tproxy`, lines 198–200.
- The catch-all `location ^~ /` block at lines 93–109 runs `web.assistance.enable()`, obtains the session manager, calls `checkrequest(true)` when the `auto_update` query argument is exactly `"true"` and otherwise calls `checkrequest()`, then calls `handleAuth()` before the content handler (lines 94–108).
- Exact `location = /api` at lines 111–122 sets 64 KiB request limits, calls `webservice.accesscontrol_token.authenticate()`, and passes its returned role to `webservice.api.process(role)` (lines 116–120).
- The loopback server defines `/ra` with `web.assistance.enable()` in its access phase and handles query arguments in its content phase (lines 133–182). `/reloadWebUsers` calls `sessioncontrol.reloadUsers()` (lines 184–188); `/api/reload` calls `accesscontrol_token.reload_config()` (lines 189–193).
- The 8080 `tproxy` server invokes `web.intercept.process()` in its access phase (lines 198–206).
- The file includes `ui_server.conf`, `main_*.conf`, and `server_*.conf` at lines 62, 125, and 209, respectively. Those included files were not inspected here, so these literals do not establish the complete effective configuration.

### `artifacts/source-review/session.lua`

- No cookie parsing code or cookie reference was found in this file by case-insensitive text search. Each `generateRandom()` call reads 32 bytes from the open `/dev/urandom` handle (lines 14–21). `generateNewIdentity()` calls that function separately for `sessionid` and `CSRFtoken` (lines 91–94), so each field is assigned from a separate read; these lines do not show cookie transport or parsing.
- The fallback user has an empty role (lines 27–40); `getrole()` returns the current/fallback user's role (lines 67–70). `changeUser()` compares old and new roles and regenerates the session identity when they differ (lines 102–109). `hasAccess()` delegates authorization to `mgr:authorizeRequest(self, resource)` (lines 123–129); this file does not define that manager policy.
- Interface and remote-address checks are implemented in lines 140–155 and 176–201. When a user's interface list or `allowed_ip` map is absent, the corresponding check returns true; when present, the code checks membership. The result is cached with the user, interface, interface address, and remote address.
- `checkCSRFtoken(token)` compares the supplied token directly with `self.CSRFtoken`; a mismatch logs an error and exits with HTTP Forbidden, while a match returns true (lines 210–220).

## Limitations and reproducibility

The XML parser read only the requested service type, relative service paths, action arguments, state-variable fields, and allowed-value ranges. It did not print or record device-description identifiers, addresses, names, or other description fields. The related-source review is static text inspection; no device, network service, runtime configuration, authentication exchange, cookie, or CSRF request was exercised in **this file’s pass**. Live control-plane results for the same service type are in [f1-wfa-wlanconfig-49152-2026-10-12.md](f1-wfa-wlanconfig-49152-2026-10-12.md). **CUPS :631** is not described in these nginx snapshots; live IPP behavior is in [f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md) ([docs/f1-cups-631.md](../docs/f1-cups-631.md)). Source includes and the implementation behind delegated manager methods remain outside this pass.

Commands used: Python 3 standard-library parsing (`xml.etree.ElementTree`) and SHA-256 (`hashlib`) in an inline script; `rg --files artifacts` filtered to the three requested XML basenames; `rg -n -i 'cookie|sessionid|CSRF|role|authorizeRequest|hasAccess|checkrequest|handleAuth|access_by_lua|authenticate\(|listen\s' artifacts/source-review/nginx.conf artifacts/source-review/session.lua`; `nl -ba artifacts/source-review/nginx.conf`; and `nl -ba artifacts/source-review/session.lua`.
