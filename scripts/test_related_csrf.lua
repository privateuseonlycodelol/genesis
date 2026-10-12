-- Offline behavior test of an extracted function from pinned public source.
-- This does not execute a router request or establish the F1 implementation.
local path = arg[1] or "artifacts/source-review/session.lua"
local file = assert(io.open(path, "r"))
local source = file:read("*a")
file:close()
local body = assert(source:match("function Session:checkCSRFtoken%(token%)(.-)\nend"),
  "could not find expected checkCSRFtoken source function")
local environment = {
  Session = {},
  ngx = {
    ERR = 3, HTTP_FORBIDDEN = 403,
    log = function() end,
    exit = function(status) error({http_status = status}, 0) end,
  },
}
local chunk = assert(load("function Session:checkCSRFtoken(token)" .. body .. "\nend",
  "extracted-public-source", "t", environment))
chunk()
local session = setmetatable({CSRFtoken = "synthetic-token"}, {__index = environment.Session})
assert(session:checkCSRFtoken("synthetic-token") == true)
for _, candidate in ipairs({"wrong-token", false, {"synthetic-token"}}) do
  local ok, result = pcall(session.checkCSRFtoken, session, candidate)
  assert(not ok and type(result) == "table" and result.http_status == 403)
end
local ok, result = pcall(session.checkCSRFtoken, session, nil)
assert(not ok and type(result) == "table" and result.http_status == 403)
print("PASS: extracted related-source CSRF function accepts matching dummy token; wrong/missing/non-string tokens exit 403")
print("LIMIT: direct-function test uses a mocked ngx.exit; it does not establish wire status or live F1 behavior")

-- Independently exercise the exact ngx.exit wrapper from pinned web.lua.
-- This distinguishes the wrapper's ngx.status assignment from the captured
-- native ngx.exit argument; neither mock determines what nginx sends on wire.
local web_path = arg[2] or "artifacts/source-review/web.lua"
local web_file = assert(io.open(web_path, "r"))
local web_source = web_file:read("*a")
web_file:close()
local wrapper_start = assert(web_source:find("  local ngx_exit = ngx.exit", 1, true),
  "could not find expected ngx.exit wrapper")
local wrapper_end = assert(web_source:find("\n  \nend", wrapper_start, true),
  "could not find end of expected ngx.exit wrapper")
local wrapper_source = web_source:sub(wrapper_start, wrapper_end - 1)
local native_exit_status, requested_template, requested_root
local wrapper_environment = {
  ngx = {
    HTTP_OK = 200,
    HTTP_FORBIDDEN = 403,
    header = {},
    exit = function(status)
      native_exit_status = status
      return status
    end,
  },
  lp = {
    setpath = function(path) requested_root = path end,
    include = function(path) requested_template = path end,
  },
}
assert(load(wrapper_source, "extracted-public-ngx-exit-wrapper", "t", wrapper_environment))()
local wrapper_return = wrapper_environment.ngx.exit(wrapper_environment.ngx.HTTP_FORBIDDEN)
assert(wrapper_environment.ngx.status == 403, "wrapper should set ngx.status to 403")
assert(wrapper_environment.ngx.header.content_type == "text/html")
assert(wrapper_environment.ngx.header.error_msg == nil)
assert(requested_root == "/www/docroot/")
assert(requested_template == "error.lp", "wrapper should request error.lp")
assert(native_exit_status == 200, "wrapper should call captured native ngx.exit(200)")
assert(wrapper_return == 200, "mocked wrapper should return the captured native exit result")
print("PASS: extracted related-source wrapper sets ngx.status=403, requests error.lp, then calls captured native ngx.exit(200)")
print("LIMIT: mocked ngx/lp; final wire status is unknown, and no live F1 behavior is established")
