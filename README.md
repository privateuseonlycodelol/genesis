# genesis — Telia F1 GCNT-X firmware RE

Device: Telia F1, GCNT-X, FW `23.1.b.0448-7241017-20260223134332`

After any step run `./scripts/report.sh` — tell Project **check genesis**

1. Put captures in `artifacts/captures/`, firmware in `artifacts/firmware/`.
2. `./scripts/wan-capture.sh <iface>` — SG108E mirror capture + telia/rbi/SNI summary.
3. `./scripts/lcm-probe.sh` — optional LCM manifest probe.
4. Record sha256 in `findings/`.

Never commit firmware blobs. See [hack-technicolor #321](https://github.com/hack-technicolor/hack-technicolor/issues/321).
