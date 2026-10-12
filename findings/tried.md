/modals/logviewer-modal.lp — 200 — router log lines, not a shell
/gateway.lp — 200 — Advanced dashboard, not a shell
/modals/wireless-ap-modal-newEM.lp — 200 — wireless AP form, not a shell
/modals/diagnostics-connection-modal.lp — 200 — connection check, not a shell
/modals/diagnostics-network-modal.lp — 200 — port statistics, not log lines
/modals/wanservices-modal.lp — 200 — port mapping form, not a shell
/modals/contentsharing-modal.lp — 200 — Samba and DLNA form, not a shell
/modals/dyndns-wanservices-modal.lp — 200 — DynDNS form, service disabled, not a shell
/modals/system-info-modal.lp — 200 — no SoC, flash chip, or Wi-Fi chip
/modals/system-config-modal.lp — 200 — restart and factory-reset buttons, not a shell
/js/system-config-min.js — 200 — reset and upgrade script; upgrade controls are not on the page
/modals/time-management-modal.lp — 200 — clock and timezone form
/modals/broadband-modal.lp — 200 — Ethernet link status
/modals/internet-modal.lp — 200 — WAN DHCP form
/modals/ethernet-modal.lp — 200 — LAN address form
/modals/firewall-modal.lp — 200 — firewall level form
/modals/device-modal.lp — 200 — client list
/modals/parental-modal.lp — 200 — site-blocking form
/modals/tod-modal.lp — 200 — time-of-day rules
/modals/dmz-modal.lp — 200 — bridge Ethernet port 4 form
/modals/l2tp-ipsec-server-modal.lp — 200 — VPN server form
/modals/diagnostics-ping-modal.lp — 200 — ping form
/modals/diagnostics-igmpproxy-modal.lp — 200 — IGMP statistics
/modals/wireless-radio-modal-newEM.lp — 200 — radio form
/modals/wireless-wps-modal-newEM.lp — 200 — WPS form
/password.lp — 200 — change-password form
/modals/basicview-accesscode-modal.lp — 200 — guided setup form
POST /modals/system-config-modal.lp action=upgradefwstatus — 403 — nginx forbidden HTML, no update or bank JSON
GET /gateway.lp?action=scheduleReboot — 200 — JSON schedule/time fields, no firmware URL
GET /gateway.lp?auto_update=true&getSessionStatus=true — 200 — JSON current_role admin
GET /modals/parental-modal.lp?action=smartwifi — 200 — JSON smartwifi state only
GET /modals/system-config-modal.lp?action=upgradefwstatus — 200 — authenticated configuration HTML modal; no upgrade-status JSON (no success/errorcode fields)
GET /modals/system-config-modal.lp?action=getbanksize — 200 — JSON success true, banksize 134217728 bytes (128 MiB)
Offline summary of five uploaded browser HARs: `docs/f1-uploaded-hars.md`
2026-10-12 CUPS tools — `scripts/cups_ipp_readonly_matrix.py`, `cups_ipp_followup.py`, `cups_ipp_policy_probe.py`; `test_cups_ipp_readonly_matrix.py` (encoder vs prior fixture). See `findings/f1-cups-ipp-policy-2026-10-12.md`.
2026-10-12 CUPS follow-up — ipptool Get-Jobs/completed PASS; get-devices/get-ppds internal error; policy probes (create-local forbidden, no queue from 0x4004); HTTP 503 blocked cupsd logviewer harvest. See `findings/f1-cups-ipp-policy-2026-10-12.md`.
2026-10-12 CUPS :631 unauthenticated read-only IPP matrix (19 POST/GET/HEAD probes, 3 s pacing) — HTTP GET/HEAD pages 403; IPP reads reach handler including Get-Jobs successful-ok empty queue and CUPS-Get-Devices cups-deviced internal error; no job creation. See `findings/f1-cups-ipp-readonly-matrix-2026-10-12.md`.
2026-10-12 07:14 local: authenticated `POST export_config` — 200, 181137-byte config envelope, not a firmware image. Unauthenticated `export_config`, `getbanksize`, and `scheduleReboot` — 200 login HTML, not JSON or an export. Reboot, reset, import, BOOTP, and firmware upload were not sent. See `findings/f1-hidden-action-boundary-2026-10-12.md`.
2026-10-12: WFA WLANConfig :49152 — SSDP→`wps_device.xml`, SCPD, HEAD/GET on `wps_control`/`wps_event`, negative SOAP for `SetSelectedRegistrar` (501), `PutWLANResponse` (600), `PutMessage` (400); no `GetDeviceInfo` in this run. See `findings/f1-wfa-wlanconfig-49152-2026-10-12.md`.
2026-10-12: WFA peer + event follow-up — `GetDeviceInfo` then `PutMessage` wrong M1+matched nonce (500) then `AA==` (400); unauth `SUBSCRIBE` (412/200), `SetSelectedRegistrar` still 501 with active SID, `UNSUBSCRIBE` 200. See same findings file.
2026-10-12: WFA deep — NOTIFY to local CALLBACK (`STAStatus`/`APStatus`/`WLANEvent`); shell M2 `PutMessage` → HTTP 200 + `WSC_NACK` (0x0e) then peer gone (400); `UNSUBSCRIBE` 412 with listener. `scripts/wfa_wlanconfig_deep_probe.py`.
2026-10-12: WFA registrar — after SUBSCRIBE+listener, `SetSelectedRegistrar` `AA==` → 500 (not 501). `scripts/wfa_wlanconfig_registrar_probe.py`.
2026-10-12 offline: `notloggedin.zip` vs `f1-grab-2026-10-12T05-57-18-863Z.zip` — mislabeled; admin session (dashboard + `current_role` JSON + same CSRF as 05:57); 89/102 shared members byte-identical; no new routes or trust-boundary evidence. See `findings/f1-grab-notloggedin-2026-10-12.md`.
2026-10-12: Config export Tier 1 — `THENC`/`GW` envelope verified on three saves; `scripts/decrypt_f1_config_export.py` + `test_decrypt_f1_config_export.py`; decryption **blocked** without per-device `RIP_ID_RANDOM_KEY_B` (`/proc/rip/0108`). See `findings/f1-config-export-decrypt-2026-10-12.md`, `findings/software-pass-config-export.md`.
2026-10-12: Config hardware-key hunt — 37× OSCK files, 55+ header-derived HMAC trials, 119 authenticated GET rip/debug/action probes (`scripts/f1_config_key_probe.py`) — **no** key material; acquisition checklist `scripts/acquire_f1_config_key.sh`. See `findings/f1-hardware-key-blocker-2026-10-12.md`.
2026-10-12 ~08:00 local: after key-probe burst, `/login.lp` and `/` return nginx **503** (190 B) for curl (user terminal confirmed); wait before more live automation. See `findings/f1-ui-leads-23.1b.md`.
