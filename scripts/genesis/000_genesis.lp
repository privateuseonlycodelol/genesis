--pretranslated
-- Dashboard cards for the overlay plugins. Read-only. Actions stay on /genesis/.

local function sh(cmd)
  local p = io.popen(cmd .. " 2>/dev/null")
  local text = p and p:read("*a") or ""
  if p then p:close() end
  return (text:gsub("%s+$", ""))
end

local function on(cmd)
  return sh(cmd) ~= ""
end

local function light(up, label)
  local cls = up and "light green" or "light red"
  return '<div class="simple-desc"><div class="' .. cls .. '"></div>' .. label .. '</div>'
end

local function card(title, body)
  ngx.print([[
<div class="span3">
  <div class="smallcard">
    <div class="header">
      <div class="header-title pull-left"><p>]])
  ngx.print(title)
  ngx.print([[</p></div>
      <a class="settings" href="/genesis/"><i class="icon-cogs"></i></a>
    </div>
    <div class="content">]])
  ngx.print(body)
  ngx.print([[
    </div>
  </div>
</div>
]])
end

local dns_up = on("pidof dnsproxy")
local telemetry_off = not on("pidof cwmpd") and not on("pidof pub_rgw_messages")
local skin_on = sh("test -f /etc/nginx/main_genesis.conf && echo yes") == "yes"
local ts_bin = sh("test -x /usr/sbin/tailscaled && echo yes") == "yes"
local ts_up = on("pidof tailscaled")
local tun = sh("test -c /dev/net/tun && echo yes") == "yes"

card("DNS",
  light(dns_up, dns_up and "DoH on" or "DoH off")
  .. '<p class="subinfos">Bootstrap 9.9.9.9<br>Fallback Quad9<br>Listen 127.0.0.1:5053<br>Cache on</p>')

card("Telemetry",
  light(telemetry_off, telemetry_off and "Blocked" or "Running")
  .. '<p class="subinfos">Usage meter, TR-069, and MQTT</p>')

card("Tailscale",
  light(ts_up, ts_up and "Running" or "Not running")
  .. '<p class="subinfos">'
  .. (ts_bin and "Binary installed" or "Binary not installed")
  .. "<br>"
  .. (tun and "Tunnel device present" or "No tunnel device")
  .. "<br>Mode would be userspace</p>")

card("Appearance",
  light(skin_on, skin_on and "Skin on" or "Skin off")
  .. '<p class="subinfos">Dashboard theme<br><a href="/genesis/">Plugin settings</a></p>')
