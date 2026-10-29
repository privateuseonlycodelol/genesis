# Genesis report

**Generated:** 2026-10-29T18:19:54Z
**Host:** (omitted)

## Owned-unit boot evidence
- [Detailed UART review](f1-boot-log-2026-10-12.md) · [redacted line-indexed evidence](f1-boot-log-2026-10-12-evidence.md) — AArch64 4.19.235, UBI/verity/AES-XTS root; no shell/root/key recovery shown; old 4.1.52 module does not match
- This report is a generated index, not independent evidence. Raw UART logs stay private under artifacts/uart/.

## UI grab reviews (newest first)
- [`f1-grab-notloggedin-2026-10-12.md`](f1-grab-notloggedin-2026-10-12.md) — `notloggedin.zip` is admin duplicate of ~05:57 grab, not logged-out
- [`f1-grab-045648-review.md`](f1-grab-045648-review.md) — finished 04:56:48Z zip; verbatim bodies; GET JSON
- [`f1-grab-040001-review.md`](f1-grab-040001-review.md) — script repair vs 03:38
- [`f1-grab-033853-review.md`](f1-grab-033853-review.md) — integrity, crypto, runtime map

## LAN surfaces (non–port-80)
- **CUPS :631** — [`docs/f1-cups-631.md`](../docs/f1-cups-631.md) · [`f1-cups-ipp-policy-2026-10-12.md`](f1-cups-ipp-policy-2026-10-12.md) · [`f1-cups-ipp-readonly-matrix-2026-10-12.md`](f1-cups-ipp-readonly-matrix-2026-10-12.md)
- **WFA WLANConfig :49152** — [`f1-wfa-wlanconfig-49152-2026-10-12.md`](f1-wfa-wlanconfig-49152-2026-10-12.md)
- **Listener inventory** — [`management-auth-boundaries-2026-10-12.md`](management-auth-boundaries-2026-10-12.md)

## `artifacts/firmware`
```
total 64008
drwxr-xr-x   7 user  staff       224 Oct 27 19:51 .
drwxr-xr-x  23 user  staff       736 Oct 29 17:49 ..
-rw-r--r--@  1 user  staff  32759365 Oct 11 05:48 REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi
-rw-r--r--@  1 user  staff       179 Oct 27 18:22 test-fit-minimal.itb
-rw-r--r--@  1 user  staff       710 Oct 27 19:07 test-fit-standard-compact.itb
-rw-r--r--@  1 user  staff       885 Oct 27 19:07 test-fit-standard.itb
drwxr-xr-x@ 11 user  staff       352 Oct 27 19:51 vendor-uboot-bcmbca-5.04behnd
```

## `artifacts/captures`
```
total 31104
drwxr-xr-x   7 user  staff      224 Oct 11 17:46 .
drwxr-xr-x  23 user  staff      736 Oct 29 17:49 ..
-rw-------   1 user  staff     1708 Oct 11 05:39 f1-reboot.pcapng
-rw-r--r--   1 user  staff      335 Oct 11 08:01 wan.pcapng
-rw-r--r--   1 user  staff   926664 Oct 11 17:46 wan2-real.pcapng
-rw-r--r--   1 user  staff  9635526 Oct 11 17:41 wan2.pcapng
-rw-r--r--   1 user  staff  5347036 Oct 11 07:02 want.pcapng
```

## `artifacts/logs`
```
total 296
drwxr-xr-x  27 user  staff    864 Oct 12 21:24 .
drwxr-xr-x  23 user  staff    736 Oct 29 17:49 ..
-rw-r--r--@  1 user  staff  49359 Oct 11 05:48 REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.png
drwxr-xr-x@  3 user  staff     96 Oct 11 09:02 _REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.extracted
-rw-r--r--@  1 user  staff    231 Oct 11 09:02 binwalk-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.txt
-rw-r--r--@  1 user  staff    410 Oct 11 05:48 binwalk-reference-rbi-extra.txt
-rw-r--r--@  1 user  staff     82 Oct 11 05:48 binwalk-reference-rbi.txt
-rw-r--r--@  1 user  staff    320 Oct 11 09:05 decrypt-attempt-19x.txt
-rw-r--r--@  1 user  staff   4858 Oct 11 09:09 decrypt-attempt2.txt
-rw-r--r--@  1 user  staff   4223 Oct 12 09:20 decrypt-attempt3.txt
-rw-r--r--@  1 user  staff   1042 Oct 12 21:44 ipping-host-deferred-20261012T212441Z.log
-rw-r--r--   1 user  staff     53 Oct 11 05:41 lcm-23.1.b.json
-rw-r--r--   1 user  staff     51 Oct 11 05:41 lcm-23.1.json
-rw-r--r--@  1 user  staff   3266 Oct 12 09:26 r2secr-build-20261012T072638Z.txt
-rw-r--r--@  1 user  staff   2525 Oct 11 05:48 rbi-download-attempts.txt
-rw-r--r--@  1 user  staff   1880 Oct 11 09:02 rbi-inspect-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.txt
-rw-r--r--@  1 user  staff   1514 Oct 11 05:48 rbi-inspect.txt
-rw-r--r--@  1 user  staff   4339 Oct 12 04:22 software-pass-capture-selftest.txt
-rw-r--r--@  1 user  staff    968 Oct 12 04:27 software-pass-crypto-validation.txt
-rw-------@  1 user  staff    271 Oct 12 04:28 software-pass-dns.json
drwx------@  7 user  staff    224 Oct 12 04:16 software-pass-http-services
-rw-------@  1 user  staff     48 Oct 12 04:18 software-pass-ipv6-default.private.json
-rw-r--r--@  1 user  staff    433 Oct 12 04:27 software-pass-related-csrf.txt
-rw-------@  1 user  staff     59 Oct 12 04:15 software-pass-router-ipv6.private.json
-rw-r--r--@  1 user  staff    937 Oct 12 04:15 software-pass-router-tcp.txt
drwx------@  7 user  staff    224 Oct 12 04:17 software-pass-ssdp
-rw-r--r--@  1 user  staff    125 Oct 11 09:02 verify-squashfs-19x-reference.txt
```

## RBI checksums
```
2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de  artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi
```

## LCM probe JSON
### `lcm-23.1.b.json`
```json
{"error":"Apps was not found GCNT-X 23.1.b f1_1.0-1"}```

### `lcm-23.1.json`
```json
{"error":"Apps was not found GCNT-X 23.1 f1_1.0-1"}```

## Findings
- [`acs-telia-8888-probe-2026-10-28.md`](acs-telia-8888-probe-2026-10-28.md)
- [`admin-url-hunt.md`](admin-url-hunt.md)
- [`auth-session-and-wps-2026-10-12.md`](auth-session-and-wps-2026-10-12.md)
- [`cups-http-ipp-source-boundary.md`](cups-http-ipp-source-boundary.md)
- [`decomp-kickoff.md`](decomp-kickoff.md)
- [`f1-advanced-ui.md`](f1-advanced-ui.md)
- [`f1-aggressive-software-pass-2026-10-12.md`](f1-aggressive-software-pass-2026-10-12.md)
- [`f1-api-map.md`](f1-api-map.md)
- [`f1-board-visual-2026-10-12.md`](f1-board-visual-2026-10-12.md)
- [`f1-boot-log-2026-10-12-evidence.md`](f1-boot-log-2026-10-12-evidence.md)
- [`f1-boot-log-2026-10-12.md`](f1-boot-log-2026-10-12.md)
- [`f1-boot-menu-a-key-2026-10-27.md`](f1-boot-menu-a-key-2026-10-27.md)
- [`f1-bootp-lan-2026-10-13.md`](f1-bootp-lan-2026-10-13.md)
- [`f1-bypass-crypto-options.md`](f1-bypass-crypto-options.md)
- [`f1-config-export-decrypt-2026-10-12.md`](f1-config-export-decrypt-2026-10-12.md)
- [`f1-cups-ipp-policy-2026-10-12.md`](f1-cups-ipp-policy-2026-10-12.md)
- [`f1-cups-ipp-readonly-matrix-2026-10-12.md`](f1-cups-ipp-readonly-matrix-2026-10-12.md)
- [`f1-diagnostics-connection-restart-2026-10-12.md`](f1-diagnostics-connection-restart-2026-10-12.md)
- [`f1-export-log-modal-2026-10-28.md`](f1-export-log-modal-2026-10-28.md)
- [`f1-firmware-acquisition-paths-2026-10-27.md`](f1-firmware-acquisition-paths-2026-10-27.md)
- [`f1-firmware-session-index-2026-10-27.md`](f1-firmware-session-index-2026-10-27.md)
- [`f1-fit-rootfs-packaging-2026-10-27.md`](f1-fit-rootfs-packaging-2026-10-27.md)
- [`f1-gap-attack-pass-2026-10-12.md`](f1-gap-attack-pass-2026-10-12.md)
- [`f1-gateway-url-action-2026-10-12.md`](f1-gateway-url-action-2026-10-12.md)
- [`f1-gpl-source-request-2026-10-29.md`](f1-gpl-source-request-2026-10-29.md)
- [`f1-grab-033853-auth-crypto.md`](f1-grab-033853-auth-crypto.md)
- [`f1-grab-033853-integrity.md`](f1-grab-033853-integrity.md)
- [`f1-grab-033853-review.md`](f1-grab-033853-review.md)
- [`f1-grab-033853-runtime.md`](f1-grab-033853-runtime.md)
- [`f1-grab-033853-ui-surfaces.md`](f1-grab-033853-ui-surfaces.md)
- [`f1-grab-040001-coverage.md`](f1-grab-040001-coverage.md)
- [`f1-grab-040001-fidelity.md`](f1-grab-040001-fidelity.md)
- [`f1-grab-040001-review.md`](f1-grab-040001-review.md)
- [`f1-grab-040001-runtime-delta.md`](f1-grab-040001-runtime-delta.md)
- [`f1-grab-045648-review.md`](f1-grab-045648-review.md)
- [`f1-grab-csrf-redaction-corruption.md`](f1-grab-csrf-redaction-corruption.md)
- [`f1-grab-notloggedin-2026-10-12.md`](f1-grab-notloggedin-2026-10-12.md)
- [`f1-har-coverage-2026-10-12.md`](f1-har-coverage-2026-10-12.md)
- [`f1-har-wanetc-2026-10-12.md`](f1-har-wanetc-2026-10-12.md)
- [`f1-hardware-key-blocker-2026-10-12.md`](f1-hardware-key-blocker-2026-10-12.md)
- [`f1-hidden-action-boundary-2026-10-12.md`](f1-hidden-action-boundary-2026-10-12.md)
- [`f1-internet-outage-2026-10-28.md`](f1-internet-outage-2026-10-28.md)
- [`f1-ipping-helper-2026-10-12.md`](f1-ipping-helper-2026-10-12.md)
- [`f1-ipping-host-2026-10-12.md`](f1-ipping-host-2026-10-12.md)
- [`f1-js-deep-2026-10-12.md`](f1-js-deep-2026-10-12.md)
- [`f1-kernel-rip-keystore-decomp-2026-10-29.md`](f1-kernel-rip-keystore-decomp-2026-10-29.md)
- [`f1-logviewer.md`](f1-logviewer.md)
- [`f1-nand-read-plan-2026-10-27.md`](f1-nand-read-plan-2026-10-27.md)
- [`f1-password-encoding-cli-trace-2026-10-15.md`](f1-password-encoding-cli-trace-2026-10-15.md)
- [`f1-rea-har-pass-2026-10-17.md`](f1-rea-har-pass-2026-10-17.md)
- [`f1-research-composite-2026-10-13.md`](f1-research-composite-2026-10-13.md)
- [`f1-rootfs-key-l598-2026-10-27.md`](f1-rootfs-key-l598-2026-10-27.md)
- [`f1-software-link-hunt-2026-10-29.md`](f1-software-link-hunt-2026-10-29.md)
- [`f1-trace-helper-2026-10-12.md`](f1-trace-helper-2026-10-12.md)
- [`f1-trace-path-2026-10-12.md`](f1-trace-path-2026-10-12.md)
- [`f1-uart-23.1b.md`](f1-uart-23.1b.md)
- [`f1-uart-interaction-2026-10-12.md`](f1-uart-interaction-2026-10-12.md)
- [`f1-uboot-source-trace-2026-10-27.md`](f1-uboot-source-trace-2026-10-27.md)
- [`f1-ui-grab-2026-10-12.md`](f1-ui-grab-2026-10-12.md)
- [`f1-ui-leads-23.1b.md`](f1-ui-leads-23.1b.md)
- [`f1-unturned-stones-2026-10-29.md`](f1-unturned-stones-2026-10-29.md)
- [`f1-usp-ipping-2026-10-12.md`](f1-usp-ipping-2026-10-12.md)
- [`f1-wfa-wlanconfig-49152-2026-10-12.md`](f1-wfa-wlanconfig-49152-2026-10-12.md)
- [`f1-wireless-qrcode-context-2026-10-12.md`](f1-wireless-qrcode-context-2026-10-12.md)
- [`gcnt-x-19x-deep.md`](gcnt-x-19x-deep.md)
- [`gcnt-x-public-hardware.md`](gcnt-x-public-hardware.md)
- [`gcnt-x-root-path.md`](gcnt-x-root-path.md)
- [`l598-key-xts-19x-rbi-2026-10-27.md`](l598-key-xts-19x-rbi-2026-10-27.md)
- [`management-auth-boundaries-2026-10-12.md`](management-auth-boundaries-2026-10-12.md)
- [`management-offline-service-evidence.md`](management-offline-service-evidence.md)
- [`mirror-test.md`](mirror-test.md)
- [`r2secr-build-2026-10-12.md`](r2secr-build-2026-10-12.md)
- [`rbi-crypto-attempt2.md`](rbi-crypto-attempt2.md)
- [`rbi-crypto-attempt3.md`](rbi-crypto-attempt3.md)
- [`rbi-crypto-debug.md`](rbi-crypto-debug.md)
- [`rbi-url-hunt-deeper-2026-10-28.md`](rbi-url-hunt-deeper-2026-10-28.md)
- [`session-source-availability-boundary.md`](session-source-availability-boundary.md)
- [`software-pass-capture-review.md`](software-pass-capture-review.md)
- [`software-pass-config-export.md`](software-pass-config-export.md)
- [`software-pass-crypto-validation.md`](software-pass-crypto-validation.md)
- [`software-pass-har7-js.md`](software-pass-har7-js.md)
- [`software-pass-har7-review.md`](software-pass-har7-review.md)
- [`software-pass-live-access.md`](software-pass-live-access.md)
- [`software-pass-request-review.md`](software-pass-request-review.md)
- [`software-pass-source-comparison.md`](software-pass-source-comparison.md)
- [`software-pass-summary.md`](software-pass-summary.md)
- [`tried.md`](tried.md)
- [`wan-pcap.md`](wan-pcap.md)
- [`wan2-tagged-frames.md`](wan2-tagged-frames.md)
- [`want-pcap.md`](want-pcap.md)
- [`wps-upnp-source-boundary.md`](wps-upnp-source-boundary.md)

## 19.x reference RBI (offline)
### attempt3 (boot-log derivations, latest)
```
decrypt_success: False
structural_scan:
  file_len: 32759365
  data_off + data_size: 32759365
  trailing_after_payload: 0
  BLI2_magic_offsets_first_1MiB: []
  zip_local_in_header_region: offset none
  gzip_in_header_region: offset none
  bli2_in_hdr_in_header_region: offset 0
  payload_prefix_hex: b74d5554450a01f3dcd09d50b329960e9b36866678955644375473aecc3addb038ac44ed75d194166aa5e2683868e079aa386f5cf5c294cf2f7d211858ed5e94
  header_gap_0x104: no obvious cleartext PEM/ssh
note: no trial passed B7 OSCK unwrap (bad_osck); GCNT-X.osck not published
```

### attempt2
```
decrypt_success: False
structural_scan:
  file_len: 32759365
  data_off + data_size: 32759365
  trailing_after_payload: 0
  BLI2_magic_offsets_first_1MiB: []
  zip_local_in_header_region: offset none
  gzip_in_header_region: offset none
  bli2_in_hdr_in_header_region: offset 0
  payload_prefix_hex: b74d5554450a01f3dcd09d50b329960e9b36866678955644375473aecc3addb038ac44ed75d194166aa5e2683868e079aa386f5cf5c294cf2f7d211858ed5e94
  header_gap_0x104: no obvious cleartext PEM/ssh
note: no trial passed B7 OSCK unwrap (bad_osck); GCNT-X.osck not published
```

### attempt1 (57-key baseline)
```
keys_tried: 57
  community_osck_files: 37
  derived_candidates: 47
status_histogram: {'bad_osck': 57}
decrypt_success: False
note: no trial passed B7 OSCK unwrap (bad_osck); GCNT-X.osck not published
```

Deep dive: `findings/gcnt-x-19x-deep.md` · Crypto: `findings/rbi-crypto-attempt3.md` · r2secr: `findings/r2secr-build-2026-10-12.md` · Root path (lab): `findings/gcnt-x-root-path.md`

