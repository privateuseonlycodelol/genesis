# DPP radio-side emission pass — incomplete exchange, reboot cause unknown (2026-11-07)

This pass pursued the missing radio half of the [DPP→shell plumbing demonstration](f1-dpp-shell-chain-demonstrated-2026-11-07.md): a genuine DPP exchange causing production hostapd to emit `DPP-CONNECTOR`, then production `wps_pbcd` parsing it. Genuine DPP Authentication Request frames were reportedly transmitted, but no exchange completed and no `DPP-CONNECTOR` event was observed. A router reboot followed the last out-of-band chirp attempt; its cause is unknown. This does **not** establish the full radio-to-shell chain or a DPP-triggered crash.

## Observations in the live run record

- **VERIFIED as reported in the session record:** shipped hostapd accepted `dpp_configurator_add` (id 1), `dpp_bootstrap_gen type=qrcode` (id 1, EC P-256 URI), and `dpp_bootstrap_set … conf=ap ssid=Telia-C66283 configurator=1` (OK).
- **VERIFIED as reported in the session record:** `dpp_auth_init peer=1 own=1` on wl0 produced these hostapd control events, captured by a second control client using the watcher source at `artifacts/lcm-demo-2026-11-07/dpp_watch.c`:

  ```
  <3>DPP-TX dst=ff:ff:ff:ff:ff:ff freq=5180 type=0
  <3>DPP-TX dst=ff:ff:ff:ff:ff:ff freq=5200 type=0
  <3>DPP-TX dst=ff:ff:ff:ff:ff:ff freq=5220 type=0
  <3>DPP-TX dst=ff:ff:ff:ff:ff:ff freq=5240 type=0
  ```

  These events show the production stack attempting/transmitting DPP Authentication Request frames. The raw `/tmp` logs did not survive the later reboot and are not preserved independently in the repository.
- **VERIFIED as reported:** two stations roamed from wl0 to wl1 during the chirp and later completed EAPOL four-way handshakes on wl1. This establishes client disruption during the attempt, but not its cause or duration beyond the captured events.
- **VERIFIED by recorded ROM disassembly:** `hostapd_dpp_handle_config_obj` contains emitters for `DPP-CONFOBJ-NETROLE`, `DPP-CONFOBJ-AKM`, `DPP-CONNECTOR`, `DPP-C-SIGN-KEY`, and net-access-key events. The recorded callers are in config-object processing after DPP authentication/configuration processing. `dpp_configurator_sign` returned `FAIL` on this build; no observed ctrl-only path emitted `DPP-CONNECTOR`.
- **VERIFIED as reported:** `get dpp_connector` returned `FAIL` during the pass and `dpp_started` remained empty. No DPP-CONNECTOR event was recorded.

## Why this attempt did not complete

The run record reports wl0 configured on 5 GHz (ch 36 / 5180 MHz) and wl1 on 2.4 GHz (ch 1 / 2412 MHz). wl0's chirp events list 5180–5240 MHz. A later `dpp_auth_init peer=1` on wl1 using the wl0 bootstrap returned `FAIL`; no external DPP peer or running `wpa_supplicant` was available in the recorded setup. These facts explain the failed attempt, but do not prove that every same-box or cross-radio arrangement is impossible. A compatible external peer is a plausible next experiment, not proof that a QR scan alone completes the exchange.

## Router reboot after the last attempt

**VERIFIED temporal sequence as reported:** the last command was `dpp_auth_init peer=1` on wl1; hostapd returned `FAIL`; within seconds SSH disconnected and the router became unreachable. It returned about 11 minutes later, with reported `uptime` near 11 minutes (reboot ~04:37, recovery ~04:48).

**Cause UNKNOWN.** No UART/panic capture, persistent crash log, or controlled reproduction distinguishes a kernel panic, watchdog action, unrelated reboot, or DPP/radio-triggered fault. Therefore this is not a demonstrated DPP crash primitive or remotely reachable DoS. Do not repeat the same wl1 out-of-band chirp based only on this evidence.

Recovery was reported verified: both radios and BSSes returned at the same frequencies with BSSIDs unchanged, mesh daemons respawned, `wps_pbcd` ran with a new pid, and `wl0_dpp_role`/`dpp_started` were empty. Reboot cleared `/tmp`, including volatile DPP state, watcher binaries, and raw logs. No persistent configuration change was reported.

## What was not shown

- A completed genuine DPP authentication/configuration exchange or a genuine `DPP-CONNECTOR` event.
- The production radio-event → `wps_pbcd` parse → unquoted `system()` chain. Only the event-transport/plumbing half was previously demonstrated using a fabricated event; see [the shell-chain finding](f1-dpp-shell-chain-demonstrated-2026-11-07.md).
- That a conforming DPP exchange can put shell metacharacters into connector or other emitted values. The fabricated event containing `;` does not answer this.
- That the out-of-band chirp caused the router reboot.

## Evidence and reproducibility limits

- Watcher source: `artifacts/lcm-demo-2026-11-07/dpp_watch.c`; deployed watcher and `/tmp/dpp_events_wl0.log`/`wl1` were lost on reboot.
- Emitter analysis: ROM copy at `artifacts/firmware/rom-2026-11-06/rom/usr/sbin/hostapd`.
- The supplied session handoff preserves the quoted event lines and sequence, but the full terminal transcript, device-side raw logs, and command-by-command uptime/BSS checks were not retained in the repository. Claims above are explicitly attributed to that run record and are not independently replayable from raw logs here.

## Next experiment

Use a separate DPP peer that supports 5 GHz channel 36, preserve host-side ctrl logs and UART/persistent reboot evidence, and observe whether authentication completes and `DPP-CONNECTOR` is emitted. First verify router baseline; stop immediately if it reboots again. Even a genuine connector event would leave shell-metacharacter reachability to be tested separately.
