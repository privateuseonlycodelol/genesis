-- Plugin page. Session check is done by nginx before this file runs.
local root = "/genesis/plugins"

local function esc(s)
  s = tostring(s or "")
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function clean(s)
  if type(s) ~= "string" then
    return ""
  end
  if string.untaint then
    return string.untaint(s)
  end
  return s
end

local function read_manifest(id)
  local t = { id = id }
  local f = io.open(root .. "/" .. id .. "/manifest")
  if not f then
    return t
  end
  for line in f:lines() do
    local k, v = line:match("^([%w_]+)=(.*)$")
    if k then
      t[k] = v
    end
  end
  f:close()
  return t
end

local function plugin_ids()
  local ids = {}
  local p = io.popen("ls -1 " .. root .. " 2>/dev/null")
  if not p then
    return ids
  end
  for name in p:lines() do
    if name:match("^[%w_-]+$") then
      ids[#ids + 1] = name
    end
  end
  p:close()
  table.sort(ids)
  return ids
end

local function capture(cmd)
  local p = io.popen(cmd .. " 2>&1")
  local text = p and p:read("*a") or ""
  if p then
    p:close()
  end
  if #text > 4000 then
    text = text:sub(1, 4000) .. "\n…"
  end
  return text
end

local function dns_up()
  return capture("pidof dnsproxy"):match("%d") ~= nil
end

local function skin_on()
  local f = io.open("/etc/nginx/main_genesis.conf")
  if not f then
    return false
  end
  f:close()
  return true
end

local function csrf()
  local session = ngx.ctx.session
  if session and session.getCSRFtoken then
    return session:getCSRFtoken() or ""
  end
  return ""
end

local function check_csrf(token)
  local session = ngx.ctx.session
  if session and session.checkCSRFtoken then
    session:checkCSRFtoken(token or "")
  end
end

local function plugin_rows()
  local rows = {}
  for _, id in ipairs(plugin_ids()) do
    local m = read_manifest(id)
    local state = "present"
    if m.kind == "service" then
      state = dns_up() and "running" or "stopped"
    elseif m.kind == "files" then
      state = skin_on() and "on" or "off"
    elseif m.kind == "tool" then
      state = "on demand"
    elseif m.kind == "enforce" then
      state = (m.enabled == "1") and "blocking" or "allowed"
    end
    rows[#rows + 1] = {
      id = id,
      name = m.name or id,
      kind = m.kind or "",
      state = state,
    }
  end
  return rows
end

local function json_escape(s)
  s = tostring(s or "")
  s = s:gsub("\\", "\\\\")
  s = s:gsub('"', '\\"')
  s = s:gsub("\r", "\\r")
  s = s:gsub("\n", "\\n")
  return s
end

local function json_plugins(rows)
  local parts = {}
  for i, row in ipairs(rows) do
    parts[i] = string.format(
      '{"id":"%s","name":"%s","kind":"%s","state":"%s"}',
      json_escape(row.id), json_escape(row.name), json_escape(row.kind), json_escape(row.state)
    )
  end
  return "[" .. table.concat(parts, ",") .. "]"
end

local notice = ""
local output = ""

if ngx.req.get_method() == "POST" then
  local args = ngx.req.get_post_args() or {}
  local action = clean(args.action)
  local id = clean(args.id)
  local nxt = clean(args["next"])
  if action == "toggle" and (id == "dns" or id == "redesign" or id == "telemetry") then
    os.execute("/genesis/genesis-supervisor ctl toggle " .. id .. " >/dev/null 2>&1")
    notice = id .. " updated"
  elseif action == "tailscale" and (id == "start" or id == "stop") then
    os.execute("/etc/init.d/tailscale " .. id .. " >/dev/null 2>&1")
    notice = "tailscale " .. id
  elseif action == "lookup" and id == "diagnostics" then
    output = capture("nslookup example.com 127.0.0.1")
    notice = "Lookup"
  elseif action == "usage" and id == "diagnostics" then
    output = capture("echo uptime $(cut -d. -f1 /proc/uptime)s; awk '/MemTotal|MemFree|MemAvailable|Slab/{print}' /proc/meminfo; echo dnsproxy $(pidof dnsproxy || echo down); echo hostapd $(pidof hostapd || echo down)")
    notice = "Usage"
  end
  if nxt == "/gateway.lp" then
    return ngx.redirect("/gateway.lp")
  end
end

local token = csrf()
local uri = ngx.var.uri or ""
if uri == "/genesis/api" or uri == "/genesis/api/" then
  local rows = plugin_rows()
  ngx.header.content_type = "application/json; charset=utf-8"
  ngx.say(string.format(
    '{"ok":%s,"notice":"%s","output":"%s","csrf":"%s","plugins":%s}',
    (notice ~= "" or ngx.req.get_method() == "GET") and "true" or "false",
    json_escape(notice),
    json_escape(output),
    json_escape(token),
    json_plugins(rows)
  ))
  return
end

local function sh(cmd)
  return (capture(cmd):gsub("%s+$", ""))
end

local function setting(title, detail, control)
  ngx.say('<div class="set"><div><strong>' .. esc(title) .. '</strong><p>' .. detail .. '</p></div><div class="ctl">' .. control .. '</div></div>')
end

local function sw(label, action, id)
  return string.format(
    '<form method="post" action="/genesis/"><input type="hidden" name="CSRFtoken" value="%s"><input type="hidden" name="action" value="%s"><input type="hidden" name="id" value="%s"><button class="btn" type="submit">%s</button></form>',
    esc(token), action, id, esc(label)
  )
end

local dns_up = sh("pidof dnsproxy") ~= ""
local lookup = sh("nslookup example.com 127.0.0.1")
local at = lookup:find("Name:")
local addr = ((at and lookup:sub(at) or ""):match("Address[^:\n]*:%s*(%S+)")) or "not answering"
local ts_proc = sh("ps w | grep '/genesis/tailscale/tailscaled' | grep -v grep") ~= ""
local ts = { backend = "down", address = "none", health = {}, self = "", peers = {} }
for line in sh("lua /genesis/tailscale_state.lua"):gmatch("[^\n]+") do
  local kind, rest = line:match("^(%S+)%s+(.*)$")
  if kind == "backend" then
    ts.backend = rest
  elseif kind == "address" then
    ts.address = rest
  elseif kind == "health" and rest ~= "none" then
    ts.health[#ts.health + 1] = rest
  elseif kind == "self" then
    ts.self = rest
  elseif kind == "peer" then
    local name, osname, state = rest:match("^(%S+)%s+(%S+)%s+(.*)$")
    if name then
      ts.peers[#ts.peers + 1] = { name = name, os = osname, state = state }
    end
  end
end
local blocked = sh("pidof cwmpd") == "" and sh("pidof pub_rgw_messages") == ""
local skin = sh("test -f /etc/nginx/main_genesis.conf && echo yes") == "yes"

ngx.header.content_type = "text/html; charset=utf-8"
ngx.say([[<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Settings</title>
<link rel="stylesheet" href="/css/genesis.css?v=8">
<style>
  body { margin: 0; background: #090a0c; color: #e7e5e4; font-family: "Avenir Next", "Segoe UI", Helvetica, Arial, sans-serif; }
  main { max-width: 720px; margin: 28px auto 64px; padding: 0 20px; }
  a { color: #d6d3d1; }
  h1 { font-size: 28px; font-weight: 600; letter-spacing: -0.03em; margin: 12px 0 24px; }
  h2 { font-size: 13px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: #a8a29e; margin: 28px 0 8px; }
  .set { display: flex; justify-content: space-between; gap: 16px; align-items: center; background: #14161b; border: 1px solid #262a31; border-bottom: 0; padding: 14px 16px; }
  section .set:first-of-type { border-radius: 12px 12px 0 0; }
  section .set:last-of-type { border-bottom: 1px solid #262a31; border-radius: 0 0 12px 12px; }
  .set strong { display: block; font-size: 15px; font-weight: 600; }
  .set p { margin: 4px 0 0; color: #a8a29e; font-size: 13px; line-height: 1.4; }
  .ctl { flex: 0 0 auto; }
  button, .btn { font: inherit; }
  pre { white-space: pre-wrap; background: #14161b; border: 1px solid #262a31; border-radius: 12px; padding: 16px; color: #e7e5e4; }
  .note { color: #a8a29e; }
</style>
</head>
<body>
<main>
<p><a href="/gateway.lp">Dashboard</a></p>
<h1>Settings</h1>
]])

if notice ~= "" then
  ngx.say("<p class=\"note\">" .. esc(notice) .. "</p>")
end

ngx.say('<section id="dns"><h2>DNS</h2>')
setting("Encrypted DNS", "example.com is " .. esc(addr) .. ". Bootstrap 9.9.9.9. Fallback Quad9. Listener 127.0.0.1 port 5053.",
  sw(dns_up and "Turn off" or "Turn on", "toggle", "dns"))
ngx.say("</section>")

ngx.say('<section id="tailscale"><h2>Tailscale</h2>')
setting("This node", esc(ts.self ~= "" and ts.self or ts.backend) .. ". Address " .. esc(ts.address) .. ". Userspace mode, no tunnel device.",
  sw(ts_proc and "Stop" or "Start", "tailscale", ts_proc and "stop" or "start"))
for _, peer in ipairs(ts.peers) do
  setting(peer.name, esc(peer.os), '<span class="note">' .. esc(peer.state) .. "</span>")
end
if #ts.health == 0 then
  setting("Health", "No warnings.", "")
else
  for _, msg in ipairs(ts.health) do
    setting("Health", esc(msg), "")
  end
end
ngx.say("</section>")

ngx.say('<section id="telemetry"><h2>Telemetry</h2>')
setting("Telia telemetry", "Usage meter, TR-069, and MQTT.",
  sw(blocked and "Allow" or "Block", "toggle", "telemetry"))
ngx.say("</section>")

ngx.say('<section id="appearance"><h2>Appearance</h2>')
setting("Dashboard skin", "Dark cards on the main page.",
  sw(skin and "Turn off" or "Turn on", "toggle", "redesign"))
ngx.say("</section>")

ngx.say('<section id="diagnostics"><h2>Diagnostics</h2>')
setting("Checks", "Run one check and show the result here.",
  sw("Lookup", "lookup", "diagnostics") .. sw("Usage", "usage", "diagnostics"))
ngx.say("</section>")

if output ~= "" then
  ngx.say("<pre>" .. esc(output) .. "</pre>")
end
ngx.say("</main></body></html>")
