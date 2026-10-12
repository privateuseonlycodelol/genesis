# F1 JavaScript audit (static, 23.1.b artifacts)

**Scope:** Offline review of saved UI files under `artifacts/ui/` plus `findings/f1-api-map.md`. No live HTTP, no router contact.

**Recovered from HAR (2026-10-12):** Response bodies extracted from `artifacts/ui/192.168.2.1.browser.har` into:

- `artifacts/ui/main-min.js` (262770 B, cache-busted URL in HAR)
- `artifacts/ui/login.js` (6608 B)

**Present and used:**

- `artifacts/ui/system-config-min.js` (17 lines, minified)
- `artifacts/ui/main-min.js`, `artifacts/ui/login.js` (see above)
- `artifacts/ui/srp-min.js` (SRP + password change posts)
- `artifacts/ui/login.lp.html`, `gateway.lp.authenticated.html`, `modals-system-config-modal.lp.html`, other `*.lp.html` modals
- `findings/f1-api-map.md`

---

## 1. `system-config-min.js` — globals

| Symbol | Source (file:line) | Role |
|--------|-------------------|------|
| `target` | L1 | `$(".modal form").attr("action")` → on saved config modal: `modals/system-config-modal.lp` (relative; resolves under gateway host). |
| `refreshTimeOut` | L1 | `5000` ms for `getbanksize` AJAX timeout. |
| `schedule_time` | L1, L4 | Built when scheduling reboot. |
| `valeur` | L1 | Progress bar width for `resetrtfd` (starts at `2`). |

**CSRF:** Every POST shown below includes `CSRFtoken: $("meta[name=CSRFtoken]").attr("content")` (meta present on `gateway.lp.authenticated.html` L9, redacted in repo).

**Helpers defined in this file**

| Function | Lines | Behavior |
|----------|-------|----------|
| `resetReboot(a,b,c)` | L1 | Shows message UI, then `$.post(target, { action: c, CSRFtoken }, wait_for_webserver_down(c), "json")`. |
| `resetrtfd(a,b,c)` | L1 | Progress UI + `$.post(target, { action: c, CSRFtoken }, wait_for_webserver_down, "json")` (no action arg to waiter). |
| `wait_for_upgradefw()` | L14–15 | Poll loop (see firmware status). |

**Not in this file:** `wait_for_webserver_down`, `wait_for_webserver_running`, `confirmationDialogue`, `tch.showProgress`, `$.fileUpload`, `$.fileDownload` — defined in `main-min.js` (§7).

---

## 2. `system-config-min.js` — dangerous actions (by feature)

### 2.1 Reboot (`system_reboot`)

| Field | Value |
|-------|--------|
| **Trigger** | `#btn-system-reboot` click (L3); after confirm, delegated `.Restart` / `touchend` (L3). |
| **Prerequisite** | If inline `resetrtfdValue == "true"` (`modals-system-config-modal.lp.html` L35), skips dialog and calls `resetrtfd` instead. Else `confirmationDialogue(T.confirmmsg, T.restartDev, "Restart")` then user clicks `.Restart`. |
| **Method** | `POST` |
| **URL** | `target` → `modals/system-config-modal.lp` |
| **Body** | `action=system_reboot`, `CSRFtoken` |
| **Response handling** | `wait_for_webserver_down("system_reboot")` (external) |

Excerpt (L3):

```javascript
$("#btn-system-reboot").click(function(){ ... confirmationDialogue(...,"Restart");
$(document).on("click",".Restart",function(){ a.call(this)}); ... });
// a() -> resetReboot($("#rebooting-msg"), $(this), "system_reboot")
```

### 2.2 Factory reset (`system_reset`)

| Trigger | `#btn-system-reset` (L5) → `.Factory` confirm |
| Method | `POST` |
| URL | `target` |
| Body | `action=system_reset`, `CSRFtoken` |
| Prerequisite | Same `resetrtfdValue` fast-path as reboot; else factory confirm dialog. |

### 2.3 Semi-reset (`system_softReset`)

| Trigger | `#btn-system-softReset` (L6) → `.SoftReset` |
| Method | `POST` |
| Body | `action=system_softReset`, `CSRFtoken` |

### 2.4 Scheduled reboot (`schedulerebootset`)

| Trigger | `#btn-schedule-reboot` click (L4) |
| Prerequisite | `#date_schedule` and `#time_schedule` non-empty; composed `schedule_time` must be **after** `system_time` (modal inline `system_time`, L34). On success hides schedule controls. If `schedule_reboot_get == "1"` (L6), schedule UI hidden on load. |
| Method | `POST` |
| URL | `target` |
| Body | `action=schedulerebootset`, `paramvalue=<ISO-like>`, `CSRFtoken` where `paramvalue = date + "T" + time + ":00Z"`. |

**Note:** Saved config modal HTML has **no** `#btn-schedule-reboot` / date fields — handlers are dead code unless another build injects markup.

### 2.5 BOOTP / “LAN Upgrade” (`system_bootp`)

| Trigger | `#btn-system-bootp` click (L2) → confirm → `.LAN` click |
| Method | `POST` |
| Body | `action=system_bootp`, `CSRFtoken` |
| Prerequisite | `confirmationDialogue(T.lanUpgradeMsg, T.lanUpgrade)`; strings in modal script L37–39. |

**Saved HTML:** no `#btn-system-bootp` (map already noted).

### 2.6 Export configuration (`export_config`)

| Trigger | `.export-config` click (L8–9) |
| Method | `POST` (via `$.fileDownload`) |
| URL | `target` |
| Data | `[{ name: "action", value: "export_config" }, { name: "CSRFtoken", value: … }]` |
| UI | `#exporting-msg` / `#export-failed-msg` |

**Saved HTML:** no `.export-config` control.

**Server (2026-10-12):** authenticated `POST` returns a **Technicolor `THENC`** binary (`CIPHERKEY=GW` labels only). Decrypt tooling: `scripts/decrypt_f1_config_export.py`; key acquisition: `findings/f1-config-export-decrypt-2026-10-12.md`, `findings/f1-hardware-key-blocker-2026-10-12.md`.

### 2.7 Import configuration (`import_config` via upload)

| Trigger | `.import-config` click (L11–12) |
| Prerequisite | `#file-import` non-empty; extension **`.bin` only**; size ≤ **1048576** bytes. |
| Upload | `$.fileUpload($("#form-import"), { params: { CSRFtoken } })` |
| On success | Shows `#rebooting-msg`, `wait_for_webserver_down("import_config")` |

**Implied POST target:** `action` likely inside `#form-import` (not in saved modal). **Saved HTML:** no `#form-import` / `#file-import`.

### 2.8 Firmware upload (`upgradefw`)

| Trigger | `.upgradefw` click (L16–17) |
| Prerequisite | `#file-upgradefw` set; extension ∈ `rbi`, `fw`, `pkgtb`; optional size check vs bank (below). |
| Pre-check | `$.ajax({ url: target, data: "action=getbanksize", dataType: "json", timeout: 5000 })` — if `success=="true"` and file size > `banksize`, show `#upgrade-too-big-msg`. |
| Upload | `$.fileUpload($("#form-upgradefw"), { params: { CSRFtoken } })` + `tch.showProgress(T.upgrading)` |
| On upload success | `wait_for_upgradefw()` |

**Saved HTML:** no `#form-upgradefw` / `#file-upgradefw` / `.upgradefw`.

### 2.9 Firmware status poll (`upgradefwstatus`)

| Trigger | Called from `wait_for_upgradefw` after successful upload (L14–15) |
| Method | `GET` (jQuery `$.ajax` default) |
| URL | `target` with query `action=upgradefwstatus` |
| Params | `data: "action=upgradefwstatus"`, `dataType: "json"`, `timeout: 15000` |
| Loop | On `success=="true"`, reschedule every **10s** (`c=1E4`). On failure, map `errorcode` `1`, `255`, `16` to user strings (`T.noFreeMemory`, `T.incorrectFirmware`, `T.wrongKey`). |

Excerpt (L14):

```javascript
$.ajax({url:target,data:"action=upgradefwstatus",timeout:b,dataType:"json"})
```

**Map vs script:** `f1-api-map.md` lists `upgradefwstatus` among POST actions from script names; **this file shows status polling as GET**. Live `findings/tried.md`: hand-built **POST** `action=upgradefwstatus` → 403; **GET** `?action=upgradefwstatus` → HTML modal (not JSON).

### 2.10 Firmware bank size (`getbanksize`)

| Trigger | During `.upgradefw` click before upload (L16) |
| Method | `GET` |
| URL | `target?action=getbanksize` |
| Expected JSON | `{ success: "true", banksize: "<number>" }` (parsed with `Number(a.banksize)`). |

---

## 3. CSRF, session, and generic form submit (frontend)

### 3.1 CSRF token

| Location | Mechanism |
|----------|-----------|
| `login.lp.html` L7 | `<meta name="CSRFtoken" content="REDACTED">` |
| `gateway.lp.authenticated.html` L9 | Same meta on authenticated shell |
| `password.lp.html` L6 | Meta on change-password page |
| `system-config-min.js` | Reads meta on every POST / download / upload params |
| `srp-min.js` L85, L89–90 | `$.post(..., { CSRFtoken, I, A })` then `{ CSRFtoken, M }` |
| `contentsharing-modal.lp.html` L71 | `tch.elementCSRFtoken()` → `{ name, value }` pair for `tch.loadModal` POST data (`main-min.js` L309, L305–316) |

Saved modal forms use `method="post"` and `action="modals/….lp"` but **no hidden `CSRFtoken` fields** in HTML grep — token is injected by JS (`meta` or `elementCSRFtoken`).

### 3.2 Session / cookies

- **Not set in JavaScript** in saved files. Session is implied by browser cookie jar on `GET`/`POST` to the gateway host.
- HAR summary (`har-192.168.2.1-summary.txt`): successful login via two `POST /authenticate` calls; cookies not exported in HAR note (`f1-ui-leads-23.1b.md`).
- **Sign out:** `gateway.lp.authenticated.html` L65 — `<a href="/" id="signout">` (navigation only in HTML; logout logic likely in `main-min.js`).

### 3.3 SRP login (`srp-min.js` + `login.js`)

| Step | Method | URL (from findings + HAR) | Body fields |
|------|--------|---------------------------|-------------|
| Identify | `POST` | `/authenticate` | `CSRFtoken`, `I` (username), `A` (client ephemeral) |
| Verify | `POST` | `/authenticate` | `CSRFtoken`, `M` (client proof) |
| Server identify response | — | — | JSON `s`, `B` (`auth-identify.json` sample) |

`SRP.prototype.identify` (L89–90): first argument `A` is **path** stored in variable `A` inside closure (overloaded name) — `login.js` passes `"/authenticate"`.

Password change (`password.lp`, guided modal):

| Step | POST target | Fields |
|------|-------------|--------|
| After `generateSaltAndVerifier` | Path arg e.g. `/password` | `CSRFtoken`, `salt`, `verifier`, `cryptedpassword` (L90–91) |
| Identify current password | `srp.identify("/password", 'User', …)` in modal inline script |

### 3.4 Modal load and JSON `.lp` GETs

**From `main-min.js` (§7) and saved HTML / captures:**

| Request | Source | Purpose |
|---------|--------|---------|
| `GET /gateway.lp?action=scheduleReboot` | HAR L11, L24; saved `gateway-scheduleReboot.json` | JSON schedule metadata |
| `GET /gateway.lp?auto_update=true&getSessionStatus=true` | `findings/tried.md`; `gateway-session.json` | `{"current_role":"admin"}` |
| `GET /modals/parental-modal.lp?action=smartwifi` | `modals-parental-modal.lp.html` L77 | Poll every 3s; toggles UI / disables `#save-config` when smartwifi phase 2 |

- `tch.loadModal` / `D()` — initial modal open uses `GET` `data-remote` (L316–318); in-modal navigation uses `loadModal` with optional POST body (L305–316).
- `#save-config` — POST SAVE pipeline (L330–332); `contentsharing-modal.lp.html` L105–116 adds local UI-only success messaging before/after save.

### 3.5 Content-sharing custom POST shape

`contentsharing-modal.lp.html` L60–73: USB eject builds POST array `action=eject`, `ejectIndex=<index>`, plus CSRF via `tch.loadModal("/modals/contentsharing-modal.lp", tparam, …)` — pattern suggests **POST body fields** to the modal URL, not a separate API.

---

## 4. Comparison with `findings/f1-api-map.md`

| Topic | Map said | Newly verified from JS/HTML files |
|-------|----------|-------------------------------------|
| Config script actions list | reboot, reset, semi-reset, export/import, BOOTP, upgradefw, upgradefwstatus, getbanksize, schedulerebootset | **Confirmed** names and POST vs GET split: **status/banksize = GET**; destructive/config ops = **POST** with `action` + `CSRFtoken`. |
| Upgrade handler exists, controls absent | Yes | **Confirmed** — handlers bind to missing DOM ids/classes in saved `modals-system-config-modal.lp.html`. |
| `upgradefwstatus` | Listed with POST actions | **Refined:** browser poll uses **GET** `action=upgradefwstatus` (L14); map’s POST 403 vs GET HTML from `tried.md` still applies to non-browser probes. |
| Auth / CSRF / forms | Meta CSRF, SRP, modal POST forms | **Confirmed** meta usage in `system-config-min.js` and `srp-min.js`; forms lack inline CSRF fields. |
| `scheduleReboot` / `getSessionStatus` on `gateway.lp` | Mentioned | **Confirmed** response shapes from saved JSON; **parental** `smartwifi` GET **added** from modal script. |
| `loadModal` / save-config | Attributed to `main-min.js` | **Verified** in recovered `main-min.js` L305–316, L330–333, L334. |
| Backend accepts removed controls | “Not tested” | Still **unknown**; JS proves client-side intent only. |

---

## 5. What cannot be known from JavaScript alone

1. **Server enforcement** — `export_config` **works** for a normal admin session when CSRF is current (hidden handler); see `findings/f1-hidden-action-boundary-2026-10-12.md`. Other actions (`system_bootp`, `upgradefw`, etc.) remain uneven (403 on some hand-built POSTs is live data, not JS).
2. **Cookie name, path, HttpOnly, rotation** — no `document.cookie` writes in reviewed scripts.
3. **Multipart field names for firmware/import** — `$.fileUpload` only injects `params` as hidden inputs; file input name and any `action=` hidden field come from server HTML (`#form-upgradefw` not in saved config modal).
4. **Whether GET `upgradefwstatus` returns JSON during a real upgrade** — script expects JSON; idle GET capture returned HTML modal.
5. **Server-side rules** for redirect IP from `login.lp`, cookie `fileDownload`, and when modal POST returns 403.

---

## 6. Security note (scope)

Documenting handlers in minified JS **does not** imply an exploitable vulnerability. Removed DOM nodes and nginx 403 responses show the **shipped HTML + server** may not expose those code paths to a normal admin session.

---

## 7. `main-min.js` helpers (used by `system-config-min.js`)

Source: `artifacts/ui/main-min.js` (from HAR). Line numbers refer to the recovered file.

### 7.1 `tch.elementCSRFtoken` (internal `A`, L309)

| | |
|--|--|
| **Returns** | `{ name: "CSRFtoken", value: $("meta[name=CSRFtoken]").attr("content") }` |
| **HTTP** | None by itself; consumed as a POST field by callers. |

Excerpt:

```javascript
function A(){return{name:"CSRFtoken",value:$("meta[name=CSRFtoken]").attr("content")}}
// … b.elementCSRFtoken=A (L334)
```

### 7.2 `tch.loadModal` (internal `q`, L305–316, exported L334)

Loads or refreshes the open Bootstrap modal body.

| | |
|--|--|
| **Trigger** | `tch.loadModal(url, postData?, callback?)`; also `q(b)` from nav tabs (L333), table ops (L315–316), refresh (L324), `#save-config` (L331–332). |
| **Method** | **GET** if `postData` omitted or empty; **POST** if `postData` is a non-empty array (jQuery `.load(url, data)`). |
| **URL** | First argument `a` (e.g. `/modals/contentsharing-modal.lp`, or `$(".modal form").attr("action")`). |
| **Parameters** | `postData`: array of `{ name, value }` (e.g. `action`, `CSRFtoken`, table fields). Refresh uses `[{ operation: "REFRESH" }, elementCSRFtoken()]`. Save uses `action=SAVE`, `fromModal=YES`, serialized form fields, `CSRFtoken`. |
| **Prerequisites** | On 403 or `#sign-me-in` in response → `window.location="/login.lp"` (L305–306). Shows progress via `M(waitMsg)` unless first field is `REFRESH`. |

Excerpt (L305–306):

```javascript
function q(a,b,c){ … $(".modal").load(a,b,function(a,b,e){
  … 403===e.status||0<$("#sign-me-in").length ? (M(loginMsg),window.location="/login.lp") : …
})}
```

**Example (contentsharing eject, `contentsharing-modal.lp.html` L60–73):** `POST` `/modals/contentsharing-modal.lp` with `action=eject`, `ejectIndex`, `CSRFtoken`.

### 7.3 `#save-config` (L330–332)

| | |
|--|--|
| **Trigger** | Click `#save-config` or `.Confirm.EasyMesh.Config.Changes` |
| **Method** | POST (via `tch.loadModal`) |
| **URL** | `$(".modal form").attr("action")` |
| **Body** | `serializeArray()` of modal form, prefixed with `action=SAVE`, `fromModal=YES`, `CSRFtoken`; sensitive password-like fields AES-CBC encrypted with `sessionStorage.session_key` when present (L330–331). |
| **After success** | If USB3 flag mismatch → `wait_for_webserver_down()` + reboot progress UI. |

### 7.4 `confirmationDialogue` (L338–340)

| | |
|--|--|
| **Trigger** | Called from `system-config-min.js` (reboot/reset/BOOTP) and `H()` for scheduled reboot alert (L320, L333). |
| **HTTP** | **None** — builds `.popUp` / `.popUpBG` DOM with `#ok` and `#cancel` buttons. |
| **Parameters** | `(bodyHtml, title, okButtonClass?, okLabel?, cancelId?, cancelLabel?)` — third arg becomes extra CSS class on OK (e.g. `"Restart"`, `"Factory"`, `"LAN"`, `"SoftReset"`) for delegated clicks in config script. |

### 7.5 `$.fileDownload` (jQuery plugin, L294–301)

| | |
|--|--|
| **Trigger** | `.export-config` in `system-config-min.js` |
| **Method** | Configurable; config script uses **`POST`**. |
| **URL** | First arg `m` → `target` (`modals/system-config-modal.lp`). |
| **Data** | Array of `{ name, value }` → hidden `<form method=POST action=url>` fields (`action`, `CSRFtoken`, …). |
| **Success detection** | Polls `document.cookie` for `fileDownload=true` (default names L296); then `successCallback`. |

### 7.6 `$.fileUpload` (jQuery plugin, L302–303)

| | |
|--|--|
| **Trigger** | `.import-config` / `.upgradefw` in `system-config-min.js` |
| **Method** | **POST** — native `form.submit()` with `enctype` implied by form (file input in server HTML). |
| **URL** | Form’s `action` attribute (`#form-import`, `#form-upgradefw`). |
| **Parameters** | `params` object → prepended hidden inputs (`CSRFtoken` only in config script). File field(s) remain from form DOM. |
| **Response** | Hidden iframe `onload` → parse `iframe.body.innerHTML` as JSON if possible → `completeCallback(form, parsed)`. |

### 7.7 `wait_for_webserver_down` / `wait_for_webserver_running` (L340–342)

Globals: `refreshDelay=3000`, `refreshTimeout=5000`, `get_action`, `newIPAddress` (implicit).

**`wait_for_webserver_down(optionalAction)` (L342)**

| Step | Method | URL | Parameters |
|------|--------|-----|------------|
| 1 | GET | `login.lp` | Query: `action=redirect`, `param=get_action` (set from arg, e.g. `system_reboot`, `import_config`) — response stored in `newIPAddress`. |
| 2 | AJAX | `$(".modal form").attr("action")` | No body; `timeout=5000`. While request **succeeds**, reschedule self every 3s (box still answering). |
| 3 | On AJAX **fail** | — | After 3s, call `wait_for_webserver_running(newIPAddress)`. |

**`wait_for_webserver_running(ipHint)` (L341)**

| Step | Method | URL | Behavior |
|------|--------|-----|----------|
| 1 | AJAX | `/` | `timeout=5000`. **Done** → `window.location.href="/"`. |
| 2 | **Fail** | — | If `get_action` is `system_reset` or `import_config`, wait **150s** then `http://` + `ipHint`; else retry `wait_for_webserver_running` every 3s. |

Config script passes action name into `wait_for_webserver_down(c)` on reboot/reset POST success (L1).

### 7.8 Other `tch` HTTP (context for session)

| Feature | Lines | Method | URL | Parameters |
|---------|-------|--------|-----|------------|
| Session poll (authenticated) | L320–321 | GET | `/gateway.lp?auto_update=true` | `getSessionStatus: true` — role mismatch → `/login.lp` |
| Scheduled reboot banner | L333–334 | GET | `/gateway.lp?action=scheduleReboot` | JSON `rebootTime`, `systemTime`, `alertMsg` |
| Sign out | L327–328 | POST | `/` | `do_signout=1`, `CSRFtoken` (dynamic form) |
| Language change | L336–337 | POST | `/gateway.lp` | `action=languageChanged`, `langVal`, `CSRFtoken` |

---

## 8. `login.js` (recovered, 202 lines)

| Feature | Lines | Method | URL | Parameters |
|---------|-------|--------|-----|------------|
| Session poll | L9–20 | GET | `/login.lp?auto_update=true` | `getSessionStatus: true` |
| Sign in | L51–166 | via `srp.identify` | `/authenticate` | `CSRFtoken`, `I`, `A`, then `M` (`srp-min.js`) |
| CSRF refresh on 403 | L113–125 | GET | `login.lp` | Parse new meta `CSRFtoken`, retry identify |
| Last-access path | L96–99 | GET | `login.lp` | `action=lastaccess` before redirect |
| Forgot-password flow | L168–200 | `srp.identify` | `/authenticate` | username `forgotpassword` → redirect `/password-reset.lp` |

Stores `session_key` in `sessionStorage` after login (L93–95) for modal password encryption in `main-min.js`.

---

*Generated from local artifacts only; secrets redacted in saved copies.*
