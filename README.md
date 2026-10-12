# genesis

![findings/board-top.jpg](findings/board-top.jpg)

Notes on the Telia F1 I have open. Vantiva board GCNT-X, firmware 23.1.b.0448-7241017-20260223134332.

`findings/` is the writeups. `scripts/` is the tooling. Browser UI harvest: [`docs/f1-artifact-grabber.md`](docs/f1-artifact-grabber.md) (Tampermonkey userscript in `scripts/f1-grab-artifacts.user.js`). Packet captures go in `artifacts/captures/`. Firmware images go in `artifacts/firmware/`. Those two stay out of git.

`./scripts/wan-capture.sh <iface>` takes a mirror capture and prints any Telia host, `.rbi`, or TLS name it sees. `./scripts/lcm-probe.sh` checks the LCM manifest. `./scripts/report.sh` rebuilds `findings/latest.md`.

Write the sha256 next to an image if you keep one. Don't commit the image.

Public thread for this board: https://github.com/hack-technicolor/hack-technicolor/issues/321

Latest software-only research pass: [verified controls, configuration export, service inventory, and tooling corrections](findings/software-pass-summary.md).

Configuration export (`export_config`): format and decrypt tooling are documented in [f1-config-export-decrypt-2026-10-12.md](findings/f1-config-export-decrypt-2026-10-12.md). Decryption needs **64-byte** `RIP_ID_RANDOM_KEY_B` from the device (`scripts/decrypt_f1_config_export.py`, `scripts/acquire_f1_config_key.sh`). UI/key-surface sweep and blockers: [f1-hardware-key-blocker-2026-10-12.md](findings/f1-hardware-key-blocker-2026-10-12.md).

WFA WLANConfig on LAN TCP **49152** (WPS over UPnP, paced probes, no demonstrated exploit): [findings/f1-wfa-wlanconfig-49152-2026-10-12.md](findings/f1-wfa-wlanconfig-49152-2026-10-12.md). Drivers: `scripts/wfa_wlanconfig_probe.py`, `wfa_wlanconfig_peer_probe.py`, `wfa_wlanconfig_event_probe.py`, `wfa_wlanconfig_deep_probe.py`, `wfa_wlanconfig_registrar_probe.py` (plus `scripts/wps_device_info.py` for `GetDeviceInfo`).

CUPS on LAN TCP **631** (HTTP **403**, unauthenticated IPP reads on empty queue; no demonstrated admin/write): [docs/f1-cups-631.md](docs/f1-cups-631.md) → [findings/f1-cups-ipp-policy-2026-10-12.md](findings/f1-cups-ipp-policy-2026-10-12.md), [f1-cups-ipp-readonly-matrix-2026-10-12.md](findings/f1-cups-ipp-readonly-matrix-2026-10-12.md). Drivers: `scripts/cups_ipp_readonly_matrix.py`, `cups_ipp_followup.py`, `cups_ipp_policy_probe.py`.

Config export scripts: `scripts/decrypt_f1_config_export.py`, `scripts/test_decrypt_f1_config_export.py`, `scripts/inspect_config_export_header.py`, `scripts/f1_config_key_probe.py` (paced rip/debug GET sweep — **do not** rerun at volume; caused **503**), `scripts/acquire_f1_config_key.sh` (on-router checklist after root).

Latest supplied UI archive review: [04:56:48Z grab — Wi-Fi card JSON, guest LAN, NTP, and finished modal coverage](findings/f1-grab-045648-review.md). The file `notloggedin.zip` (2026-10-12) is **not** an unauthenticated capture — it duplicates the ~05:57 admin session; see [notloggedin review](findings/f1-grab-notloggedin-2026-10-12.md). Earlier: [04:00:01 versus 03:38:53](findings/f1-grab-040001-review.md) and the [03:38:53 evidence map](findings/f1-grab-033853-review.md). Grabber behavior and known tooling gaps: [`docs/f1-artifact-grabber.md`](docs/f1-artifact-grabber.md).
