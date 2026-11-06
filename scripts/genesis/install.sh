#!/bin/sh
# Install this project onto the router. Run it from the repo on the Mac.
# SSH_ASKPASS must already be set, as for the other lab scripts.
set -eu

cd "$(dirname "$0")/../.."
HOST="${F1_HOST:-root@192.168.1.1}"
if [ -z "${F1PW:-}" ] && [ -f artifacts/secrets/f1-root.password ]; then
	F1PW=$(tr -d '\r' < artifacts/secrets/f1-root.password)
	export F1PW
fi
export SSH_ASKPASS="${SSH_ASKPASS:-/tmp/f1ask/askpass.sh}"
export SSH_ASKPASS_REQUIRE="${SSH_ASKPASS_REQUIRE:-force}"
export DISPLAY="${DISPLAY:-none}"
SSH="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o IdentitiesOnly=yes -o NumberOfPasswordPrompts=1 -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR"

put() {
	dest=$1
	src=$2
	payload=$(base64 < "$src" | tr -d '\n')
	$SSH "$HOST" "echo $payload | base64 -d > $dest" < /dev/null
}

$SSH "$HOST" "mkdir -p /genesis/plugins/dns /genesis/plugins/diagnostics /genesis/plugins/redesign /genesis/plugins/telemetry /var/run/genesis" < /dev/null

put /genesis/genesis-supervisor scripts/genesis/genesis-supervisor
put /etc/init.d/genesis scripts/genesis/genesis.init
put /genesis/ui.lua scripts/genesis/ui.lua
put /genesis/tailscale_state.lua scripts/genesis/tailscale_state.lua
put /etc/nginx/main_genesis_ui.conf scripts/genesis/nginx-ui.conf
put /genesis/plugins/dns/manifest scripts/genesis/plugins/dns/manifest
put /genesis/plugins/diagnostics/manifest scripts/genesis/plugins/diagnostics/manifest
put /genesis/plugins/redesign/manifest scripts/genesis/plugins/redesign/manifest
put /genesis/plugins/redesign/skin.conf scripts/genesis/plugins/redesign/skin.conf
put /genesis/plugins/telemetry/manifest scripts/genesis/plugins/telemetry/manifest
put /genesis/plugins/telemetry/apply scripts/genesis/plugins/telemetry/apply
put /www/cards/000_genesis.lp scripts/genesis/000_genesis.lp
put /etc/init.d/genesis-persist scripts/genesis/genesis-persist.init
put /www/docroot/css/genesis.css scripts/f1_ui_genesis.css
put /etc/nginx/main_genesis.conf scripts/f1_nginx_main_genesis.conf
put /genesis/allow-web.sh scripts/genesis/allow-web.sh
put /usr/lib/lua/web/check_host.lua scripts/genesis/check_host.lua

$SSH "$HOST" "set -e
chmod 755 /genesis/genesis-supervisor /etc/init.d/genesis
chmod 644 /genesis/ui.lua /etc/nginx/main_genesis_ui.conf /etc/nginx/main_genesis.conf /www/docroot/css/genesis.css /usr/lib/lua/web/check_host.lua
chmod 755 /genesis/tailscale_state.lua
chmod 755 /genesis/plugins/telemetry/apply /etc/init.d/genesis-persist
chmod 644 /genesis/plugins/dns/manifest /genesis/plugins/diagnostics/manifest /genesis/plugins/redesign/manifest /genesis/plugins/redesign/skin.conf /genesis/plugins/telemetry/manifest
sh /genesis/allow-web.sh 2>/dev/null || true
nginx -t
/etc/init.d/nginx reload
/etc/init.d/genesis enable
/etc/init.d/genesis start
echo INSTALLED" < /dev/null
