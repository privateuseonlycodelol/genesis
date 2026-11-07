# DPP radio-side emission pass — incomplete exchange, reboot cause unknown (2026-11-07)

This pass pursued the missing radio half of the [DPP→shell plumbing demonstration](f1-dpp-shell-chain-demonstrated-2026-11-07.md): a DPP exchange causing production hostapd to emit `DPP-CONNECTOR`, then production `wps_pbcd` parsing it. The radio attempts did not complete an exchange. Later TCP and control-only tests made production hostapd emit genuine, locally generated connector events; neither establishes peer-controlled connector content or the full radio-to-shell chain. A router reboot followed an earlier out-of-band chirp attempt; its cause remains unknown.

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
- **VERIFIED by recorded ROM disassembly:** `hostapd_dpp_handle_config_obj` contains emitters for `DPP-CONFOBJ-NETROLE`, `DPP-CONFOBJ-AKM`, `DPP-CONNECTOR`, `DPP-C-SIGN-KEY`, and net-access-key events. The recorded callers are in config-object processing after DPP authentication/configuration processing. The earlier recorded `dpp_configurator_sign` attempt returned `FAIL`; a later direct live test returned `OK` and emitted a locally generated connector event (below).
- **VERIFIED as reported:** `get dpp_connector` returned `FAIL` during the pass and `dpp_started` remained empty. No DPP-CONNECTOR event was recorded.

## Why this attempt did not complete

The run record reports wl0 configured on 5 GHz (ch 36 / 5180 MHz) and wl1 on 2.4 GHz (ch 1 / 2412 MHz). wl0's chirp events list 5180–5240 MHz. A later `dpp_auth_init peer=1` on wl1 using the wl0 bootstrap returned `FAIL`; no external DPP peer or running `wpa_supplicant` was available in the recorded setup. These facts explain the failed attempt, but do not prove that every same-box or cross-radio arrangement is impossible. A compatible external peer is a plausible next experiment, not proof that a QR scan alone completes the exchange.

## Router reboot after the last attempt

**VERIFIED temporal sequence as reported:** the last command was `dpp_auth_init peer=1` on wl1; hostapd returned `FAIL`; within seconds SSH disconnected and the router became unreachable. It returned about 11 minutes later, with reported `uptime` near 11 minutes (reboot ~04:37, recovery ~04:48).

**Cause UNKNOWN.** No UART/panic capture, persistent crash log, or controlled reproduction distinguishes a kernel panic, watchdog action, unrelated reboot, or DPP/radio-triggered fault. Therefore this is not a demonstrated DPP crash primitive or remotely reachable DoS. Do not repeat the same wl1 out-of-band chirp based only on this evidence.

Recovery was reported verified: both radios and BSSes returned at the same frequencies with BSSIDs unchanged, mesh daemons respawned, `wps_pbcd` ran with a new pid, and `wl0_dpp_role`/`dpp_started` were empty. Reboot cleared `/tmp`, including volatile DPP state, watcher binaries, and raw logs. No persistent configuration change was reported.

## What was not shown

- A completed genuine radio DPP authentication/configuration exchange or a peer-originated `DPP-CONNECTOR` event. The later local TCP exchange and control-only signer event do not establish either.
- The production radio-event → `wps_pbcd` parse → unquoted `system()` chain. Only the event-transport/plumbing half was previously demonstrated using a fabricated event; see [the shell-chain finding](f1-dpp-shell-chain-demonstrated-2026-11-07.md).
- That a conforming DPP exchange can put shell metacharacters into connector or other emitted values. The fabricated event containing `;` does not answer this.
- That the out-of-band chirp caused the router reboot.

## Controlled repeat after recovery (2026-11-07 ~05:05 local)

At the user's direction, the wl1 cross-band attempt was repeated once from a clean baseline while SSH was connected over wl0/wl1 Wi-Fi (`en0`). Baseline: uptime ~25 minutes, hostapd PIDs `6891 6839`, both BSSes up, `wl0_dpp_role` and `dpp_started` empty. Temporary configurators/bootstrap state was rebuilt and checked after each step; uptime advanced continuously and both BSSes/PIDs remained stable.

`hostapd_cli -i wl1 dpp_auth_init peer=1` returned `OK`. Filtered device logs showed real `DPP-TX dst=ff:ff:ff:ff:ff:ff type=0` events from wl1 at 2437, 2412, 2462, 2417, 2422, 2427, 2432, and 2442 MHz. The router did not reboot during the observation: uptime advanced from about 28 minutes to 29 minutes; PIDs stayed `6891 6839`; both BSSes remained up. `get dpp_connector` still returned `FAIL`. Thus the earlier reboot was **not reproduced** by this single repeat; its cause remains unknown.

Cleanup was verified: `dpp_stop_chirp` and `dpp_stop_listen` returned `OK`; removal of bootstrap/configurator id 1 on both radios returned `OK`; subsequent bootstrap/configurator lookups returned `FAIL`; DPP role/start keys remained empty; both BSSes and original hostapd PIDs remained present. No root command was run or obtained.

## Over-the-air root impact assessment

**Not demonstrated as an over-the-air exploit.** The root command ran from a fabricated ctrl event. The shipped hostapd will emit a connector that still contains `;` after a successful signature check, because its base64url decoder skips that byte and the saved string is the original text. See the shell-chain finding. What has not been sent is the configuration response that carries that string.

### Same-PHY two-BSS attempt and field-format narrowing (2026-11-07)

**VERIFIED from the live-run transcript:** two hostapd control interfaces on the same 5 GHz PHY (wl0.1 and wl0.2, 5180 MHz) were configured as enrollee/listener and configurator/initiator. Bootstrap/configurator setup and `dpp_auth_init peer=2 conf=ap-dpp ... configurator=1` returned `OK`. Watchers on both control interfaces observed only broadcast `DPP-TX ... freq=5180 type=0` events. No `DPP-AUTH-SUCCESS`, `DPP-CONF-*`, credential event, or `DPP-CONNECTOR` was observed. This arrangement therefore did not complete a loopback exchange.

**Cleanup independently rechecked over read-only SSH:** uptime was continuous at 1:24; hostapd PIDs 6839 and 6891 remained; wl0.1 and wl0.2 remained ENABLED at 5180 MHz; `wl0_dpp_role`, `wl1_dpp_role`, and `dpp_started` were empty; `/tmp/dpp_watch` and both watcher logs were absent. The filtered process listing showed only the two hostapd processes. No Wi-Fi configuration change or router reboot was observed during that check.

**Superseded (2026-11-07, vendor disassembly):** the upstream-mirror claim that a connector cannot carry `;` does not hold for this binary. The shipped decoder skips non-alphabet bytes, and the original signedConnector text is what `DPP-CONNECTOR %s` emits. Details and addresses are in the [shell-chain finding](f1-dpp-shell-chain-demonstrated-2026-11-07.md). C-sign and net-access keys are still hex-encoded. Genuine locally generated connector events have since been observed, but no peer-originated event has been captured.

## Evidence and reproducibility limits

- Watcher source: `artifacts/lcm-demo-2026-11-07/dpp_watch.c`; deployed watcher and `/tmp/dpp_events_wl0.log`/`wl1` were lost on reboot.
- Emitter analysis: ROM copy at `artifacts/firmware/rom-2026-11-06/rom/usr/sbin/hostapd`.
- The supplied session handoff preserves the quoted event lines and sequence, but the full terminal transcript, device-side raw logs, and command-by-command uptime/BSS checks were not retained in the repository. Claims above are explicitly attributed to that run record and are not independently replayable from raw logs here.

## Local TCP exchange (VERIFIED 2026-11-07, no Wi-Fi frame)

`DPP_AUTH_INIT` takes the TCP connect at `0xe8ca0` when the command contains `tcp_addr=`, and returns without the radio send. With that argument present, wl0 listened as enrollee on TCP port 8908 and wl1 initiated as configurator to `127.0.0.1`. The bootstrap channel was `81/1` so wl1 could build the authentication message; an earlier attempt with `115/36` failed before connect with `No available channels for initiating DPP Authentication` and did not transmit.

At 13:34:54 the syslog showed `DPP-AUTH-SUCCESS` on both processes, `DPP-CONF-SENT` on wl1, and on wl0 `DPP-CONF-RECEIVED`, `DPP-CONFOBJ-SSID genesis`, and `DPP-CONNECTOR`. The ssid was the one set in that command. `logread` count of `DPP-TX` stayed 0. wl0 stayed ENABLED on channel 36. Uptime advanced through the exchange. `wl0_dpp_role` was empty, so this did not exercise `wps_pbcd`'s `system()`.

A repeat through a TCP proxy on the lab Mac (configurator connected to `192.168.1.150:8910`, proxy to the enrollee on port 8908) also reached `DPP-CONF-RECEIVED` for ssid genesis. The configuration response body on that socket did not contain the connector text; it is encrypted before it is sent. A runtime `SET dpp_config_obj_override` was accepted, and a connector carrying shell punctuation was then offered. No marker file appeared. Clearing that override was done by restarting the wl1 hostapd process; wl1 had no stations. It came back ENABLED on channel 1. wl0's hostapd pid was unchanged.

With the role latched (`wl0_dpp_role=enrollee`, `wps_pbcd` restarted, then both restored), a PSK override whose SSID was `gene;sis` was emitted as `DPP-CONFOBJ-SSID`. A signed connector with `;id>` only in the signature segment was not. Debug logs showed the c-sign parse succeed and then `netAccessKey in connector does not match own protocol key`, followed by `DPP-FAIL Configurator rejected configuration`. The ignore-mismatch bit lives at hostapd `+0x9ec` and is copied into an initiator auth object at `+0xb00` (`0xe9c98`). The TCP enrollee that received the object did not have the bit set, including when wl0 itself initiated. A `strdup`/`memcpy` hook in the wl1 process never observed the connector string that hostapd builds on its own. No marker file. The live SSID stayed `Telia-C66283`. `DPP-TX` stayed 0. wl0's hostapd pid stayed 6839.

**Not shown:** an 802.11 configuration frame, or `wps_pbcd` executing a genuine connector.

## Corrected responder-side TCP exchange (VERIFIED 2026-11-07 14:20–14:21 local)

The earlier reverse-direction exchange failed for two separately identified setup reasons: `dpp_bootstrap_set` alone did not provide a responder configuration, and a bootstrap URI advertising 2.4 GHz channel 1 gave the 5 GHz initiator no usable DPP channel. Upstream hostapd code shows the responder reads `hapd->dpp_configurator_params` when processing Authentication Requests and when starting its DPP controller; this is a source-based explanation, not a claim of vendor-source parity. The live CLI accepted `SET dpp_configurator_params`.

With wl1 temporarily configured as a DPP configurator (`conf=ap-dpp`, configurator id 1, SSID `genesis`) and a bootstrap URI for 115/36 (5180 MHz), wl1's controller listened on TCP 8908. wl0 imported that URI and `dpp_auth_init peer=1 role=enrollee conf=query tcp_addr=127.0.0.1 tcp_port=8908` returned `OK`. Syslog recorded `DPP-AUTH-SUCCESS` on both interfaces, `DPP-CONF-RECEIVED` on wl0, and `DPP-CONF-SENT` on wl1. A corrected `hostapd_cli -a` observer accounted for the event arguments separately and recorded `DPP-CONNECTOR value_len=445 semicolon=0`; it never logged the connector or key values. Uptime advanced continuously; both BSSes remained enabled at 5180 and 2462 MHz.

Cleanup was verified after the run: the temporary controller stopped; configurator and bootstrap objects were removed; the runtime configurator parameter was set to an empty value; the temporary listener, scripts, and files were absent; both DPP role keys and `dpp_started` were empty; all five exact background event-watcher processes created by the attempts were terminated; and both BSSes remained enabled. No marker was tested or created in this run. This is a locally generated TCP DPP exchange, not an over-air or peer-originated attack, and the enrollee role gate was closed, so `wps_pbcd` did not apply the connector.

Sanitized reproduction record: `artifacts/lcm-demo-2026-11-07/dpp-tcp-config-exchange-2026-11-07.txt`. Raw connector, keys, and bootstrap URI were not retained.

Earlier `AUTH FAIL` attempts were not counted as protocol failures: DEBUG logs showed `No available channels for initiating DPP Authentication` because the 5 GHz initiator was given a channel-1-only bootstrap. Changing the bootstrap to 115/36 distinguished and resolved that setup error.

## Control-only local signer event capture (VERIFIED 2026-11-07)

A small AF_UNIX datagram observer attached to `/var/run/hostapd/wl0`. With the DPP role unset and no radio frames, `hostapd_cli -i wl0 dpp_configurator_add` returned id `1`; `hostapd_cli -i wl0 dpp_configurator_sign conf=ap-dpp configurator=1` returned `OK`. The observer recorded three `DPP-CONFOBJ` events, `DPP-CONNECTOR value_len=445 semicolon=0`, `DPP-C-SIGN-KEY`, and `DPP-NET-ACCESS-KEY`. It recorded only event categories, connector length, and semicolon presence; connector and key values were not printed or retained. Configurator removal was verified (`dpp_configurator_get_key 1` returned `FAIL`). A subsequent check found the observer binary/socket absent, role/start keys empty, and the hostapd processes still present.

Reproduction/evidence: `artifacts/lcm-demo-2026-11-07/dpp_ctrl_observer.c` (SHA-256 `51fe83815e24a491ef9241b8bacb67b9245c97da0096ecbfb8ac9a2758c3e1a4`); sanitized output `artifacts/lcm-demo-2026-11-07/dpp-local-signer-event-2026-11-07.txt`; uploaded observer binary SHA-256 `25b85c67e1e083bc36f04bb66245b8e386bdf3629830e9005110b1268fe565bb`. This proves a ctrl-only path emits a locally generated connector while the onboarding gate is closed. It does not prove the event reaches the shell sink, contains attacker-controlled bytes, or enables command execution.

**Attempted gate follow-up aborted before signing:** a later test temporarily set `wl0_dpp_role=enrollee` but stopped because the router-side observer had been removed by the preceding cleanup. No configurator or signature command ran; the cleanup trap restored the unset role and removed temporary files. A subsequent status check found wl0 and wl1 enabled, while wl1's hostapd PID had changed. Logs show a concurrent wl1 `E_RADIO`/`E_LINK` down-up event; whether that relates to the short-lived role change is **UNKNOWN**. The role-gated test was not repeated.

## Next experiment

The open piece is a peer-originated connector reaching `wps_pbcd` while `wl0_dpp_role=enrollee`, with shell punctuation that survives connector verification, followed by a verified marker. The observed local TCP and control-only events were generated on-device; Wi-Fi delivery still needs an independent 5 GHz DPP peer. Do not present the shell plumbing proof as a demonstrated over-the-air RCE.

## Live radio and configurator-socket recheck (2026-11-07 14:47–14:50 CET)

**VERIFIED, read-only SSH on the same owned unit:** uptime was 10 h 11 min; `hostapd` PIDs were 6839 (`wl0`) and 13889 (`wl1`), and `map-dpp-configurator` PID 21884. `wl0` supported 5 GHz channels and was on channel 36 / 5180 MHz; `wl1` supported only 2.4 GHz channels and was on channel 11 / 2462 MHz. `hostapd_cli all_sta` counted one associated station on `wl0` and zero on `wl1`. Both interfaces were enabled; `wl0_dpp_role`, `wl1_dpp_role`, and `dpp_started` were empty.

**DERIVED route elimination:** the two on-board radios cannot exchange same-channel DPP action frames in their present band/channel configuration. Retuning `wl0` would interrupt its associated station, so the proposed same-device over-air pairing was not attempted. This does not rule out a compatible external 5 GHz peer or a later no-client maintenance window.

The live configurator process is root inside mount namespace `mnt:[4026532602]` (an LCM container). Its bound datagram socket inode 118080 appeared in `/proc/net/unix` as `/tmp/dpp.sock`; the path is visible at `/proc/21884/root/tmp/dpp.sock` but not in the host namespace's `/tmp`. The executable's receive loop accepts up to 1024 bytes and copies at most 256 bytes to its callback buffer before dispatch. **No datagram was sent:** the callback message format and a harmless request/response exchange remain unestablished, and the socket is local to the container. No network exposure or exploit was demonstrated.

**What was not shown:** an over-air DPP exchange, a peer-controlled connector reaching `wps_pbcd`, or command execution from a genuine connector. The next high-value experiment still requires a compatible 5 GHz DPP peer (or an empty-client window) and a capture/observer that preserves sanitized event metadata.
