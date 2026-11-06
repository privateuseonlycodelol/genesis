#!/bin/sh
# Re-resolve dns.rilah.app through 9.9.9.9 and restart dnsproxy when that
# address set changes. Also restart if the local proxy stops answering for
# about a minute. This file has no upstream URL.

fail_loops=0
cooldown=0
loops=0
last_ips=""

resolve_ips() {
	nslookup dns.rilah.app 9.9.9.9 2>&1 | lua -e '
		local s = io.read("*a")
		local at = s:find("Name:")
		local body = at and s:sub(at) or ""
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
		local f = io.open("/tmp/doh-watch-health")
		local s = f:read("*a")
		f:close()
		local at = s:find("Name:")
		local body = at and s:sub(at) or ""
		if body:find("Address") then os.exit(0) end
		os.exit(1)
	'
}

restart_proxy() {
	pid=$(pidof dnsproxy)
	if [ -n "$pid" ]; then
		kill $pid
	fi
}

while true; do
	sleep 20
	loops=$((loops + 1))
	if [ "$cooldown" -gt 0 ]; then
		cooldown=$((cooldown - 1))
	fi

	if [ "$loops" -eq 1 ] || [ $((loops % 15)) -eq 0 ]; then
		ips=$(resolve_ips)
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
