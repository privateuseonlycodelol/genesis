# Genesis

Research notes for an owned Telia F1. Vantiva board GCNT-X, firmware 23.1.b.

`findings/` holds the write-ups. `scripts/` holds the tools. Firmware images, captures, and secrets stay in `artifacts/` and are not committed. Record a SHA-256 beside any image you keep.

The 2026-10-27 note that recovery flashing needs no vendor signature is overstated. That run skipped every bundle member, so nothing was written. An unsigned `bootfs` still hangs this board. See [BOOT-P LAN, Addendum 9](findings/f1-bootp-lan-2026-10-13.md) and [FIT packaging](findings/f1-fit-rootfs-packaging-2026-10-27.md).

## Current state

| Topic | Status | Note |
| --- | --- | --- |
| Root | Overlay SSH, after one serial recovery | [Do it again](docs/root-again.md), [what happened](findings/f1-quad-overlay-flash-2026-11-06.md) |
| Signed boot | Vendor `bootfs` is checked. `rootfs_data` is not. An aarch64 musl userspace runs under this kernel | [FLD gate](findings/f1-uboot-fld-secure-boot-gate-2026-11-04.md), [OpenWrt userspace](findings/f1-openwrt-userspace-2026-11-06.md) |
| Flash and OSCK | Both banks and the 19.x reference image unwrap. Do not flash the 19.x image | [Flash volumes](findings/f1-flash-volumes-2026-11-06.md) |
| LAN DNS | dnsmasq forwards to a local DoH proxy for `dns.rilah.app`. The URL is only on the router | [DNS and phone-home](findings/f1-doh-and-tracking-2026-11-06.md) |
| Idle services | Usage meter and Airties `cloud-comm` disabled. `cwmpd` stopped. Telia MQTT still up. Wi-Fi processes were left running | [Idle services](findings/f1-idle-services-stopped-2026-11-06.md), [reset parking lot](findings/f1-reset-persistence-2026-11-06.md) |
| Wi-Fi | 2026-11-07 read-only check: `Telia-C66283` reported on wl0 (5 GHz ch 36) and wl1 (2.4 GHz ch 11); one station associated on wl0. This supersedes the 2026-11-06 down snapshot | [Wi-Fi BSS](findings/f1-wifi-bss-down-2026-11-06.md) |
| Reset | Parking lot re-seeded across an unplanned reboot. A button reset is still untested. `rtfd --all` still wipes it | [Reset parking lot](findings/f1-reset-persistence-2026-11-06.md) |
| Upgrade wipe | A restore script is on the `opt` volume, which the flasher does not name. The launcher was left dormant and has not been shown running it | [Opt restore](findings/f1-opt-keep-root-2026-11-06.md) |
| Admin UI | Overlay stylesheet, injected into HTML by nginx. Login page restyled. Templates unchanged | [UI skin](findings/f1-ui-skin-2026-11-06.md) |
| Plugins | Supervisor on the overlay. Page `/genesis/` and JSON `/genesis/api` after login. Install with `scripts/genesis/install.sh` | [Plugin supervisor](findings/f1-plugin-supervisor-2026-11-06.md) |
| Tailscale UI | The Tailscale address loads the Sign in page. A foreign Host header stays rejected | [Tailscale UI](findings/f1-tailscale-ui-2026-11-06.md) |
| GPL source | No public 23.1.b tree. The running kernel config is saved. 188 packages are tagged GPL-2.0 | [GPL request](findings/f1-gpl-source-request-2026-10-29.md) |
| WPS on port 49152 | No demonstrated pre-login bug | [WPS parser](findings/f1-hostapd-wps-parser-2026-11-06.md) |
| LAN surface | Exhaustion pass 2026-11-06/07: every live listener, web handler, and message-taking binary triaged. No unauthenticated RCE demonstrated. 2026-11-07: unauth WAN restart VERIFIED live (`ifup wan` executes with no session), wps_pbcd 58032 loopback protocol decoded (no injection; no pre-onboarding path), domos-qosd live copy = ROM + timestamp (no network listener), kernel sip/h323 ALG parsers VERIFIED packet-reachable from LAN, CUPS queue-dependent test done: anonymous reads/disclosure on live queues, but state ops are 401-walled (earlier write-exposure derivation refuted; opcode mislabels corrected). DPP→shell sink demonstrated with a fabricated ctrl event. A corrected localhost TCP config exchange emitted a genuine 445-character DPP-CONNECTOR (no semicolon) without Wi-Fi frames; the enrollee role was unset, so wps_pbcd did not run it. The shipped hostapd keeps a `;` in the connector text it emits (`DPP-CONNECTOR %s`); C-sign and net-access keys are hex. A frame carrying that connector has not been sent, and a punctuated connector did not create a marker. A router reboot followed an out-of-band chirp attempt; cause undetermined. kernel h323 CVE-2024-26851 trigger FIRED (no crash — masked shift, graceful drop). **Later same night:** sip CVE-2026-23457 Content-Length truncation **VERIFIED with oracle** (2^32+32 truncates → trailer parsed as second SIP message → attacker-chosen expectation/pinhole); h323 decode_choice OOB fired 3× (no crash, silent 1–2 byte heap read class); DecodeQ931 zero-len fired (safe — pointer-wrap guard); RAS decode_int CONS live side-effect oracle VERIFIED: TTL=120 control and one-byte-open-type spill trigger both set conntrack timeout to 119 seconds; the original 19-byte no-tail trigger retained 59 seconds. This confirms the decoder consumed bytes past the declared open type; the packet-end read remains DERIVED from the exact loaded module disassembly because CONFIG_KPROBES/FTRACE/DEBUG_FS are disabled. A separate valid TCP Setup control confirmed Q.931 reachability; the old H.245 videoBitRate recipe was invalid (field is SKIP and wrapper was ReleaseComplete). Helpers do NOT attach to loopback flows, INPUT flows do. Remaining open: independent over-air DPP peer and shell-chain test, plus direct observation of the packet-end read | [miniupnpd/cwmpd pass](findings/f1-miniupnpd-cwmpd-2026-11-06.md) |
| Non-associated WiFi | wl.ko 17.10.251.7305 confirmed live. PSK BSSes are PMF-optional; SAE hunt-and-peck, anti-clog 5, is backhaul `wl0.2` only. Probe-SSID copies in `wlc_probresp_recv_process_prbreq` are clamped to 32. Hostapd returns status 77 for a group outside 19/20/21 and requests an anti-clog token once open SAE sessions reach the configured threshold. No SAE or deauth frame was sent: this Mac cannot open a monitor interface, and `wl1` is 2.4 GHz only. DPP is idle (no bootstrap objects) | [Non-associated WiFi](findings/f1-nonassociated-wifi-surfaces-2026-11-07.md) |
| LCM package channel | Deep audit 2026-11-07: plain-HTTP backend, no auth, per-member RSA-2048 sigs vs `tc_public.pem`, fail-closed. **Demonstrated live**: apps-list substitution (root-controlled) made the router fetch, verify, and install a chosen vendor-signed package at an attacker-chosen DOWNGRADE version — no downgrade protection. Native installer board-cert chain, EFU skip absent. Realistic remote attack: network-position MITM → historical-package install | [LCM deep audit](findings/f1-lcm-package-channel-deep-audit-2026-11-07.md) |
| Closed-case recovery | The boot flag exists. The web action that sets it has not been sent | [Closed-case BOOT-P](findings/f1-closed-case-bootp-2026-11-06.md) |

Usage dashboard refresh: `python3 scripts/f1_usage_snapshot.py`. Index rebuild: `./scripts/report.sh`.

DPP follow-up: [localhost TCP config exchange emitted a 445-character connector; over-air path still open](findings/f1-dpp-radio-emission-pass-2026-11-07.md). The earlier event-to-shell plumbing result used a fabricated ctrl event: [details and limits](findings/f1-dpp-shell-chain-demonstrated-2026-11-07.md).

The live DPP configurator also shares the host user/network namespaces and has `CAP_NET_ADMIN` / `CAP_SYS_ADMIN` with an all-devices LXC cgroup. This raises the impact of a future parser compromise; no namespace escape or DPP exploit was demonstrated.

## Layout

- [Software pass summary](findings/software-pass-summary.md) is the running inventory.
- [API map](findings/f1-api-map.md) is Homeware on port 80, plus the parallel listeners.
- [Tooling](scripts/TOOLING.md) covers language choices and the password-change gate.
- Public board thread: <https://github.com/hack-technicolor/hack-technicolor/issues/321>

## Where to look

**Boot and flash.** [Root this unit again](docs/root-again.md), [UART 23.1.b](findings/f1-uart-23.1b.md), [boot log](findings/f1-boot-log-2026-10-12.md), [BOOT-P on the LAN](findings/f1-bootp-lan-2026-10-13.md), [overlay flash](findings/f1-rootfs-data-overlay-flashing-2026-11-04.md), [live overlay injection](findings/f1-live-overlay-injection-2026-11-06.md), [RTFD and Clash](findings/f1-mount-root-rtfd-and-clash-deconstruction-2026-11-06.md). Mac recovery responder: `scripts/f1_bootp_tftp_mac.py`.

**Keys and images.** [Rootfs key on the boot log](findings/f1-rootfs-key-l598-2026-10-27.md), [config export](findings/f1-config-export-decrypt-2026-10-12.md), [key blocker, superseded](findings/f1-hardware-key-blocker-2026-10-12.md), [19.x notes before the unwrap](findings/gcnt-x-19x-deep.md), [EFU and OSIK](findings/efu-osik-signature-chain-2026-11-02.md).

**LAN services.** [WFA 49152](findings/f1-wfa-wlanconfig-49152-2026-10-12.md), [listener diff](findings/f1-rootfs-diff-listeners-2026-11-06.md), [CUPS](docs/f1-cups-631.md), [session and WPS](findings/auth-session-and-wps-2026-10-12.md), [management boundaries](findings/management-auth-boundaries-2026-10-12.md).

**Kernel ALG experiments.** `scripts/h323_bitmap_trigger.py` and `scripts/h323_ras_cons_trigger.py` build H.323 parser inputs. `scripts/h323_cons_oracle_trigger.py` is a retired invalid draft and refuses to emit packets. See [the live ALG finding](findings/f1-miniupnpd-cwmpd-2026-11-06.md) for demonstrated results and limits.

**UI.** [Grabber](docs/f1-artifact-grabber.md), [hidden modals](findings/f1-ui-audit-hidden-modals-2026-10-29.md), [uploaded HARs](docs/f1-uploaded-hars.md). Password-change blobs are TypeScript only: `scripts/password-encoding/`.
