#!/bin/sh
# Let a signed-in admin open /genesis/ and /genesis.
# The session rules reject an unknown path with 404 before the page runs.
if ! uci -q get web.genesis.target >/dev/null; then
	uci set web.genesis=rule
	uci set web.genesis.target='/genesis/'
	uci add_list web.genesis.roles='admin'
	uci add_list web.genesis.roles='telia'
	uci add_list web.genesis.roles='superuser'
fi
if ! uci -q get web.genesisnoslash.target >/dev/null; then
	uci set web.genesisnoslash=rule
	uci set web.genesisnoslash.target='/genesis'
	uci add_list web.genesisnoslash.roles='admin'
	uci add_list web.genesisnoslash.roles='telia'
	uci add_list web.genesisnoslash.roles='superuser'
fi
listed=$(uci show web.ruleset_main.rules 2>/dev/null || true)
if ! uci -q get web.genesisapi.target >/dev/null; then
	uci set web.genesisapi=rule
	uci set web.genesisapi.target='/genesis/api'
	uci add_list web.genesisapi.roles='admin'
	uci add_list web.genesisapi.roles='telia'
	uci add_list web.genesisapi.roles='superuser'
fi
if ! uci -q get web.genesisapislash.target >/dev/null; then
	uci set web.genesisapislash=rule
	uci set web.genesisapislash.target='/genesis/api/'
	uci add_list web.genesisapislash.roles='admin'
	uci add_list web.genesisapislash.roles='telia'
	uci add_list web.genesisapislash.roles='superuser'
fi
echo "$listed" | grep -q "'genesis'" || uci add_list web.ruleset_main.rules='genesis'
echo "$listed" | grep -q "'genesisnoslash'" || uci add_list web.ruleset_main.rules='genesisnoslash'
echo "$listed" | grep -q "'genesisapi'" || uci add_list web.ruleset_main.rules='genesisapi'
echo "$listed" | grep -q "'genesisapislash'" || uci add_list web.ruleset_main.rules='genesisapislash'
uci commit web
