# Tailscale address reaches the login page — 2026-11-06

## Result

**VERIFIED.** Opening `http://100.91.82.75/` returned nginx `401 Authorization Required`. The log line was `sessionmgr.lua:251 preventDNSRebind`, client `127.0.0.1`, host `100.91.82.75`. Userspace Tailscale forwards that connection to local nginx. `web.check_host` only treated LAN addresses and the system hostname as this router, so the Tailscale address was rejected before the login page.

The overlay copy `/usr/lib/lua/web/check_host.lua` (`scripts/genesis/check_host.lua`) also accepts the addresses from `tailscale ip` and this node's MagicDNS name. The nginx worker runs as `nobody` and could not execute the CLI while `/genesis/tailscale` was mode `700`. That directory is now mode `711`. `tailscaled.state` stayed mode `600`.

After the nginx reload:

- `GET http://100.91.82.75/` is `200`. The body is the Sign in page.
- The same request with `Host: openwrt.tailc8804.ts.net` is `200`.
- `Host: evil.example` on the LAN address stays `401`.
- `GET http://192.168.1.1/` stays `200`.
- `dnsproxy` stayed pid `8717`.

## What was not shown

A signed-in session over Tailscale. The web admin password is still required. HTTPS presents the existing Technicolor certificate, so the browser warns. One direct request to the MagicDNS name from this Mac did not connect. The name is accepted when it arrives as the Host header.
