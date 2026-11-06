# Plugin supervisor — 2026-11-06

One foreground loop owns the overlay plugins. The page is `/genesis/` on the existing nginx, after a normal admin login. The signed templates were not replaced.

## Layout

| Plugin | Kind | What it is |
| --- | --- | --- |
| DNS | service | `dnsproxy` with the existing `/etc/dnsproxy.yaml`. The supervisor restarts it if `example.com` through `127.0.0.1` fails for about a minute, and if the public address of `dns.rilah.app` from `9.9.9.9` changes. Same intervals as the retired watcher. The URL file is not in the plugin directory. |
| Diagnostics | tool | Lookup and usage run when the button is pressed. Nothing stays running. |
| Redesign | files | `genesis.css` and the nginx skin filter. |

Repo copies: `scripts/genesis/`. The web rule that lets those paths through the session check is `scripts/genesis/allow-web.sh`.

## Live

**VERIFIED, 22:10 CET.** `/genesis/genesis-supervisor` is pid 2158, started by `/etc/init.d/genesis` (`S18genesis`). `dnsproxy` is pid 2202. `nslookup example.com 127.0.0.1` returned an address. `doh-bootstrap-watch` is absent. `hostapd` pids 16174 and 14927 were still present. `/etc/init.d/doh-proxy` is disabled, and the parked `S18doh-proxy` file was removed so the next boot does not put that start link back. `genesis-persist` now enables `genesis` instead of `doh-proxy`, and that copy was written into the parking lot.

`/etc/nginx/main_genesis_ui.conf` is an exact location for `/genesis/` and `/genesis`. This nginx has no `return` directive, and a prefix location lost to the catch-all. An unknown path is rejected with 404 by the session rules before the page runs, so `uci` rules `web.genesis` and `web.genesisnoslash` were added for admin, telia, and superuser. A request without that role receives the login page. The login page includes the Plugins link. A signed-in load of the three buttons was not done.

## Not shown

Stopping DNS from the page, turning the skin off, and the diagnostics buttons were not clicked. An overlay wipe removes `/genesis`. The address-change restart was not provoked.

## Undo

`/etc/init.d/genesis stop` and `disable`. Enable and start `/etc/init.d/doh-proxy`. Remove `/etc/nginx/main_genesis_ui.conf`, reload nginx, and delete the two `web.genesis*` rules from the ruleset.
