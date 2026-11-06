# Plugin supervisor — 2026-11-06

One foreground loop owns the overlay plugins. The page is `/genesis/` on the existing nginx, after a normal admin login. The signed templates were not replaced.

## Layout

| Plugin | Kind | What it is |
| --- | --- | --- |
| DNS | service | `dnsproxy` with the existing `/etc/dnsproxy.yaml`. The supervisor restarts it if `example.com` through `127.0.0.1` fails for about a minute, and if the public address of `dns.rilah.app` from `9.9.9.9` changes. Same intervals as the retired watcher. The URL file is not in the plugin directory. |
| Diagnostics | tool | Lookup and usage run when the button is pressed. Nothing stays running. |
| Redesign | files | `genesis.css` and the nginx skin filter. |
| Telemetry | enforce | Keeps the usage meter, `cwmpd`, and Telia MQTT stopped. `cloud-comm` stays disabled in the Airties file. Allow puts the start links back and does not restart the Wi-Fi launcher. |

Repo copies: `scripts/genesis/`. Install from the repo with `scripts/genesis/install.sh`. The web rule that lets those paths through the session check is `scripts/genesis/allow-web.sh`.

## Live

**VERIFIED, 22:10 CET.** `/genesis/genesis-supervisor` is pid 2158, started by `/etc/init.d/genesis` (`S18genesis`). `dnsproxy` is pid 2202. `nslookup example.com 127.0.0.1` returned an address. `doh-bootstrap-watch` is absent. `hostapd` pids 16174 and 14927 were still present. `/etc/init.d/doh-proxy` is disabled, and the parked `S18doh-proxy` file was removed so the next boot does not put that start link back. `genesis-persist` now enables `genesis` instead of `doh-proxy`, and that copy was written into the parking lot.

`/etc/nginx/main_genesis_ui.conf` is an exact location for `/genesis/` and `/genesis`. This nginx has no `return` directive, and a prefix location lost to the catch-all. An unknown path is rejected with 404 by the session rules before the page runs, so `uci` rules `web.genesis` and `web.genesisnoslash` were added for admin, telia, and superuser. A request without that role receives the login page. The login page includes the Plugins link. A signed-in load of the three buttons was not done.

## Actions, 22:14 CET

**VERIFIED.** The same commands the page runs:

- Lookup of `example.com` through `127.0.0.1` succeeded. Usage printed `MemAvailable` 121780 kB, `dnsproxy` 2202, and both `hostapd` pids.
- Skin off removed `/etc/nginx/main_genesis.conf`. After the reload, `login.lp` had no `genesis.css` link. Skin on put the file back and the link returned (`genesis.css?v=2`). The manifest was left `enabled=1`.
- DNS off set the manifest to `enabled=0`, `dnsproxy` was absent, and it was still absent 22 seconds later, so the supervisor did not start it again. DNS on started pid 8717 and the lookup succeeded. `hostapd` pids were unchanged. The supervisor stayed pid 2158.

Dashboard cards are `/www/cards/000_genesis.lp`. They sort first. Each card links its gear to `/genesis/`. DNS shows DoH on or off, bootstrap `9.9.9.9`, Quad9 fallback, and `127.0.0.1:5053`. Telemetry shows whether TR-069 and MQTT are stopped. The skin card shows whether the stylesheet is on.

At 22:14 the Tailscale card looked for `/usr/sbin/tailscaled` and reported the binary missing. That was wrong. The running binary is `/genesis/tailscale/tailscaled` 1.104.5, started with `--tun=userspace-networking` because `CONFIG_TUN` is unset and `/dev/net/tun` does not exist.

**Superseded 22:50 CET.** The card and the settings section read `lua /genesis/tailscale_state.lua`, which uses `tailscale status`. The node row is the backend state and the 100.x address. A peer whose status column is `-` and whose JSON `Online` is true is shown as `online, no path`. The status name is the DNS label. `HostName` can differ (`tower-1` in the table, `Tower` in JSON), so the lookup uses `DNSName` when the host name does not match. Offline and idle lines are passed through. The health row is the daemon's health list, including `--accept-routes` being false. Start and stop still call `/etc/init.d/tailscale`.

The clicks were these commands, not a signed-in browser session. The address-change restart was not provoked. An overlay wipe removes `/genesis`.

## API

**VERIFIED, 22:19 CET.** `GET /genesis/api` and `GET /genesis/api/` are exact nginx locations using the same session check as the page. UCI rules `web.genesisapi` and `web.genesisapislash` allow admin, telia, and superuser. A request with no admin role got the login page (`Sign in`, 6446 bytes), not a JSON body. `dnsproxy` stayed pid 8717.

A signed-in `GET` returns `ok`, `notice`, `output`, `csrf`, and `plugins` (`id`, `name`, `kind`, `state`). A signed-in `POST` takes form fields `csrftoken`, `action` (`toggle`, `lookup`, `usage`), and `id`. That response was not captured. The handler is the same file as the Plugins page.

## Undo

`/etc/init.d/genesis stop` and `disable`. Enable and start `/etc/init.d/doh-proxy`. Remove `/etc/nginx/main_genesis_ui.conf`, reload nginx, and delete the two `web.genesis*` rules from the ruleset.
