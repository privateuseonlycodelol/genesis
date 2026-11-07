# DPP → shell chain demonstrated live (plumbing half) — 2026-11-07

Demonstrates, on the live F1, the **shell-sink plumbing** in the onboarding-gated DPP path from [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md): a fabricated `DPP-CONNECTOR` event value reaches `wps_pbcd`'s `system()` with no shell filtering, and a value containing `;` executes a second command as root. This does **not** establish that a standards-conforming DPP peer can place shell syntax in any production event field.

## What was executed (VERIFIED)

`wps_pbcd` was restarted with a lab-built `LD_PRELOAD` shim (`artifacts/lcm-demo-2026-11-07/dpp_hook.c`, cross-compiled `zig cc -target arm-linux-gnueabi.2.32`) that (a) fabricates one hostapd ctrl-interface event at the `wpa_ctrl_recv` transport boundary and (b) logs every `system()` command line the daemon runs. A benign WPS-PBC activation made the ctrl socket readable. The fabricated event was:

```
DPP-RX type=0
DPP-TX t
DPP-CONNECTOR genesisprobe;touch /tmp/genesis_dpp_marker
```

The daemon's own production code then executed (from `/tmp/genesis_system_log`):

```
hostapd_cli -i wl0 set dpp_connector genesisprobe;touch /tmp/genesis_dpp_marker
```

and `/tmp/genesis_dpp_marker` was created — the shell parsed the `;` inside the connector value and ran the attacker-chosen second command **as root**. That is the unquoted-`%s` shell injection predicted by the exhaustion pass, now observed executing.

## The exact production path (VERIFIED by disassembly, in `sbin/wps_pbcd`)

1. hostapd ctrl unsolicited event → usched fd callback → `wpa_ctrl_recv` into the per-connection buffer at `ctx+164`, length at `ctx+0x2a4` (call at `0x16ab0`).
2. Tail-jump through the slot `ctx+0xc58` (registered at init, `0x13468`) = the dispatcher at `0x153f4`.
3. The dispatcher calls the slot `ctx+0xc60` (registered at init, `0x13910`) = **the applier at `0x19490`** with the ctx — every event passes through it.
4. The applier parses the message: needles `DPP-RESPONSE-PENDING `, `DPP-RX `/`type=0` (sets `dpp_started`), `DPP-TX ` or the alternates at `0x198ec` (all converge to the connector path), `DPP-CONNECTOR `, `DPP-C-SIGN-KEY `, `DPP-NET-ACCESS-KEY `.
5. Gates resolved empirically this pass:
   - `nvram <if>_mode` must be exactly `ap` → sets the internal flag r6 (live value on this unit: `ap` on all interfaces — naturally satisfied).
   - **`nvram <if>_dpp_role` must be non-NULL** — this was the last unknown gate. With it unset, the applier reads the connector, skips the `system()` site, and moves to the next interface (observed live via an `nvram_get` trace). With `wl0_dpp_role=enrollee`, the connector `system()` fires. The daemon init sets a per-ctx flag when `<if>_dpp_role == "enrollee"` (`0x1392c` → `ctx+0xc70 |= 4`), i.e. the device is in the DPP-enrollee role — exactly the state a real onboarding window creates. The strings `configurator` / `enrollee` and the log `unset dpp_started NVRAM because credentials received from configurator` confirm the intended semantics.
   - ctx backhaul-type `0xc3c != 3`.
6. `snprintf("hostapd_cli -i %s set dpp_connector %s", ifname, value)` at `0x19708` — **no quoting around the value** — then `system()` at `0x19720`. The `set dpp_csign %s` variant converges onto the same `system()` site (`0x197f8` → `0x1971c`), and `set dpp_netaccesskey %s` has its own site at `0x19b1c` in the same function.

**Correction to the 2026-11-07 per-site addendum in [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md):** the `set dpp_csign %s` format in `wps_pbcd` is **not** a dead string — it is fed by the live `DPP-C-SIGN-KEY ` needle branch at `0x1977c` and shares the `system()` site at `0x19720`. The `set ssid %s` / `set wpa_passphrase %s` / `Info: PBCD ...` strings remain unreferenced (dead) as recorded. Static analysis identifies all three DPP value branches (`dpp_connector`, `dpp_csign`, `dpp_netaccesskey`) as shell command inputs, but the live fabricated-event execution exercised the connector branch only. Vendor-matching ROM disassembly shows quote/newline checks followed by a base64url decoder that skips non-alphabet characters and retains the original connector string for emission. A semicolon inserted only in the JWS signature segment is therefore a **DERIVED** candidate; an offline public test vector verified that insertion followed by skipped decoding preserves signature validity. The live router has now emitted a genuine 445-character connector in a corrected localhost TCP exchange, but no punctuated connector has passed the live parser or reached the shell sink. See the radio-side finding for the experiment and remaining gap.

## Demonstrated vs not demonstrated

**Demonstrated:** event-value → parse → gates → `snprintf` → `system()` → attacker-chosen root command execution, running the daemon's real code on the device.

- The **radio transport and real field encoding**: the root-command proof used a fabricated event at `wpa_ctrl_recv`; the later genuine DPP exchange used localhost TCP, not 802.11, and the onboarding role gate was closed. Vendor-matching ROM disassembly and the live TCP event confirm that the connector is emitted as a string. The decoder skips non-alphabet bytes while the original connector text is retained. A semicolon in the third JWS segment can therefore survive signature checking in principle; this was verified offline with a public test vector, but a live punctuated connector has not passed the parser. C-sign and network-access keys are emitted as hex and do not offer the same punctuation route. See the [DPP radio-side finding](f1-dpp-radio-emission-pass-2026-11-07.md).
- The **state**: `wl0_dpp_role=enrollee` (plus the natural `wl0_mode=ap`) was set by root for this test. In the real attack the same state is created by the device being in the user-initiated DPP-onboarding window; outside that window the gate blocks the `system()` sites (also observed live: with the role unset, the parse ran and skipped the command).
- No radio-side DPP exchange was performed; no Wi-Fi state was changed.

## Restore (VERIFIED)

`wl0_dpp_role` and `dpp_started` unset (`nvram unset` + `commit`; live values empty), the shim and all `/tmp/genesis_*` evidence removed from the device, and `wps_pbcd` restarted clean — no `LD_PRELOAD` in its environment, UDP 58032 rebound, marker absent. Evidence preserved privately in `artifacts/lcm-demo-2026-11-07/` (`dpp_hook.c`, `dpp_hook.so`, run outputs).

## Impact

**VERIFIED:** if attacker-controlled bytes containing shell metacharacters reach the parsed event value while the onboarding gate is open, `wps_pbcd` executes shell syntax as root. The fabricated `;` event proved that sink. The vendor hostapd binary, checked below, keeps a `;` inside the connector string it later emits. A frame that delivers that string has not been sent.

## Vendor connector formatter (VERIFIED in ROM hostapd, 2026-11-07)

ROM `usr/sbin/hostapd` sha256 `875f3bad42fa1addf2d10bf4f466f2f520c4b5be8b9ab85e6c7e5c1b19adf00d`. This supersedes the earlier note that a conforming connector cannot carry `;`. That note was from an upstream source mirror and a reading of the JWS alphabet. The shipped decoder does not use that rule.

- The credential emitter at `0xe98d4` loads the pointer at the start of the config object and passes it to the message function with `DPP-CONNECTOR %s`. There is no hex conversion and no character filter on that path. The C-sign key (`0xe990c`) and the net-access key (`0xe9958`) are different: each allocates `2*len+1`, converts the binary key, and emits the hex text.
- Before a signed connector is accepted, `0xd2960` rejects it only when `strchr` finds `"` (`0x22`) or a newline (`0x0a`). A semicolon matches neither.
- The JWS walk at `0xddc3c` finds the dots, then calls `0xfeb40`. That decoder (`0xfe814`) fills a 128-byte map with `0x80`, writes the 64 base64url alphabet entries, and on a lookup of `0x80` branches to `0xfe928`, which advances to the next input byte. Characters outside the alphabet, including `;`, are skipped. They do not fail the decode.
- On the success path, `0xd2c7c` does `strdup` of `sl` and stores it at the start of the config object. `sl` was loaded at `0xd295c` from the JSON string value (`[r8+0xc]`), the original signedConnector text.

**DERIVED:** insert `;` into a base64url segment of a signature-valid connector. The decoder skips it, the signature still covers the same bytes, and `DPP-CONNECTOR %s` emits the original text, semicolon included. A Python model of that skip agreed on one sample (`eyJ0ZXN0` versus `eyJ0;ZXN0`); that model is not the device function. Quote and newline still die at the `strchr` checks.

**Offline vector check (VERIFIED, not a live-device test):** a public hostapd DPP test vector was verified with Python `cryptography` using its P-256 public key. Inserting `;` only in the third JWS segment, then stripping it as the vendor decoder does, reproduced the same 64-byte signature and valid SHA-256/ECDSA verification. The original connector text still contains the inserted byte. Fixture: ignored private file `artifacts/lcm-demo-2026-11-07/dpp_semicolon_signature_override.json` (SHA-256 `1f674c9ea5aed471e0983631b9581f3d278f782e85ab73528387d64f4d6d2057`). This establishes the signature-segment construction, not acceptance by the live peer or shell execution.

**Updated 2026-11-07, TCP:** localhost DPP exchanges made production hostapd emit genuine `DPP-CONNECTOR` events. The corrected reverse-direction run measured the event argument safely as 445 characters with no semicolon. See the radio-side finding. `wl0_dpp_role` was empty for these exchanges, so `wps_pbcd` did not run the values. A prior configurator override containing shell punctuation did not create a marker file; the signature-segment candidate has not yet been tested with a connector whose network-access key matches the live exchange.

**Not shown:** a configuration response on the air, or `wps_pbcd` running a command from a genuine connector. The sink, the formatter, and the TCP delivery into the emitter are verified. The Wi-Fi delivery and the shell step from a real connector are still open.
