#!/bin/sh
# Refresh dns.rilah.app through 9.9.9.9.
# Restart dnsproxy when the address set changes, or when local DNS has
# failed for about a minute. This file does not contain the upstream URL.

set -u

fail_loops=0
cooldown=0
loops=0
last_ips=""

resolve_ips() {
	nslookup dns.rilah.app 9.9.9.9 2>&1 | lua -e '
		local text = io.read("*a")
		local at = text:find("Name:")
		local body = at and text:sub(at) or ""
		local ips = {}
		for ip in body:gmatch("Address[^:\n]*:%s*(%S+)") do
			ips[#ips + 1] = ip
		end
		table.sort(ips)
		io.write(table.concat(ips, " "))
	'
}

health_ok() {
	nslookup example.com 127.0.0.1 >/tmp/doh-watch-health 2>&1
	lua -e '
		local handle = io.open("/tmp/doh-watch-health")
		local text = handle:read("*a")
		handle:close()
		local at = text:find("Name:")
		local body = at and text:sub(at) or ""
		os.exit(body:find("Address") and 0 or 1)
	'
}

restart_proxy() {
	pid=$(pidof dnsproxy) || pid=""
	if [ -n "$pid" ]; then
		# shellcheck disable=SC2086
		kill $pid
	fi
}

while true; do
	sleep 20
	loops=$((loops + 1))
	if [ "$cooldown" -gt 0 ]; then
		cooldown=$((cooldown - 1))
	fi

	# First pass, then about every 300 seconds.
	if [ "$loops" -eq 1 ] || [ $((loops % 15)) -eq 0 ]; then
		ips=$(resolve_ips) || ips=""
		if [ -n "$ips" ]; then
			if [ -n "$last_ips" ] && [ "$ips" != "$last_ips" ] && [ "$cooldown" -eq 0 ]; then
				logger -t doh-watch "public address changed; restarting proxy" || true
				restart_proxy
				cooldown=5
				fail_loops=0
			fi
			last_ips=$ips
		fi
	fi

	# Skip the first minute so a cold start is not treated as a failure.
	if [ "$loops" -ge 4 ]; then
		if health_ok; then
			fail_loops=0
		else
			fail_loops=$((fail_loops + 1))
			if [ "$fail_loops" -ge 3 ] && [ "$cooldown" -eq 0 ]; then
				logger -t doh-watch "proxy failed for over a minute; restarting" || true
				restart_proxy
				cooldown=15
				fail_loops=0
			fi
		fi
	fi
done
