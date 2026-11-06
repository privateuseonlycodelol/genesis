--pretranslated
-- One card per settings section. The control itself is on /genesis/.

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

local function card(title, href, body)
  ngx.print('<div class="span3"><div class="smallcard"><div class="header"><div class="header-title pull-left"><p>')
  ngx.print(title)
  ngx.print('</p></div><a class="settings" href="' .. href .. '"><i class="icon-cogs"></i></a></div><div class="content">')
  ngx.print(body)
  ngx.print('<p class="subinfos"><a href="' .. href .. '">Settings</a></p></div></div></div>')
end

local dns_up = on("pidof dnsproxy")
local blocked = not on("pidof cwmpd") and not on("pidof pub_rgw_messages")
local skin_on = sh("test -f /etc/nginx/main_genesis.conf && echo yes") == "yes"
local ts_backend = "down"
local ts_paths, ts_nopath, ts_off = 0, 0, 0
for line in sh("lua /genesis/tailscale_state.lua"):gmatch("[^\n]+") do
  local kind, rest = line:match("^(%S+)%s+(.*)$")
  if kind == "backend" then
    ts_backend = rest
  elseif kind == "peer" then
    if rest:find("no path", 1, true) then
      ts_nopath = ts_nopath + 1
    elseif rest:find("offline", 1, true) or rest:find("last seen", 1, true) then
      ts_off = ts_off + 1
    else
      ts_paths = ts_paths + 1
    end
  end
end

card("DNS", "/genesis/#dns",
  light(dns_up, dns_up and "DoH on" or "DoH off"))

card("Telemetry", "/genesis/#telemetry",
  light(blocked, blocked and "Blocked" or "Running"))

card("Tailscale", "/genesis/#tailscale",
  light(ts_backend == "Running", ts_backend)
  .. '<p class="subinfos">' .. ts_paths .. " with a path, " .. ts_nopath .. " online with no path, " .. ts_off .. " offline</p>")

card("Appearance", "/genesis/#appearance",
  light(skin_on, skin_on and "Skin on" or "Skin off"))
