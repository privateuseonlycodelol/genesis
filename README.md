# Genesis

Research notes for an owned Telia F1. Vantiva board GCNT-X, firmware 23.1.b.

`findings/` holds the write-ups. `scripts/` holds the tools. Firmware images, captures, and secrets stay in `artifacts/` and are not committed. Record a SHA-256 beside any image you keep.

The 2026-10-27 note that recovery flashing needs no vendor signature is overstated. That run skipped every bundle member, so nothing was written. An unsigned `bootfs` still hangs this board. See [BOOT-P LAN, Addendum 9](findings/f1-bootp-lan-2026-10-13.md) and [FIT packaging](findings/f1-fit-rootfs-packaging-2026-10-27.md).

## Current state

| Topic | Status | Note |
| --- | --- | --- |
| Root | Overlay SSH, after one serial recovery | [Quadruple-vector flash](findings/f1-quad-overlay-flash-2026-11-06.md) |
| Signed boot | Vendor `bootfs` is checked. `rootfs_data` is not | [FLD gate](findings/f1-uboot-fld-secure-boot-gate-2026-11-04.md) |
| Flash and OSCK | Both banks and the 19.x reference image unwrap. Do not flash the 19.x image | [Flash volumes](findings/f1-flash-volumes-2026-11-06.md) |
| LAN DNS | dnsmasq forwards to a local DoH proxy for `dns.rilah.app`. The URL is only on the router | [DNS and phone-home](findings/f1-doh-and-tracking-2026-11-06.md) |
| Idle services | Usage meter and Airties `cloud-comm` disabled. `cwmpd` stopped. Telia MQTT still up. Wi-Fi left up | [Idle services](findings/f1-idle-services-stopped-2026-11-06.md), [reset parking lot](findings/f1-reset-persistence-2026-11-06.md) |
| Reset | Parking lot re-seeded across an unplanned reboot. A button reset is still untested. `rtfd --all` still wipes it | [Reset parking lot](findings/f1-reset-persistence-2026-11-06.md) |
| Upgrade wipe | A restore script is on the `opt` volume, which the flasher does not name. The launcher was left dormant and has not been shown running it | [Opt restore](findings/f1-opt-keep-root-2026-11-06.md) |
| WPS on port 49152 | No demonstrated pre-login bug | [WPS parser](findings/f1-hostapd-wps-parser-2026-11-06.md) |
| Closed-case recovery | The boot flag exists. The web action that sets it has not been sent | [Closed-case BOOT-P](findings/f1-closed-case-bootp-2026-11-06.md) |

Usage dashboard refresh: `python3 scripts/f1_usage_snapshot.py`. Index rebuild: `./scripts/report.sh`.

## Layout

- [Software pass summary](findings/software-pass-summary.md) is the running inventory.
- [API map](findings/f1-api-map.md) is Homeware on port 80, plus the parallel listeners.
- [Tooling](scripts/TOOLING.md) covers language choices and the password-change gate.
- Public board thread: <https://github.com/hack-technicolor/hack-technicolor/issues/321>

## Where to look

**Boot and flash.** [UART 23.1.b](findings/f1-uart-23.1b.md), [boot log](findings/f1-boot-log-2026-10-12.md), [BOOT-P on the LAN](findings/f1-bootp-lan-2026-10-13.md), [overlay flash](findings/f1-rootfs-data-overlay-flashing-2026-11-04.md), [live overlay injection](findings/f1-live-overlay-injection-2026-11-06.md), [RTFD and Clash](findings/f1-mount-root-rtfd-and-clash-deconstruction-2026-11-06.md). Mac recovery responder: `scripts/f1_bootp_tftp_mac.py`.

**Keys and images.** [Rootfs key on the boot log](findings/f1-rootfs-key-l598-2026-10-27.md), [config export](findings/f1-config-export-decrypt-2026-10-12.md), [key blocker, superseded](findings/f1-hardware-key-blocker-2026-10-12.md), [19.x notes before the unwrap](findings/gcnt-x-19x-deep.md), [EFU and OSIK](findings/efu-osik-signature-chain-2026-11-02.md).

**LAN services.** [WFA 49152](findings/f1-wfa-wlanconfig-49152-2026-10-12.md), [listener diff](findings/f1-rootfs-diff-listeners-2026-11-06.md), [CUPS](docs/f1-cups-631.md), [session and WPS](findings/auth-session-and-wps-2026-10-12.md), [management boundaries](findings/management-auth-boundaries-2026-10-12.md).

**UI.** [Grabber](docs/f1-artifact-grabber.md), [hidden modals](findings/f1-ui-audit-hidden-modals-2026-10-29.md), [uploaded HARs](docs/f1-uploaded-hars.md). Password-change blobs are TypeScript only: `scripts/password-encoding/`.
