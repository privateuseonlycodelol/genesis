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

local notice = ""
local output = ""

ngx.req.read_body()
if ngx.req.get_method() == "POST" then
  local args = ngx.req.get_post_args() or {}
  local token = clean(args.csrftoken)
  check_csrf(token)
  local action = clean(args.action)
  local id = clean(args.id)
  if action == "toggle" and (id == "dns" or id == "redesign") then
    os.execute("/genesis/genesis-supervisor ctl toggle " .. id .. " >/dev/null 2>&1")
    notice = id .. " updated"
  elseif action == "lookup" and id == "diagnostics" then
    output = capture("nslookup example.com 127.0.0.1")
    notice = "Lookup"
  elseif action == "usage" and id == "diagnostics" then
    output = capture("echo uptime $(cut -d. -f1 /proc/uptime)s; awk '/MemTotal|MemFree|MemAvailable|Slab/{print}' /proc/meminfo; echo dnsproxy $(pidof dnsproxy || echo down); echo hostapd $(pidof hostapd || echo down)")
    notice = "Usage"
  end
end

local token = csrf()
ngx.header.content_type = "text/html; charset=utf-8"
ngx.say([[<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plugins</title>
<link rel="stylesheet" href="/css/genesis.css?v=2">
<style>
  body { margin: 0; }
  main { max-width: 880px; margin: 48px auto; padding: 0 20px 48px; }
  h1 { font-size: 28px; font-weight: 560; letter-spacing: -0.03em; margin: 0 0 8px; }
  p.lead { color: #a8a29e; margin: 0 0 28px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 14px 0; border-bottom: 1px solid #2c313a; vertical-align: middle; }
  th { color: #a8a29e; font-weight: 500; font-size: 13px; }
  .state { font-variant-numeric: tabular-nums; }
  button, .btn { font: inherit; }
  pre { white-space: pre-wrap; background: #0c0d10; border-radius: 12px; padding: 16px; color: #e7e5e4; }
</style>
</head>
<body>
<main>
<h1>Plugins</h1>
<p class="lead">Services, checks, and the skin. The signed pages are unchanged.</p>
]])

if notice ~= "" then
  ngx.say("<p>" .. esc(notice) .. "</p>")
end

ngx.say("<table><thead><tr><th>Name</th><th>Kind</th><th>State</th><th></th></tr></thead><tbody>")

for _, id in ipairs(plugin_ids()) do
  local m = read_manifest(id)
  local state = "present"
  local buttons = ""
  if m.kind == "service" then
    state = dns_up() and "running" or "stopped"
    buttons = string.format(
      [[<form method="post" action="/genesis/"><input type="hidden" name="csrftoken" value="%s"><input type="hidden" name="action" value="toggle"><input type="hidden" name="id" value="%s"><button class="btn" type="submit">%s</button></form>]],
      esc(token), esc(id), state == "running" and "Stop" or "Start"
    )
  elseif m.kind == "files" then
    state = skin_on() and "on" or "off"
    buttons = string.format(
      [[<form method="post" action="/genesis/"><input type="hidden" name="csrftoken" value="%s"><input type="hidden" name="action" value="toggle"><input type="hidden" name="id" value="%s"><button class="btn" type="submit">%s</button></form>]],
      esc(token), esc(id), state == "on" and "Turn off" or "Turn on"
    )
  elseif m.kind == "tool" then
    state = "on demand"
    buttons = string.format(
      [[<form method="post" action="/genesis/" style="display:inline"><input type="hidden" name="csrftoken" value="%s"><input type="hidden" name="action" value="lookup"><input type="hidden" name="id" value="%s"><button class="btn" type="submit">Lookup</button></form> <form method="post" action="/genesis/" style="display:inline"><input type="hidden" name="csrftoken" value="%s"><input type="hidden" name="action" value="usage"><input type="hidden" name="id" value="%s"><button class="btn" type="submit">Usage</button></form>]],
      esc(token), esc(id), esc(token), esc(id)
    )
  end
  ngx.say(string.format(
    "<tr><td>%s</td><td>%s</td><td class=\"state\">%s</td><td>%s</td></tr>",
    esc(m.name or id), esc(m.kind or ""), esc(state), buttons
  ))
end

ngx.say("</tbody></table>")
if output ~= "" then
  ngx.say("<pre>" .. esc(output) .. "</pre>")
end
ngx.say("</main></body></html>")
