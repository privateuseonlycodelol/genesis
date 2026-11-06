#!/bin/sh
# Let a signed-in admin open /genesis/ and /genesis.
# The session rules reject an unknown path with 404 before the page runs.
uci set web.genesis=rule
uci set web.genesis.target='/genesis/'
uci del web.genesis.roles >/dev/null 2>&1 || true
uci add_list web.genesis.roles='admin'
uci add_list web.genesis.roles='telia'
uci add_list web.genesis.roles='superuser'
uci set web.genesisnoslash=rule
uci set web.genesisnoslash.target='/genesis'
uci del web.genesisnoslash.roles >/dev/null 2>&1 || true
uci add_list web.genesisnoslash.roles='admin'
uci add_list web.genesisnoslash.roles='telia'
uci add_list web.genesisnoslash.roles='superuser'
uci add_list web.ruleset_main.rules='genesis'
uci add_list web.ruleset_main.rules='genesisnoslash'
uci commit web
