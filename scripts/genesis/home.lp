--pretranslated
-- One interface. The chooser between simplified and advanced is not shown.
-- Sign-out still clears the session, then the browser lands on the full card page.
if ngx.req.get_method() == "POST" then
  ngx.req.read_body()
  local post_args = ngx.req.get_post_args() or {}
  if post_args.do_signout and ngx.ctx.session then
    ngx.ctx.session:logout()
  end
end
return ngx.redirect("/gateway.lp")
