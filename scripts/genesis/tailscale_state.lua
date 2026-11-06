#!/usr/bin/lua
-- Print this node's Tailscale state and each peer's state.
-- A "-" from `tailscale status` means the peer is online and this node has no path.

local cmd = "/genesis/tailscale/tailscale --socket=/var/run/tailscale/tailscaled.sock"

local function run(args)
  local p = io.popen(cmd .. " " .. args .. " 2>/dev/null")
  local text = p and p:read("*a") or ""
  if p then p:close() end
  return text or ""
end

local text = run("status")
local json = run("status --json")
local backend = json:match('"BackendState"%s*:%s*"([^"]+)"') or ""
if backend == "" then
  print(text == "" and "backend down" or "backend unknown")
else
  print("backend " .. backend)
end

local address = run("ip -4"):match("(%d+%.%d+%.%d+%.%d+)") or ""
print("address " .. (address ~= "" and address or "none"))

local health_body = json:match('"Health"%s*:%s*%[(.-)%]') or ""
local health_count = 0
for msg in health_body:gmatch('"([^"]*)"') do
  health_count = health_count + 1
  print("health " .. msg)
end
if health_count == 0 then
  print("health none")
end

local function online_for(name)
  local at = json:find('"HostName": "' .. name .. '"', 1, true)
  if not at then
    at = json:find('"DNSName": "' .. name .. '.', 1, true)
  end
  if not at then
    return ""
  end
  local slice = json:sub(at, at + 8000)
  local value = slice:match('"Online"%s*:%s*(%a+)')
  if value == "true" or value == "false" then
    return value
  end
  return ""
end

local first = true
for line in text:gmatch("[^\n]+") do
  local host, osname, rest = line:match("^%d+%.%d+%.%d+%.%d+%s+(%S+)%s+%S+%s+(%S+)%s+(.*)$")
  if host then
    rest = rest:gsub("%s+$", "")
    if first then
      print("self " .. host .. " " .. osname .. " " .. (backend ~= "" and backend or rest))
      first = false
    else
      if rest == "-" then
        local online = online_for(host)
        if online == "true" then
          rest = "online, no path"
        elseif online == "false" then
          rest = "offline"
        else
          rest = "unknown"
        end
      end
      print("peer " .. host .. " " .. osname .. " " .. rest)
    end
  end
end
