#!/usr/bin/lua
-- Retired Cloudflare forwarder. The overlay process is /usr/sbin/dnsproxy.
-- The upstream URL is not stored here.
io.stderr:write("doh-proxy.lua: retired; dnsproxy is the forwarder\n")
os.exit(1)
