# DPP → shell chain demonstrated live (plumbing half) — 2026-11-07

Demonstrates, on the live F1, the code-execution half of the onboarding-gated DPP chain from [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md): an attacker-influenced `DPP-CONNECTOR` event value reaches `wps_pbcd`'s `system()` with **no shell filtering**, and a value containing `;` executes an attacker-chosen second command as root.

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

**Correction to the 2026-11-07 per-site addendum in [f1-miniupnpd-cwmpd-2026-11-06.md](f1-miniupnpd-cwmpd-2026-11-06.md):** the `set dpp_csign %s` format in `wps_pbcd` is **not** a dead string — it is fed by the live `DPP-C-SIGN-KEY ` needle branch at `0x1977c` and shares the `system()` site at `0x19720`. The `set ssid %s` / `set wpa_passphrase %s` / `Info: PBCD ...` strings remain unreferenced (dead) as recorded. The demonstrated injection therefore applies to all three DPP value sites (`dpp_connector`, `dpp_csign`, `dpp_netaccesskey`), all quotes-absent or quotes-only.

## Demonstrated vs not demonstrated

**Demonstrated:** event-value → parse → gates → `snprintf` → `system()` → attacker-chosen root command execution, running the daemon's real code on the device.

**Not demonstrated (and honestly bounded):**
- The **transport**: the event was fabricated by the lab `LD_PRELOAD` at `wpa_ctrl_recv`. In a real attack it is emitted by hostapd itself, whose patched build contains the emitters `DPP-CONNECTOR %s` and `DPP-NET-ACCESS-KEY %s %lu` (verified in the `hostapd` strings). The connector value originates from the remote DPP configurator (the exhaustion-pass provenance trace), so a malicious configurator completing a DPP exchange with the enrollee supplies the bytes.
- The **state**: `wl0_dpp_role=enrollee` (plus the natural `wl0_mode=ap`) was set by root for this test. In the real attack the same state is created by the device being in the user-initiated DPP-onboarding window; outside that window the gate blocks the `system()` sites (also observed live: with the role unset, the parse ran and skipped the command).
- No radio-side DPP exchange was performed; no Wi-Fi state was changed.

## Restore (VERIFIED)

`wl0_dpp_role` and `dpp_started` unset (`nvram unset` + `commit`; live values empty), the shim and all `/tmp/genesis_*` evidence removed from the device, and `wps_pbcd` restarted clean — no `LD_PRELOAD` in its environment, UDP 58032 rebound, marker absent. Evidence preserved privately in `artifacts/lcm-demo-2026-11-07/` (`dpp_hook.c`, `dpp_hook.so`, run outputs).

## Impact

Inside the onboarding window, a peer that completes DPP as configurator can turn the configurator-supplied credential fields into **arbitrary root command execution** (demonstrated at the `system()` layer; the one-time `LD_PRELOAD` only replaced the event transport, not any daemon logic). Outside the window the gate holds — consistent with, and sharpening, the exhaustion-pass DERIVED assessment. The chain is now: **user starts onboarding → device enters DPP-enrollee role → malicious configurator completes exchange → `DPP-CONNECTOR`/`DPP-NET-ACCESS-KEY`/`DPP-C-SIGN-KEY` values flow to `system()` unquoted → root RCE.**
