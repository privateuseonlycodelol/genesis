# genesis

![findings/board-top.jpg](findings/board-top.jpg)

Notes on the Telia F1 I have open. Vantiva board GCNT-X, firmware 23.1.b.0448-7241017-20260223134332.

`findings/` is the writeups. `scripts/` is the tooling. Packet captures go in `artifacts/captures/`. Firmware images go in `artifacts/firmware/`. Those two stay out of git.

`./scripts/wan-capture.sh <iface>` takes a mirror capture and prints any Telia host, `.rbi`, or TLS name it sees. `./scripts/lcm-probe.sh` checks the LCM manifest. `./scripts/report.sh` rebuilds `findings/latest.md`.

Write the sha256 next to an image if you keep one. Don't commit the image.

Public thread for this board: https://github.com/hack-technicolor/hack-technicolor/issues/321

Latest software-only research pass: [verified controls, configuration export, service inventory, and tooling corrections](findings/software-pass-summary.md).
