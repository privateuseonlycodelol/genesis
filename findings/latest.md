# Genesis report

**Generated:** 2026-10-11T15:46:08Z
**Host:** MacBook-Pro-som-tillhor-Nils

## `artifacts/firmware`
```
total 63984
drwxr-xr-x  3 nils  staff        96 okt. 11 05:48 .
drwxr-xr-x  7 nils  staff       224 okt. 11 09:01 ..
-rw-r--r--@ 1 nils  staff  32759365 okt. 11 05:48 REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi
```

## `artifacts/captures`
```
total 31104
drwxr-xr-x  7 nils  staff      224 okt. 11 17:46 .
drwxr-xr-x  7 nils  staff      224 okt. 11 09:01 ..
-rw-------  1 nils  staff     1708 okt. 11 05:39 f1-reboot.pcapng
-rw-r--r--  1 nils  staff      335 okt. 11 08:01 wan.pcapng
-rw-r--r--  1 nils  staff   926664 okt. 11 17:46 wan2-real.pcapng
-rw-r--r--  1 nils  staff  9635526 okt. 11 17:41 wan2.pcapng
-rw-r--r--  1 nils  staff  5347036 okt. 11 07:02 want.pcapng
```

## `artifacts/logs`
```
total 200
drwxr-xr-x@  3 nils  staff     96 okt. 11 09:02 _REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.extracted
drwxr-xr-x  15 nils  staff    480 okt. 11 09:09 .
drwxr-xr-x   7 nils  staff    224 okt. 11 09:01 ..
-rw-r--r--@  1 nils  staff    231 okt. 11 09:02 binwalk-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.txt
-rw-r--r--@  1 nils  staff    410 okt. 11 05:48 binwalk-reference-rbi-extra.txt
-rw-r--r--@  1 nils  staff     82 okt. 11 05:48 binwalk-reference-rbi.txt
-rw-r--r--@  1 nils  staff    320 okt. 11 09:05 decrypt-attempt-19x.txt
-rw-r--r--@  1 nils  staff   4858 okt. 11 09:09 decrypt-attempt2.txt
-rw-r--r--   1 nils  staff     53 okt. 11 05:41 lcm-23.1.b.json
-rw-r--r--   1 nils  staff     51 okt. 11 05:41 lcm-23.1.json
-rw-r--r--@  1 nils  staff   2525 okt. 11 05:48 rbi-download-attempts.txt
-rw-r--r--@  1 nils  staff   1880 okt. 11 09:02 rbi-inspect-REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.txt
-rw-r--r--@  1 nils  staff   1514 okt. 11 05:48 rbi-inspect.txt
-rw-r--r--@  1 nils  staff  49359 okt. 11 05:48 REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi.png
-rw-r--r--@  1 nils  staff    125 okt. 11 09:02 verify-squashfs-19x-reference.txt
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
- [`admin-url-hunt.md`](findings/admin-url-hunt.md)
- [`decomp-kickoff.md`](findings/decomp-kickoff.md)
- [`f1-uart-23.1b.md`](findings/f1-uart-23.1b.md)
- [`f1-ui-leads-23.1b.md`](findings/f1-ui-leads-23.1b.md)
- [`gcnt-x-19x-deep.md`](findings/gcnt-x-19x-deep.md)
- [`gcnt-x-root-path.md`](findings/gcnt-x-root-path.md)
- [`mirror-test.md`](findings/mirror-test.md)
- [`rbi-crypto-attempt2.md`](findings/rbi-crypto-attempt2.md)
- [`rbi-crypto-debug.md`](findings/rbi-crypto-debug.md)
- [`wan-pcap.md`](findings/wan-pcap.md)
- [`wan2-tagged-frames.md`](findings/wan2-tagged-frames.md)
- [`want-pcap.md`](findings/want-pcap.md)

## 19.x reference RBI (offline)
### attempt2 (latest)
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

Deep dive: `findings/gcnt-x-19x-deep.md` · Crypto: `findings/rbi-crypto-attempt2.md` · Root path (lab): `findings/gcnt-x-root-path.md`

