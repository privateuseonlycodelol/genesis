# Root this F1 again

Use this when SSH to this GCNT-X is gone and the bootloader is still the 23.1.b one that prints `Press b to enter BOOT-P`. That is the path that produced `uid=0` on 2026-11-06. It is serial plus one overlay volume. It is not a LAN login and it is not closed-case.

The write replaces `rootfs_data`. DNS, the plugin page, the skin, and the current root password live on that volume, so they go away with it. The copies under `/airties-edge/genesis/` were not shown to bring SSH back by themselves.

## Do not flash these

An unsigned `bootfs` makes U-Boot wipe keys and hang. The bundle builder leaves `bootfs`, `rootfs`, and `loader` out. Do not add them.

Do not flash `REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi` or `GCNT-X-23.1.b-bank*.itb`. A bank-only upgrade can erase the overlay you just wrote.

## What has to be plugged in

- USB serial on the UART already used: router TX to adapter RX, adapter TX to router RX, shared ground, adapter power pin disconnected. 115200 8N1. Last device was `/dev/cu.usbserial-0001`. Check `ls /dev/cu.usbserial*` if the name changed. Capture helper: `bash scripts/f1-boot-capture.command`.
- USB Ethernet from the Mac to a LAN port. Last interface was `en10` (ASIX). The Mac must be on `192.168.1.0/24`. A phone hotspot (`172.20.10.0/24`) is the wrong network.
- Tailscale must not own `192.168.1.0/24`. `route get 192.168.1.1` has to leave through `en10`, not `utun`. That collision is what made earlier BOOTP replies miss the router.

## 1. Rebuild the overlay

`tools/bin/mkfs.ubifs` has to exist. If it does not, build it with `tools/patches/build_mkfs_ubifs_macos.sh`.

```sh
python3 scripts/build_f1_overlay_bundle.py
```

That stages both bank trees, builds `artifacts/firmware/rootfs_data.ubifs`, and packs `artifacts/firmware/overlay-injection-bundle.itb`. The script stops if validation reports an error or a warning. The image stays under `artifacts/` and is not committed.

The piece that actually opened the console is the overlay copy of `restricted_shell`, which `scripts/generate_f1_overlay.py` writes over the stock binary. `procd` reads `/rom/etc/inittab` before the overlay is mounted, so the staged `inittab` line does not replace the console by itself. The first flash still landed in `restricted_shell`. The second flash, with `b` sent once, opened BusyBox ash as root.

## 2. Serve it once

Start the responder before the reboot. The run that opened the shell was:

```sh
python3 scripts/f1_bootp_tftp_mac.py \
  --iface en10 \
  --no-set-ip \
  --no-pcap \
  --allow-non-root \
  --timeout 300 \
  --uart /dev/cu.usbserial-0001 \
  --file artifacts/firmware/overlay-injection-bundle.itb \
  --reboot
```

`--reboot` asks the web UI to restart. If the admin page is down, leave that flag off and power-cycle after the script is listening. UDP 67 and 69 are the BOOTP and TFTP ports. If the process cannot bind them, run it with `sudo` and drop `--allow-non-root`.

The log should show one `SENT 'b'`, a full TFTP ACK run (the working image was 27,283 blocks), a SHA-256 check, and a write to volume `rootfs_data`. Then stop the script. The earlier run pressed `b` again on the next boot, got `BOOTP Reply timeout`, and reset. One press is enough.

A successful log from that day is `artifacts/bootp/sessions/session-20261106-192838.log`.

## 3. Turn the serial root shell into SSH

Press Enter on the serial line. The working result was `uid=0(root)` and a `root@OpenWrt` prompt. If you still get the stock restricted shell, the overlay did not mount. Do not keep flashing other images. Read the UART log for `rootfs_data` and stop.

From that root prompt, `/etc/passwd` already said `/bin/sh`, and `/etc/shells` listed only `/bin/ash` and `/bin/restricted_shell`. Dropbear rejected SSH with `User 'root' has invalid shell` until `/bin/sh` was appended to `/etc/shells`. Then `chpasswd` set the root password. Keep that password in `artifacts/secrets/f1-root.password` (mode 0600). It is not the web admin password, and it does not belong in git.

```sh
grep -qx /bin/sh /etc/shells || echo /bin/sh >> /etc/shells
passwd
```

From the Mac, on the LAN:

```sh
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no root@192.168.1.1
```

`id` should print `uid=0(root)`.

## 4. Put the lab back

SSH is the root. The DNS proxy, telemetry stops, skin, and `/genesis/` settings page are a later install: `scripts/genesis/install.sh`. The DoH URL stays in `/etc/doh-rilah.url` on the router. Do not copy it into the repo.

## When this will not work

- `rtfd --all`, or an upgrade package that deletes and recreates `rootfs_data`, removes the overlay. Run this guide again.
- A newer bootloader that drops the `Press b` prompt, or that refuses an unsigned `rootfs_data`, is a different problem. This guide does not cover it.
- The web action that sets the BOOT-P flag was never sent. Do not treat it as a tested substitute for the serial cable.
