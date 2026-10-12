// ==UserScript==
// @name         Genesis F1 artifact grabber
// @namespace    https://github.com/privateuseonlycodelol/genesis
// @version      1.8.1
// @description  Wide F1 UI capture: JS/LinkFinder chase, HAR import, verbatim bodies, traffic tap.
// @author       Genesis
// @match        http://192.168.2.1/*
// @grant        GM_xmlhttpRequest
// @grant        GM_download
// @grant        GM_addStyle
// @connect      192.168.2.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  const BASE = "http://192.168.2.1";
  const HOST = "192.168.2.1";
  const DELAY_MS = 1500;
  const DB_NAME = "genesis-f1-grab-v3";
  const DB_VERSION = 1;
  /** Bump when stored bodies must be re-fetched (e.g. removed redaction). */
  const CAPTURE_FORMAT = 2;

  /** Names noticed in source. Only GET_ACTION_PROBES are fetched. */
  const UNSAFE_ACTIONS = new Set([
    "export_config",
    "import_config",
    "schedulerebootset",
    "system_bootp",
    "system_reboot",
    "system_reset",
    "system_softReset",
    "upgradefw",
    "languageChanged",
    "SAVE",
    "PasswordChanged",
    "ReleaseAndRenew",
  ]);
  /** Stable nonexistent action. Same response as this means the candidate name was not special. */
  const CONTROL_ACTION = "gf1nosuchaction";

  const ACTION_NAMES = [
    "scheduleReboot",
    "smartwifi",
    "upgradefwstatus",
    "getbanksize",
    "getSessionStatus",
    "export_config",
    "import_config",
    "schedulerebootset",
    "system_bootp",
    "system_reboot",
    "system_reset",
    "system_softReset",
    "upgradefw",
    "languageChanged",
    "lastaccess",
    "redirect",
    "SAVE",
    "AJAX-GET",
    "PasswordChanged",
    "ReleaseAndRenew",
  ];

  const KNOWN_JS = [
    "/js/004_wireless.js",
    "/js/asmcrypto-min.js",
    "/js/chart-min.js",
    "/js/device-min.js",
    "/js/diagnostics-ping-modal-min.js",
    "/js/dmz-modal-min.js",
    "/js/ethernet-min.js",
    "/js/firewall-min.js",
    "/js/gateway.js",
    "/js/internet-dns-min.js",
    "/js/internet-routed-settings-min.js",
    "/js/jquery-eval-patch.js",
    "/js/logviewer-min.js",
    "/js/login.js",
    "/js/main-min.js",
    "/js/media-min.js",
    "/js/password.js",
    "/js/srp-min.js",
    "/js/system-config-min.js",
    "/js/tod-modal-min.js",
    "/js/wanservices-min.js",
    "/js/wireless-ap-modal-newEM.js",
    "/js/wireless-radio-modal-newEM.js",
    "/js/wireless-qrcode-modal-min.js",
  ];

  const KNOWN_MODALS = [
    "/modals/basicview-accesscode-modal.lp",
    "/modals/broadband-modal.lp",
    "/modals/contentsharing-modal.lp",
    "/modals/device-modal.lp",
    "/modals/diagnostics-connection-modal.lp",
    "/modals/diagnostics-igmpproxy-modal.lp",
    "/modals/diagnostics-network-modal.lp",
    "/modals/diagnostics-ping-modal.lp",
    "/modals/dmz-modal.lp",
    "/modals/dyndns-wanservices-modal.lp",
    "/modals/ethernet-modal.lp",
    "/modals/firewall-modal.lp",
    "/modals/internet-modal.lp",
    "/modals/l2tp-ipsec-server-modal.lp",
    "/modals/logviewer-modal.lp",
    "/modals/parental-modal.lp",
    "/modals/system-config-modal.lp",
    "/modals/system-info-modal.lp",
    "/modals/time-management-modal.lp",
    "/modals/tod-modal.lp",
    "/modals/wanservices-modal.lp",
    "/modals/wireless-ap-modal-newEM.lp",
    "/modals/wireless-radio-modal-newEM.lp",
    "/modals/wireless-wps-modal-newEM.lp",
    "/modals/wireless-qrcode-modal.lp",
    "/modals/internet-ex-modal.lp",
    "/modals/ipv6devices-modal.lp",
    "/modals/basicview-wifissid-modal.lp",
    "/modals/basicview-wifissid5GHz-modal.lp",
    "/modals/basicview-wifipsk-modal.lp",
    "/modals/basicview-wifipsk5GHz-modal.lp",
    "/modals/basicview-wifiguest-modal.lp",
    "/modals/basicview-wifiguest5GHz-modal.lp",
  ];

  const SHELL_PAGES = ["/gateway.lp", "/login.lp", "/password.lp", "/home.lp"];
  const EXTRA_STATIC = [
    "/css/gw.css",
    "/css/responsive.css",
    "/favicon.ico",
    "/img/logo.png",
  ];
  const SENSITIVE = new Set(["/modals/wireless-qrcode-modal.lp"]);
  const BLOCK = new Set(["/authenticate"]);

  /** Read-only GETs with query params (session cookie required for JSON, not login HTML). */
  const GET_ACTION_PROBES = [
    { path: "/gateway.lp?action=scheduleReboot", method: "probe-get-action" },
    { path: "/gateway.lp?auto_update=true&getSessionStatus=true", method: "probe-get-session" },
    { path: "/modals/parental-modal.lp?action=smartwifi", method: "probe-get-action" },
    { path: "/modals/system-config-modal.lp?action=getbanksize", method: "probe-get-action" },
    { path: "/modals/system-config-modal.lp?action=upgradefwstatus", method: "probe-get-action" },
  ];

  const PROBES = [
    ["/robots.txt", "probe-wellknown"],
    ["/sitemap.xml", "probe-wellknown"],
    ["/crossdomain.xml", "probe-wellknown"],
    ["/clientaccesspolicy.xml", "probe-wellknown"],
    ["/.well-known/security.txt", "probe-wellknown"],
    ["/overview.lp", "probe-homeware-name"],
    ["/system.lp", "probe-homeware-name"],
    ["/modals/gateway-modal.lp", "probe-homeware-name"],
    ["/ajax/wirelesscard.lua", "probe-known-ajax"],
    ["/internet-dhcp-routed.lp", "probe-homeware-name"],
    ["/css/font-awesome-ie7.css", "probe-homeware-name"],
  ];

  const QUEUE_QUERY_KEYS = new Set([
    "action",
    "auto_update",
    "getSessionStatus",
    "requested_params",
    "intf",
    "submenu",
    "getNTP",
  ]);

  let busy = false;
  let dbPromise = null;

  const QUIET_OUTCOMES = new Set([
    "IGNORED_PARAMETER",
    "ACTION_CONTROL",
    "AUTH_REQUIRED",
    "NOT_FOUND",
    "UNSAFE_TO_PROBE",
  ]);

  function buildKnownActionProbes() {
    const items = [];
    const bases = new Set();
    for (const p of GET_ACTION_PROBES) {
      items.push({ path: p.path, method: p.method, from: "" });
      const split = splitRequestKey(p.path);
      if (split.action) bases.add(split.pathname);
    }
    for (const base of bases) {
      items.push({
        path: `${base}?action=${CONTROL_ACTION}`,
        method: "probe-action-control",
        from: base,
      });
    }
    items.push({
      path: "/login.lp?auto_update=true&getSessionStatus=true",
      method: "probe-get-session",
      from: "",
    });
    return items;
  }

  function parseResponseHeaders(raw) {
    const out = {};
    if (!raw) return out;
    for (const line of raw.split(/\r?\n/)) {
      const i = line.indexOf(":");
      if (i > 0) out[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
    }
    return out;
  }

  function pickHeaders(h) {
    return {
      contentType: h["content-type"] || "",
      contentLength: h["content-length"] || "",
      server: h["server"] || "",
    };
  }

  function jsonKeysDeep(value, prefix = "", depth = 0) {
    if (depth > 4) return [];
    const keys = [];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      for (const k of Object.keys(value)) {
        const p = prefix ? `${prefix}.${k}` : k;
        keys.push(p);
        keys.push(...jsonKeysDeep(value[k], p, depth + 1));
      }
    }
    return keys;
  }

  async function loadTraffic() {
    const t = await getMeta("traffic");
    return Array.isArray(t) ? t : [];
  }

  async function appendTraffic(entry) {
    let url = entry.url || "";
    try {
      const u = new URL(url, BASE);
      if (u.hostname !== HOST) {
        await mergeOffHostUrls([
          {
            kind: "off-host",
            url: u.href,
            host: u.hostname,
            from: "(live traffic)",
            via: entry.via || "traffic",
          },
        ]);
        return;
      }
      url = u.pathname + u.search;
    } catch (_) {
      if (!String(url).includes(HOST)) {
        if (String(url).trim().startsWith("data:")) {
          await mergeOffHostUrls(extractOffHostFromText(String(url), "(live traffic)", entry.via || "traffic"));
        }
        return;
      }
    }
    const t = await loadTraffic();
    t.push({ ...entry, url, at: new Date().toISOString() });
    if (t.length > 8000) t.splice(0, t.length - 8000);
    await setMeta("traffic", t);
  }

  async function mergeForms(forms) {
    if (!forms?.length) return;
    const prev = (await getMeta("forms")) || [];
    const key = (f) => `${f.source}|${f.action}|${f.method}|${f.id}`;
    const seen = new Set(prev.map(key));
    for (const f of forms) {
      if (!seen.has(key(f))) {
        prev.push(f);
        seen.add(key(f));
      }
    }
    await setMeta("forms", prev);
  }

  async function mergePathLiterals(literals, from) {
    if (!literals?.length) return;
    const prev = (await getMeta("pathLiterals")) || [];
    const seen = new Set(prev.map((x) => `${x.path}|${x.from}`));
    for (const p of literals) {
      const row = { path: p, from };
      if (!seen.has(`${p}|${from}`)) {
        prev.push(row);
        seen.add(`${p}|${from}`);
      }
    }
    await setMeta("pathLiterals", prev);
  }

  /** Record data: and non-gateway URLs for RE leads. Never queued for GET. */
  async function mergeOffHostUrls(items) {
    if (!items?.length) return;
    const prev = (await getMeta("offHostUrls")) || [];
    const seen = new Set(prev.map((r) => `${r.kind}|${r.url || r.preview}|${r.from}|${r.via}`));
    for (const row of items) {
      const key = `${row.kind}|${row.url || row.preview}|${row.from}|${row.via}`;
      if (seen.has(key)) continue;
      seen.add(key);
      prev.push({ ...row, at: new Date().toISOString() });
    }
    if (prev.length > 8000) prev.splice(0, prev.length - 8000);
    await setMeta("offHostUrls", prev);
  }

  function extractOffHostFromText(text, fromPath, defaultVia) {
    const out = [];
    if (!text || text.length < 4) return out;
    const addHref = (href, via) => {
      const h = (href || "").trim();
      if (!h || h.length > 4000) return;
      if (h.startsWith("#") || h.startsWith("javascript:")) return;
      if (h.startsWith("data:")) {
        if (!/^data:(?:image|text|application|font)\//i.test(h)) return;
        const semi = h.indexOf(";");
        const mime = semi > 5 ? h.slice(5, semi) : "unknown";
        out.push({
          kind: "data",
          mime,
          preview: h.slice(0, 160),
          approxChars: h.length,
          from: fromPath || "",
          via: via || defaultVia || "chase",
        });
        return;
      }
      let parseable = h;
      if (h.startsWith("//")) parseable = `http:${h}`;
      if (!/^https?:\/\//i.test(parseable)) return;
      try {
        const u = new URL(parseable);
        if (!u.hostname || u.hostname === HOST) return;
        if (!u.hostname.includes(".")) return;
        out.push({
          kind: "off-host",
          url: u.href,
          host: u.hostname,
          from: fromPath || "",
          via: via || defaultVia || "chase",
        });
      } catch (_) {
        /* skip */
      }
    };
    for (const m of text.matchAll(/data:(?:image|text|application|font)\/[^"'`\s)>]+/gi)) addHref(m[0], "regex-data");
    for (const m of text.matchAll(/https?:\/\/[^\s"'`<>]+/gi)) addHref(m[0], "regex-http");
    for (const m of text.matchAll(/\/\/[a-z0-9][a-z0-9.-]*\.[a-z]{2,}[^\s"'`<>]*/gi)) addHref(m[0], "regex-protocol-relative");
    return out;
  }

  function installTrafficTap() {
    if (document.documentElement.dataset.gf1Tap) return;
    document.documentElement.dataset.gf1Tap = "1";
    window.addEventListener("message", (e) => {
      if (e.source !== window || e.data?.type !== "GF1_TRAFFIC") return;
      appendTraffic(e.data).catch(() => {});
    });
    const code = `(function(){
if(window.__gf1TapInstalled)return;window.__gf1TapInstalled=1;
function bodyStr(b){if(b==null||b===undefined)return'';return typeof b==='string'?b:JSON.stringify(b);}
function emit(o){window.postMessage(Object.assign({type:'GF1_TRAFFIC'},o),'*');}
var xo=XMLHttpRequest.prototype.open,xs=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this._gf1m=m;this._gf1u=u;return xo.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(b){try{emit({via:'xhr',method:(this._gf1m||'GET').toUpperCase(),url:String(this._gf1u||''),body:bodyStr(b)})}catch(e){}return xs.apply(this,arguments);};
if(window.fetch){var of=window.fetch;window.fetch=function(i,n){var m=(n&&n.method)||'GET';var u=typeof i==='string'?i:(i&&i.url)||'';emit({via:'fetch',method:String(m).toUpperCase(),url:String(u),body:bodyStr(n&&n.body)});return of.apply(this,arguments);};}
if(window.jQuery&&window.jQuery.ajax){var oa=window.jQuery.ajax;window.jQuery.ajax=function(a,b){var m='GET',u='',d='';if(typeof a==='object'){b=a;a=b.url;}if(b){m=b.type||b.method||'GET';u=b.url||'';d=b.data||'';}else u=a||'';emit({via:'jquery',method:String(m).toUpperCase(),url:String(u),body:bodyStr(d)});return oa.apply(this,arguments);};}
})();`;
    const el = document.createElement("script");
    el.textContent = code;
    (document.head || document.documentElement).appendChild(el);
    el.remove();
  }

  GM_addStyle(`
    #genesis-f1-grabber {
      position: fixed; right: 12px; bottom: 12px; z-index: 2147483646;
      font: 12px/1.35 system-ui, sans-serif; color: #e8e8e8;
      background: #1a1a1e; border: 1px solid #444; border-radius: 8px;
      padding: 12px; width: 340px; box-shadow: 0 4px 20px rgba(0,0,0,.45);
    }
    #genesis-f1-grabber h3 { margin: 0 0 8px; font-size: 13px; color: #fff; }
    #genesis-f1-grabber .step { margin: 0 0 10px; padding: 8px; background: #141418; border-radius: 6px; }
    #genesis-f1-grabber .step h4 { margin: 0 0 6px; font-size: 11px; color: #9cf; font-weight: 600; }
    #genesis-f1-grabber .step.on { outline: 1px solid #4a8; }
    #genesis-f1-grabber label { display: flex; gap: 6px; align-items: flex-start; margin: 4px 0; font-size: 11px; }
    #genesis-f1-grabber label span { color: #ccc; }
    #genesis-f1-grabber button {
      display: block; width: 100%; margin: 0; padding: 8px; border-radius: 4px;
      border: 1px solid #555; background: #2a2a32; color: #eee; cursor: pointer;
    }
    #genesis-f1-grabber button.gf1-primary { background: #2d4a3e; border-color: #4a8; font-weight: 600; }
    #genesis-f1-grabber button.gf1-quiet { margin-top: 6px; padding: 5px; font-size: 11px; color: #bbb; }
    #genesis-f1-grabber button:disabled { opacity: 0.45; cursor: not-allowed; }
    #genesis-f1-grabber .plan, #genesis-f1-grabber .now, #genesis-f1-grabber .stat {
      font-size: 11px; color: #cde; margin: 6px 0 0;
    }
    #genesis-f1-grabber .log {
      margin-top: 8px; max-height: 110px; overflow: auto; font-size: 10px;
      color: #888; border-top: 1px solid #333; padding-top: 6px;
    }
  `);

  function log(el, msg) {
    const line = document.createElement("div");
    line.textContent = msg;
    el.appendChild(line);
    while (el.childNodes.length > 60) el.removeChild(el.firstChild);
    el.scrollTop = el.scrollHeight;
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function tick() {
    return new Promise((r) => setTimeout(r, 0));
  }

  /** Scan HAR text for request URLs. No Worker: the gateway CSP blocks blob workers. */
  async function collectHarUrls(text, report) {
    const items = [];
    const harOffHost = [];
    const seen = new Set();
    const needle = '"url"';
    let from = 0;
    let scanned = 0;
    while (from < text.length) {
      const i = text.indexOf(needle, from);
      if (i < 0) break;
      let p = i + needle.length;
      while (p < text.length && text[p] <= " ") p += 1;
      if (text[p] !== ":") {
        from = i + needle.length;
        continue;
      }
      p += 1;
      while (p < text.length && text[p] <= " ") p += 1;
      if (text[p] !== '"') {
        from = i + needle.length;
        continue;
      }
      p += 1;
      let url = "";
      while (p < text.length && url.length < 4000) {
        const c = text[p];
        if (c === "\\") {
          const n = text[p + 1];
          url += n === "u" ? text.slice(p + 2, p + 6) : n || "";
          p += n === "u" ? 6 : 2;
          continue;
        }
        if (c === '"') break;
        url += c;
        p += 1;
      }
      from = p + 1;
      scanned += 1;
      if (url.includes(HOST)) {
        try {
          const u = new URL(url);
          if (u.hostname === HOST) {
            const key = requestKeyFromString(`${u.pathname}${u.search}`, "/", { preserveQuery: true });
            if (key && !seen.has(key)) {
              seen.add(key);
              items.push({ path: key, method: "import-har", from: "har-import" });
            }
          } else {
            harOffHost.push({
              kind: "off-host",
              url: u.href,
              host: u.hostname,
              from: "har-import",
              via: "import-har",
            });
          }
        } catch (_) {
          /* skip malformed */
        }
      } else if (/^https?:\/\//i.test(url) || url.startsWith("//") || url.startsWith("data:")) {
        harOffHost.push(...extractOffHostFromText(url, "har-import", "import-har"));
      }
      if (scanned % 150 === 0) {
        report(`HAR: scanned ${scanned} url fields, ${items.length} kept…`);
        await tick();
      }
    }
    return { items, scanned, harOffHost };
  }

  function isHtmlCapturePath(requestKey) {
    const { pathname } = splitRequestKey(requestKey);
    return pathname.endsWith(".lp") || pathname.endsWith(".html");
  }

  function extractApiHints(text) {
    const hints = [];
    const seen = new Set();
    const add = (name, kind) => {
      if (!name || seen.has(`${kind}:${name}`)) return;
      seen.add(`${kind}:${name}`);
      hints.push({ name, kind });
    };
    if (!text) return hints;
    for (const m of text.matchAll(/[?&]action=([A-Za-z0-9_-]+)/g)) add(m[1], "query-action");
    for (const m of text.matchAll(/action\s*[=:]\s*["']([A-Za-z0-9_-]+)["']/g)) add(m[1], "js-action-string");
    for (const m of text.matchAll(/action=([A-Za-z0-9_-]+)/g)) add(m[1], "action-literal");
    for (const m of text.matchAll(/requested_params=([A-Za-z0-9_-]+)/gi)) add(m[1], "requested-param");
    for (const name of ACTION_NAMES) {
      if (text.includes(name)) add(name, "known-action-name");
    }
    for (const m of text.matchAll(/data-action\s*=\s*["']([^"']+)["']/gi)) add(m[1], "data-action");
    for (const m of text.matchAll(/(?:url|target)\s*[=:]\s*["']([^"']+\.(?:lp|lua)[^"']*)["']/gi)) add(m[1], "url-literal");
    for (const m of text.matchAll(/fileDownload\s*\(\s*["'`]([^"'`]+)["'`]/g)) add(m[1], "fileDownload-target");
    for (const m of text.matchAll(/\$\.(?:post|get|ajax)\s*\(\s*["'`]([^"'`]+)["'`]/g)) add(m[1], "jquery-url");
    for (const m of text.matchAll(/name\s*:\s*["']([A-Za-z0-9_-]+)["']/g)) add(m[1], "object-field-name");
    if (text.includes("<")) {
      const doc = new DOMParser().parseFromString(text, "text/html");
      doc.querySelectorAll("[data-action], form[action], input[name], select[name], textarea[name], button[name]").forEach((el) => {
        const tag = el.tagName.toLowerCase();
        if (tag === "form") {
          const act = el.getAttribute("action");
          if (act) add(act.replace(/^\//, ""), "form-action-attr");
        } else {
          const da = el.getAttribute("data-action");
          if (da) add(da, "data-action");
          const n = el.getAttribute("name");
          if (n && n !== "CSRFtoken") add(n, "form-field-name");
        }
      });
    }
    return hints;
  }

  function extractFormsFromHtml(text, sourcePath) {
    if (!text || !text.includes("<form")) return [];
    const doc = new DOMParser().parseFromString(text, "text/html");
    const forms = [];
    doc.querySelectorAll("form").forEach((form, idx) => {
      const fields = [];
      form.querySelectorAll("input, select, textarea, button").forEach((el) => {
        const name = el.getAttribute("name");
        if (name) {
          fields.push({
            name,
            type: el.getAttribute("type") || el.tagName.toLowerCase(),
            id: el.getAttribute("id") || "",
          });
        }
      });
      forms.push({
        source: sourcePath,
        action: form.getAttribute("action") || "",
        method: (form.getAttribute("method") || "GET").toUpperCase(),
        id: form.getAttribute("id") || `form-${idx}`,
        fields,
      });
    });
    return forms;
  }

  function extractPathLiterals(text) {
    const s = new Set();
    if (!text) return [];
    for (const m of text.match(/(?<![A-Za-z0-9_])\/[A-Za-z0-9_./-]+\.(?:lp|js|lua|css|bin|json|xml|html)/gi) || []) {
      if (m.length > 200 || m.includes("://")) continue;
      s.add(m.split("?")[0]);
    }
    return [...s];
  }

  function summarizeOutcome(status, raw) {
    const notes = [];
    let outcome = classifyBody(status, raw);
    let jsonKeys = [];
    let jsonKeyPaths = [];
    if (status === 200) {
      const t = (raw || "").trim();
      if (t.startsWith("{") || t.startsWith("[")) {
        try {
          const j = JSON.parse(t);
          if (j && typeof j === "object" && !Array.isArray(j)) {
            jsonKeys = Object.keys(j).sort();
            jsonKeyPaths = jsonKeysDeep(j).sort();
            outcome = "application-json";
            if (j.success === true) notes.push("success=true");
            else if (j.success === false) notes.push("success=false");
            if ("errorcode" in j) notes.push("has-errorcode");
            if ("banksize" in j) notes.push("has-banksize");
            if ("current_role" in j) notes.push("has-current_role");
            if ("current_state" in j) notes.push("has-current_state");
          }
        } catch (_) {
          notes.push("json-parse-failed");
        }
      }
    }
    return { outcome, jsonKeys, jsonKeyPaths, notes };
  }

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        dbPromise = null;
        reject(err || new Error("IndexedDB open failed"));
      };
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (ev) => {
        const db = ev.target.result;
        if (!db.objectStoreNames.contains("records")) db.createObjectStore("records", { keyPath: "path" });
        if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta");
      };
      req.onsuccess = () => {
        if (settled) return;
        settled = true;
        resolve(req.result);
      };
      req.onerror = () => fail(req.error);
      req.onblocked = () =>
        fail(new Error("IndexedDB blocked — close other tabs on 192.168.2.1 and reload"));
    });
    return dbPromise;
  }

  function bodyLooksTampered(requestKey, body) {
    if (!body || typeof body !== "string") return false;
    const { pathname } = splitRequestKey(requestKey);
    if (pathname.endsWith(".js")) return body.includes("REDACTED");
    if (pathname.endsWith(".lp") || pathname.endsWith(".html")) {
      return /<meta[^>]*name\s*=\s*["']CSRFtoken["'][^>]*content\s*=\s*["']REDACTED["']/i.test(body);
    }
    return /CSRFtoken[=:][^"'&\s]*REDACTED|REDACTED"meta/i.test(body);
  }

  function recordTrusted(rec) {
    if (!rec || rec.status !== 200) return true;
    if (bodyLooksTampered(rec.path, rec.body)) return false;
    if (rec.captureFormat != null && rec.captureFormat !== CAPTURE_FORMAT) return false;
    const { pathname } = splitRequestKey(rec.path || "");
    if (/\.(png|gif|jpe?g|ico|woff2?|ttf|eot|bin)$/i.test(pathname) && typeof rec.body === "string" && rec.body.charCodeAt(0) === 0xfffd) {
      return false;
    }
    return true;
  }

  function clearRecordsStore() {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readwrite");
          tx.objectStore("records").clear();
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        })
    );
  }

  async function purgeTamperedHits() {
    const rows = await allRecords();
    const toDelete = rows.filter((r) => r.status === 200 && !recordTrusted(r)).map((r) => r.path);
    if (!toDelete.length) return 0;
    await openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readwrite");
          const store = tx.objectStore("records");
          for (const p of toDelete) store.delete(p);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        })
    );
    return toDelete.length;
  }

  async function ensureCacheGeneration() {
    const gen = await getMeta("captureFormat");
    if (gen === CAPTURE_FORMAT) {
      return purgeTamperedHits();
    }
    const count = (await allRecords()).length;
    await clearRecordsStore();
    await setMeta("captureFormat", CAPTURE_FORMAT);
    return count;
  }

  function putRecord(rec) {
    const stored = { ...rec, captureFormat: CAPTURE_FORMAT };
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readwrite");
          tx.objectStore("records").put(stored);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        })
    );
  }

  function allRecords() {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readonly");
          const req = tx.objectStore("records").getAll();
          req.onsuccess = () => resolve(req.result || []);
          req.onerror = () => reject(req.error);
        })
    );
  }

  function recordCount() {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readonly");
          const req = tx.objectStore("records").count();
          req.onsuccess = () => resolve(req.result || 0);
          req.onerror = () => reject(req.error);
        })
    );
  }

  function getMeta(key) {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("meta", "readonly");
          const req = tx.objectStore("meta").get(key);
          req.onsuccess = () => resolve(req.result);
          req.onerror = () => reject(req.error);
        })
    );
  }

  function setMeta(key, value) {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("meta", "readwrite");
          tx.objectStore("meta").put(value, key);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        })
    );
  }

  function clearDb() {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction(["records", "meta"], "readwrite");
          tx.objectStore("records").clear();
          tx.objectStore("meta").clear();
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        })
    );
  }

  /** SHA-256 without SubtleCrypto (admin UI is http://, not a secure context). */
  function sha256BytesPure(bytes) {
    const K = new Uint32Array([
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
      0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
      0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
      0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
      0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
      0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
      0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
      0xc67178f2,
    ]);
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    const bitLen = data.length * 8;
    const withLen = new Uint8Array(((data.length + 9 + 63) >> 6) << 6);
    withLen.set(data);
    withLen[data.length] = 0x80;
    const view = new DataView(withLen.buffer);
    view.setUint32(withLen.length - 4, bitLen, false);
    const h = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    const w = new Uint32Array(64);
    const rotr = (x, n) => (x >>> n) | (x << (32 - n));
    for (let off = 0; off < withLen.length; off += 64) {
      for (let i = 0; i < 16; i++) w[i] = view.getUint32(off + i * 4, false);
      for (let i = 16; i < 64; i++) {
        const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, hh] = h;
      for (let i = 0; i < 64; i++) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ (~e & g);
        const t1 = (hh + S1 + ch + K[i] + w[i]) >>> 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + maj) >>> 0;
        hh = g;
        g = f;
        f = e;
        e = (d + t1) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (t1 + t2) >>> 0;
      }
      h[0] = (h[0] + a) >>> 0;
      h[1] = (h[1] + b) >>> 0;
      h[2] = (h[2] + c) >>> 0;
      h[3] = (h[3] + d) >>> 0;
      h[4] = (h[4] + e) >>> 0;
      h[5] = (h[5] + f) >>> 0;
      h[6] = (h[6] + g) >>> 0;
      h[7] = (h[7] + hh) >>> 0;
    }
    let out = "";
    for (let i = 0; i < 8; i++) out += h[i].toString(16).padStart(8, "0");
    return out;
  }

  async function sha256Bytes(bytes) {
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    if (crypto?.subtle) {
      try {
        const buf = await crypto.subtle.digest("SHA-256", data);
        return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
      } catch (_) {
        /* fall through */
      }
    }
    return sha256BytesPure(data);
  }

  async function sha256(text) {
    return sha256Bytes(new TextEncoder().encode(text || ""));
  }

  function terminal(status) {
    return status === 200 || status === 404 || status === 403 || status === 500;
  }

  function isWanted(requestKey) {
    const { pathname } = splitRequestKey(requestKey);
    if (!pathname || !pathname.startsWith("/") || BLOCK.has(pathname)) return false;
    if (pathname.startsWith("/js/") && pathname.endsWith(".js")) return true;
    if (pathname.endsWith(".lp")) return true;
    if (pathname.startsWith("/css/") && pathname.endsWith(".css")) return true;
    if (pathname === "/robots.txt" || pathname === "/sitemap.xml" || pathname === "/crossdomain.xml")
      return true;
    if (pathname === "/favicon.ico") return true;
    if (pathname === "/clientaccesspolicy.xml" || pathname === "/.well-known/security.txt") return true;
    if (pathname.startsWith("/img/") || pathname.startsWith("/font/")) return true;
    if (pathname.startsWith("/ajax/")) return true;
    if (/\.(png|gif|jpe?g|ico|svg|woff2?|ttf|eot|bin)$/i.test(pathname)) return true;
    return false;
  }

  function classifyBody(status, body) {
    const n = (body || "").length;
    const head = (body || "").slice(0, 180).replace(/\s+/g, " ");
    if (status === 404 && n === 146 && /404/.test(body || "")) return "nginx-404-stub";
    if (status === 403) return "forbidden";
    if (status === 503) return "nginx-503-lockout";
    if (status === 500) return "http-500";
    if (/<title>\s*Login/i.test(body || "") && n < 8000) return "login-html-not-modal";
    if (status === 200 && pathLooksJs(body)) return "javascript";
    return status === 200 ? "http-200" : `http-${status}`;
  }

  function pathLooksJs(body) {
    return /^\s*(?:function|var |const |let |\/\*|!function|\(function)/.test(body || "");
  }

  function cleanPath(path) {
    if (!path) return path;
    let p = path;
    const q = p.indexOf("?");
    if (q >= 0) {
      return cleanPath(p.slice(0, q)) + p.slice(q);
    }
    while (p.includes("/modals/modals/")) p = p.replace("/modals/modals/", "/modals/");
    const base = p.replace(/^\//, "");
    if (/^[A-Za-z0-9_-]*modal[A-Za-z0-9_-]*\.lp$/i.test(base) && !p.startsWith("/modals/")) {
      return "/modals/" + base;
    }
    return p;
  }

  function splitRequestKey(key) {
    const k = cleanPath(key || "");
    const i = k.indexOf("?");
    if (i < 0) return { pathname: k, search: "", action: "" };
    const search = k.slice(i + 1);
    let action = "";
    for (const part of search.split("&")) {
      const [name, val] = part.split("=");
      if (name === "action" && val) action = decodeURIComponent(val);
    }
    return { pathname: k.slice(0, i), search, action };
  }

  function queryActionFromKey(key) {
    return splitRequestKey(key).action;
  }

  function isUnsafeActionKey(key) {
    const action = queryActionFromKey(key);
    return Boolean(action && UNSAFE_ACTIONS.has(action));
  }

  const NORM_VERSION = 2;

  /** Fingerprint ignores CSRF text. HTML also ignores digit runs (live counters, log lines). */
  function normalizeForFingerprint(text) {
    let s = String(text || "")
      .replace(/(<meta[^>]*name\s*=\s*["']CSRFtoken["'][^>]*content\s*=\s*["'])[^"']*/gi, "$1")
      .replace(/(name\s*=\s*["']CSRFtoken["'][^>]*value\s*=\s*["'])[^"']*/gi, "$1")
      .replace(/(["']CSRFtoken["']\s*[:=]\s*["'])[^"']*/gi, "$1");
    if (s.includes("<")) s = s.replace(/\d{2,}/g, "0");
    return s;
  }

  function actionClassNotes(rec) {
    const drop = new Set([
      "bare-page-not-cached",
      "control-not-cached",
      "same-as-bare-page",
      "same-as-invalid-action",
      "differs-from-bare-page",
      "differs-from-bare-and-control",
      "unnormalized-hash",
      "fingerprint-missing",
    ]);
    return (rec.outcomeNotes || []).filter((n) => !drop.has(n));
  }

  function fingerprintOf(rec) {
    return rec?.normSha256 || "";
  }

  /**
   * An action counts only when the normalized body differs from both the bare
   * page and the invalid-action control. HTTP 200 is not a classification.
   */
  function classifyAction(rec, cache) {
    const split = splitRequestKey(rec.path);
    if (!split.action) return;
    const notes = actionClassNotes(rec);
    if (!rec.normSha256 && rec.sha256) notes.push("unnormalized-hash");
    if (split.action === CONTROL_ACTION) {
      rec.outcome = "ACTION_CONTROL";
      rec.outcomeNotes = notes;
      return;
    }
    if (UNSAFE_ACTIONS.has(split.action)) {
      rec.outcome = "UNSAFE_TO_PROBE";
      rec.outcomeNotes = notes;
      return;
    }
    if (rec.status === 404) {
      rec.outcome = "NOT_FOUND";
      rec.outcomeNotes = notes;
      return;
    }
    if (rec.status === 401 || rec.status === 403 || rec.bodyClass === "login-html-not-modal") {
      rec.outcome = "AUTH_REQUIRED";
      rec.outcomeNotes = notes;
      return;
    }
    const fp = fingerprintOf(rec);
    const bare = cache.get(split.pathname);
    const control = cache.get(`${split.pathname}?action=${CONTROL_ACTION}`);
    const bareFp = fingerprintOf(bare);
    const controlFp = fingerprintOf(control);
    if (!fp) {
      notes.push("fingerprint-missing");
      rec.outcomeNotes = notes;
      return;
    }
    if (!bare || bare.status !== 200 || !bareFp) {
      notes.push("bare-page-not-cached");
      rec.outcomeNotes = notes;
      return;
    }
    const sameBare = fp === bareFp;
    const haveControl = Boolean(control && control.status === 200 && controlFp);
    const sameControl = haveControl && fp === controlFp;
    if (sameBare || sameControl) {
      rec.outcome = "IGNORED_PARAMETER";
      if (sameBare) notes.push("same-as-bare-page");
      if (sameControl) notes.push("same-as-invalid-action");
      if (!haveControl) notes.push("control-not-cached");
      rec.outcomeNotes = notes;
      return;
    }
    if (!haveControl) {
      rec.outcome = "POSSIBLE_ACTION";
      notes.push("differs-from-bare-page", "control-not-cached");
      rec.outcomeNotes = notes;
      return;
    }
    const json =
      (rec.jsonKeys && rec.jsonKeys.length > 0) ||
      /json/i.test(rec.responseHeaders?.contentType || "") ||
      rec.bodyClass === "application-json";
    notes.push("differs-from-bare-and-control");
    rec.outcome = json ? "CONFIRMED_ACTION_RESPONSE" : "POSSIBLE_ACTION";
    rec.outcomeNotes = notes;
  }

  async function ensureRecordDigests(rec) {
    if (rec.binary && rec.bytesBody) {
      const raw = rec.bytesBody instanceof Uint8Array ? rec.bytesBody : new Uint8Array(rec.bytesBody);
      if (!rec.sha256) rec.sha256 = await sha256Bytes(raw);
      if (!rec.normSha256) {
        rec.normSha256 = rec.sha256;
        rec.normVersion = NORM_VERSION;
      }
      return;
    }
    if (!rec.body) return;
    if (!rec.sha256) rec.sha256 = await sha256Bytes(new TextEncoder().encode(rec.body));
    await ensureNormSha(rec);
  }

  async function ensureNormSha(rec) {
    if (rec.normVersion === NORM_VERSION && rec.normSha256) return;
    if (!rec.body) return;
    rec.normSha256 = await sha256(normalizeForFingerprint(rec.body));
    rec.normVersion = NORM_VERSION;
  }

  async function relabelQueryVariants(pathname, cache) {
    for (const rec of cache.values()) {
      const split = splitRequestKey(rec.path);
      if (split.pathname !== pathname || !split.action || rec.status !== 200) continue;
      await ensureNormSha(rec);
      const before = `${rec.outcome}|${(rec.outcomeNotes || []).join(",")}|${rec.normSha256 || ""}`;
      classifyAction(rec, cache);
      const after = `${rec.outcome}|${(rec.outcomeNotes || []).join(",")}|${rec.normSha256 || ""}`;
      if (after !== before) await putRecord(rec);
    }
  }

  /** Modal HTML is injected into the shell; relative img/ and foo.lp from /js/ are site-root paths. */
  function resolveHrefBase(fromPath, href) {
    const h = (href || "").trim();
    if (!h || h.startsWith("/") || /^https?:/i.test(h) || h.startsWith("//")) return fromPath || "/";
    const { pathname } = splitRequestKey(fromPath || "");
    if (pathname.startsWith("/modals/") && pathname.endsWith(".lp")) {
      if (/^(img|image|font|css|js)\//i.test(h) || /\.(png|gif|jpe?g|ico|svg|woff2?|ttf|eot|css|js)(\?|#|$)/i.test(h)) {
        return "/";
      }
    }
    if (pathname.startsWith("/js/") && pathname.endsWith(".js") && /\.lp(\?|#|$)/i.test(h)) {
      return "/";
    }
    return fromPath || "/";
  }

  function canonicalizeQuery(pathname, rawSearch) {
    if (!rawSearch) return pathname;
    const q = rawSearch.startsWith("?") ? rawSearch.slice(1) : rawSearch;
    if (!q) return pathname;
    if (/^(_=\d+|\d+\.\d+\.)/.test(q) && !q.includes("&") && !q.includes("=")) return pathname;
    if (/^\d+\.\d+\./.test(q) && q.includes(".b.") && !q.includes("&")) return pathname;
    try {
      const u = new URL(`${pathname}?${q}`, BASE);
      const parts = [];
      for (const [k, v] of u.searchParams) {
        if (k === "_") continue;
        if (/^\d+\.\d+\./.test(k)) continue;
        if (QUEUE_QUERY_KEYS.has(k)) parts.push(`${k}=${encodeURIComponent(v)}`);
      }
      return parts.length ? `${pathname}?${parts.join("&")}` : pathname;
    } catch (_) {
      return pathname;
    }
  }

  function normalizePath(href, basePath) {
    if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("data:")) return null;
    try {
      const u = new URL(href, BASE + resolveHrefBase(basePath, href));
      if (u.hostname !== HOST) return null;
      return cleanPath(u.pathname || null);
    } catch (_) {
      return null;
    }
  }

  function requestKeyFromString(href, fromPath, opts) {
    if (!href || typeof href !== "string") return null;
    const h = href.trim();
    if (!h || h.startsWith("#") || h.startsWith("javascript:") || h.startsWith("data:")) return null;
    try {
      const base = resolveHrefBase(fromPath, h);
      let parseHref = h;
      if (h.startsWith("//")) parseHref = `http:${h}`;
      const u = new URL(parseHref, BASE + base);
      if (u.hostname !== HOST) return null;
      let pathname = u.pathname || "/";
      if (!pathname.startsWith("/")) pathname = `/${pathname}`;
      pathname = cleanPath(pathname);
      if (!isWanted(pathname)) return null;
      if (opts && opts.preserveQuery) {
        return canonicalizeQuery(pathname, u.search ? u.search.slice(1) : "");
      }
      return canonicalizeQuery(
        pathname,
        [...u.searchParams].length
          ? [...u.searchParams]
              .filter(([k]) => QUEUE_QUERY_KEYS.has(k))
              .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
              .join("&")
          : ""
      );
    } catch (_) {
      return null;
    }
  }

  function pushRequestKey(refs, href, fromPath, method) {
    const h = (href || "").trim();
    let key = requestKeyFromString(h, fromPath);
    const bareLp = h.split("?")[0].replace(/^\//, "");
    if (!key && bareLp.endsWith(".lp")) {
      const lp = resolveLp(bareLp, fromPath);
      if (lp) {
        const qs = h.includes("?") ? `?${h.split("?").slice(1).join("?")}` : "";
        key = requestKeyFromString(`${lp}${qs}`, "/");
      }
    }
    if (key) {
      const { pathname } = splitRequestKey(key);
      if (pathname.startsWith("/js/") && pathname.endsWith(".lp")) {
        const fixed = resolveLp(bareLp, fromPath);
        if (fixed) {
          const qs = h.includes("?") ? `?${h.split("?").slice(1).join("?")}` : "";
          key = requestKeyFromString(`${fixed}${qs}`, "/");
        }
      }
    }
    if (key) refs.push({ path: key, method, from: fromPath || "" });
  }

  const URL_HINT_KINDS = new Set(["jquery-url", "url-literal", "fileDownload-target", "form-action-attr"]);

  function refsFromApiHints(hints, fromPath) {
    const refs = [];
    for (const h of hints || []) {
      if (!URL_HINT_KINDS.has(h.kind)) continue;
      pushRequestKey(refs, h.name, fromPath, `chase-hint-${h.kind}`);
    }
    return refs;
  }

  /** LinkFinder-style extraction from JS/HTML text (quoted URLs, fetch, jQuery, XHR). */
  function extractJsUrlRefs(text, fromPath) {
    const refs = [];
    if (!text || text.length < 4) return refs;
    const push = (href, method) => pushRequestKey(refs, href, fromPath, method);

    const quotedPath =
      /["'`]((\/(?:js|modals|ajax|css|img|font)\/[^"'`\s]+)|(\/[A-Za-z0-9_.-]+\.(?:lp|js|lua|css|bin)(?:\?[^"'`\s]*)?))["'`]/g;
    let m;
    while ((m = quotedPath.exec(text))) push(m[1], "chase-js-quoted");

    for (const m of text.matchAll(/fetch\s*\(\s*["'`]([^"'`]+)["'`]/g)) push(m[1], "chase-js-fetch");
    for (const m of text.matchAll(/\$\.(?:get|post|ajax)\s*\(\s*["'`]([^"'`]+)["'`]/g)) push(m[1], "chase-js-jquery");
    for (const m of text.matchAll(/\.fileDownload\s*\(\s*["'`]([^"'`]+)["'`]/g)) push(m[1], "chase-js-fileDownload");
    for (const m of text.matchAll(/\b(?:url|target|href)\s*:\s*["'`]([^"'`]+)["'`]/g)) push(m[1], "chase-js-obj-url");
    for (const m of text.matchAll(/\.open\s*\(\s*["'][A-Za-z]+["']\s*,\s*["'`]([^"'`]+)["'`]/gi)) push(m[1], "chase-js-xhr-open");
    for (const m of text.matchAll(/(?<![A-Za-z0-9_])\/[A-Za-z0-9_.-]+\.lp\?[A-Za-z0-9_=&%.-]+/g)) push(m[0], "chase-js-lp-query");
    for (const m of text.matchAll(/\/ajax\/[A-Za-z0-9._/-]+\.lua(?:\?[A-Za-z0-9_=&%.-]+)?/g)) push(m[0], "chase-js-ajax");

    return refs;
  }

  function isTerminalCached(cache, path) {
    const rec = cache.get(path);
    if (!rec || !terminal(rec.status)) return false;
    if (rec.status !== 200) return true;
    return recordTrusted(rec);
  }

  function pruneQueue(queue, cache) {
    const seen = new Set();
    const out = [];
    for (const item of queue) {
      const path = cleanPath(item.path);
      if (!path || seen.has(path) || BLOCK.has(path)) continue;
      if (isTerminalCached(cache, path)) continue;
      seen.add(path);
      out.push({ ...item, path });
    }
    return out;
  }

  function resolveLp(name, fromPath) {
    if (!name) return null;
    if (name.startsWith("/")) return cleanPath(name);
    if (name.startsWith("modals/")) return "/" + name;
    // Homeware shell pages are at /, modal filenames are under /modals/.
    if (/^[A-Za-z0-9_-]+\.lp$/.test(name)) {
      if (/modal/i.test(name)) return "/modals/" + name;
      return "/" + name;
    }
    if (name.startsWith("js/")) return null;
    const dir = fromPath && fromPath.includes("/") ? fromPath.replace(/\/[^/]+$/, "/") : "/";
    try {
      const p = new URL(name, BASE + dir).pathname;
      if (p.startsWith("/js/") && p.endsWith(".lp")) return null;
      return p;
    } catch (_) {
      return null;
    }
  }

  /** HTTrack/Burp read links out of CSS and robots/sitemap. We already download those files. */
  function extractDeclaredLinks(text, fromPath) {
    const refs = [];
    if (!text) return refs;
    for (const m of text.matchAll(/url\(\s*(['"]?)([^'")\s]+)\1\s*\)/gi)) {
      pushRequestKey(refs, m[2], fromPath, "chase-css-url");
    }
    for (const m of text.matchAll(/@import\s+(?:url\(\s*)?(['"])([^'"]+)\1/gi)) {
      pushRequestKey(refs, m[2], fromPath, "chase-css-import");
    }
    const pathname = splitRequestKey(fromPath || "").pathname;
    if (pathname === "/robots.txt") {
      for (const m of text.matchAll(/^(?:Allow|Disallow|Sitemap)\s*:\s*(\S+)/gim)) {
        pushRequestKey(refs, m[1], fromPath, "chase-robots");
      }
    }
    if (pathname.endsWith(".xml")) {
      for (const m of text.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/gi)) {
        pushRequestKey(refs, m[1], fromPath, "chase-sitemap");
      }
    }
    return refs;
  }

  function extractRefs(text, fromPath) {
    const out = [];
    const push = (path, method) => {
      path = cleanPath(path);
      if (path && isWanted(path)) out.push({ path, method, from: fromPath || "" });
    };
    if (!text) return { refs: out, actions: [] };
    for (const p of text.match(/\/js\/[A-Za-z0-9_.-]+\.js/g) || []) push(p, "chase-regex-js");
    for (const p of text.match(/\/modals\/[A-Za-z0-9_.-]+\.lp/g) || []) push(p, "chase-regex-modal");
    for (const p of text.match(/\/ajax\/[A-Za-z0-9._/-]+\.lua/g) || []) push(p, "chase-regex-ajax");
    for (const p of text.match(/\/css\/[A-Za-z0-9_.-]+\.css/g) || []) push(p, "chase-regex-css");
    for (const p of text.match(/\/(?:img|font)\/[A-Za-z0-9_.-]+\.(?:png|gif|jpe?g|ico|svg|woff2?|ttf)/gi) || [])
      push(p, "chase-regex-asset");
    for (const p of extractPathLiterals(text)) push(p, "chase-path-literal");
    const reLp = /(?:^|["'(=\s])([A-Za-z0-9_./-]+\.lp)/g;
    let m;
    while ((m = reLp.exec(text))) {
      push(resolveLp(m[1], fromPath), "chase-regex-lp");
    }
    if (text.includes("<")) {
      const doc = new DOMParser().parseFromString(text, "text/html");
      doc
        .querySelectorAll("script[src], link[href], a[href], form[action], img[src], source[src]")
        .forEach((el) => {
          const attr = el.getAttribute("src") || el.getAttribute("href") || el.getAttribute("action");
          const key = requestKeyFromString(attr, fromPath) || normalizePath(attr, fromPath);
          push(key, "chase-html-attr");
        });
    }
    for (const r of extractJsUrlRefs(text, fromPath)) push(r.path, r.method);
    for (const r of extractDeclaredLinks(text, fromPath)) push(r.path, r.method);
    const actionHints = extractApiHints(text);
    for (const r of refsFromApiHints(actionHints, fromPath)) push(r.path, r.method);
    const actions = actionHints.map((h) => `${h.kind}:${h.name}`);
    return { refs: out, actions, actionHints };
  }

  function guessFrom(path) {
    const out = [];
    const add = (p, method) => {
      if (isWanted(p)) out.push({ path: p, method, from: path });
    };
    const base = path.split("/").pop() || "";
    if (path.startsWith("/modals/") && base.endsWith(".lp")) {
      const stem = base.replace(/\.lp$/, "");
      add(`/js/${stem}.js`, "guess-modal-to-js");
      add(`/js/${stem}-min.js`, "guess-modal-to-js");
      if (stem.endsWith("-modal")) {
        add(`/js/${stem.replace(/-modal$/, "-min")}.js`, "guess-modal-stem-min");
        add(`/js/${stem.replace(/-modal$/, "")}-min.js`, "guess-modal-stem-min");
      }
    }
    if (path.startsWith("/js/") && base.endsWith(".js")) {
      const stem = base.replace(/\.js$/, "").replace(/-min$/, "");
      add(`/modals/${stem}-modal.lp`, "guess-js-to-modal");
      add(`/modals/${stem}.lp`, "guess-js-to-modal");
    }
    return out;
  }

  function looksBinary(bytes, contentType) {
    const ct = (contentType || "").toLowerCase();
    if (/^(image|font|audio|video)\//.test(ct)) return true;
    if (/application\/(octet-stream|zip|gzip|x-tar|x-binary|vnd\.)/.test(ct)) return true;
    if (/text\/|javascript|json|xml|css|html/.test(ct)) return false;
    if (!bytes || bytes.length < 4) return false;
    const b0 = bytes[0];
    const b1 = bytes[1];
    if (b0 === 0x89 && b1 === 0x50) return true;
    if (b0 === 0x47 && b1 === 0x49) return true;
    if (b0 === 0xff && b1 === 0xd8) return true;
    if (b0 === 0x00) return true;
    if (b0 === 0x1f && b1 === 0x8b) return true;
    return false;
  }

  function gmGet(path) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: "GET",
        url: BASE + path,
        responseType: "arraybuffer",
        timeout: 15000,
        onload(res) {
          const headers = parseResponseHeaders(res.responseHeaders);
          const bytes = new Uint8Array(res.response || new ArrayBuffer(0));
          const binary = looksBinary(bytes, headers["content-type"]);
          resolve({
            path,
            status: res.status,
            bytes,
            binary,
            body: binary ? "" : new TextDecoder("utf-8", { fatal: false }).decode(bytes),
            headers,
          });
        },
        onerror() {
          reject(new Error("network error"));
        },
        ontimeout() {
          reject(new Error("timeout"));
        },
      });
    });
  }

  function seeds(includeSensitive) {
    const items = [];
    const push = (path, method) => {
      if (!includeSensitive && SENSITIVE.has(path)) return;
      if (isWanted(path)) items.push({ path, method, from: "" });
    };
    KNOWN_JS.forEach((p) => push(p, "seed-known-js"));
    KNOWN_MODALS.forEach((p) => push(p, "seed-known-modal"));
    SHELL_PAGES.forEach((p) => push(p, "seed-shell"));
    EXTRA_STATIC.forEach((p) => push(p, "seed-static"));
    if (location.pathname && isWanted(location.pathname)) {
      items.push({ path: location.pathname, method: "seed-current-page", from: "" });
    }
    const live = extractRefs(document.documentElement.outerHTML, location.pathname);
    live.refs.forEach((r) => {
      if (!includeSensitive && SENSITIVE.has(r.path)) return;
      items.push(r);
    });
    return items;
  }

  /** Abandon the old IndexedDB backlog; each Run builds its own in-memory work list. */
  async function discardLegacyQueue() {
    await setMeta("queue", []);
  }

  async function loadHarPaths() {
    const h = await getMeta("harPaths");
    return Array.isArray(h) ? h : [];
  }

  async function mergeHarPaths(items) {
    const list = Array.isArray(items) ? items : [];
    const prev = await loadHarPaths();
    const seen = new Set(prev.map((x) => cleanPath(x.path)));
    let added = 0;
    for (const item of list) {
      const path = cleanPath(item?.path);
      if (!path || seen.has(path)) continue;
      prev.push({ path, method: item.method || "import-har", from: item.from || "har-import" });
      seen.add(path);
      added += 1;
    }
    await setMeta("harPaths", prev);
    return added;
  }

  async function pruneHarPaths(cache) {
    const prev = await loadHarPaths();
    const out = prev.filter((item) => !isTerminalCached(cache, item.path));
    if (out.length !== prev.length) await setMeta("harPaths", out);
    return prev.length - out.length;
  }

  function mergeQueue(queue, items, cache) {
    const list = Array.isArray(items) ? items : items && Array.isArray(items.refs) ? items.refs : [];
    const seen = new Set(queue.map((x) => cleanPath(x.path)));
    let added = 0;
    for (const item of list) {
      const path = cleanPath(item?.path);
      if (!path || seen.has(path) || BLOCK.has(path) || isBogusModalPath(path)) continue;
      if (!isWanted(path)) continue;
      if (isUnsafeActionKey(path)) continue;
      if (cache && isTerminalCached(cache, path)) continue;
      queue.push({ path, method: item.method || "unknown", from: item.from || "" });
      seen.add(path);
      added += 1;
    }
    return added;
  }

  function isBogusModalPath(path) {
    const { pathname } = splitRequestKey(path);
    return /modal/i.test(pathname) && pathname.endsWith(".lp") && !pathname.startsWith("/modals/");
  }

  function actionProbeBases() {
    const bases = new Set();
    for (const p of GET_ACTION_PROBES) {
      const split = splitRequestKey(p.path);
      if (split.action) bases.add(split.pathname);
    }
    return bases;
  }

  /** Drop leftover matrix probes, filename guesses, and /foo-modal.lp paths that skipped /modals/. */
  function keepWorkItem(item) {
    if (!item?.path || isUnsafeActionKey(item.path) || isBogusModalPath(item.path)) return false;
    const m = item.method || "";
    if (m.startsWith("guess-")) return false;
    // Old matrix methods. Nothing in 1.7 enqueues them; this drops rows still saved in IndexedDB.
    if (m === "probe-read-action" || m === "probe-wide-action" || m === "probe-wide-session") return false;
    if (m === "probe-action-control") return actionProbeBases().has(splitRequestKey(item.path).pathname);
    return true;
  }

  function queueRank(item) {
    const m = item.method || "";
    if (m.startsWith("seed-")) return 0;
    if (m === "probe-action-control") return 1;
    if (m === "probe-get-action") return 2;
    if (m === "import-har") return 3;
    if (
      m.startsWith("probe-get") ||
      m.startsWith("probe-known") ||
      m.startsWith("probe-homeware") ||
      m.startsWith("probe-wellknown")
    )
      return 4;
    if (m.startsWith("chase-") || m === "meta-path-literal") return 5;
    if (m.startsWith("guess-")) return 9;
    return 6;
  }

  function prioritizeQueue(queue) {
    return queue
      .map((item, i) => ({ item, i }))
      .sort((a, b) => queueRank(a.item) - queueRank(b.item) || a.i - b.i)
      .map((x) => x.item);
  }

  async function refreshStat(el, opts = {}) {
    const light = opts.light === true;
    try {
      const total = await recordCount();
      const harPending = (await loadHarPaths()).length;
      if (light || total > 400) {
        const harNote = harPending ? ` HAR paths waiting for next Run: ${harPending}.` : "";
        el.textContent = `Saved on this browser: ${total} cached request(s).${harNote}`;
        return { ok: total, miss: 0, light: true };
      }
      const rows = await allRecords();
      const ok = rows.filter((r) => r.status === 200).length;
      const miss = rows.filter((r) => r.status === 404 || r.status === 403 || r.status === 500).length;
      const harNote = harPending ? ` HAR paths for next Run: ${harPending}.` : "";
      el.textContent = `Saved on this browser: ${ok} files, ${miss} misses.${harNote}`;
      return { ok, miss };
    } catch (e) {
      const msg = e && e.message ? e.message : String(e);
      el.textContent = `Could not read saved results: ${msg}`;
      throw e;
    }
  }

  async function relabelCachedQueries(cache) {
    for (const rec of cache.values()) {
      const digBefore = `${rec.sha256}|${rec.normSha256}|${rec.normVersion}`;
      await ensureRecordDigests(rec);
      if (`${rec.sha256}|${rec.normSha256}|${rec.normVersion}` !== digBefore) await putRecord(rec);
    }
    let n = 0;
    for (const rec of cache.values()) {
      if (!splitRequestKey(rec.path).action) continue;
      const before = `${rec.outcome}|${(rec.outcomeNotes || []).join(",")}|${rec.normSha256 || ""}`;
      classifyAction(rec, cache);
      const after = `${rec.outcome}|${(rec.outcomeNotes || []).join(",")}|${rec.normSha256 || ""}`;
      if (after !== before) {
        await putRecord(rec);
        n += 1;
      }
    }
    return n;
  }

  async function processQueue(logEl, statEl, opts) {
    const purged = await ensureCacheGeneration();
    if (purged > 0) {
      log(
        logEl,
        `cache: dropped ${purged} stale response(s) (pre-verbatim / redacted). Re-fetching on this run where possible.`
      );
    }
    const includeSensitive = opts.sensitive;
    const chase = opts.chase;
    const phase = opts.onPhase || (() => {});
    phase(1, "Building the list of paths");
    const cacheRows = await allRecords();
    const cache = new Map(cacheRows.map((r) => [r.path, r]));
    const relabeled = await relabelCachedQueries(cache);
    if (relabeled) {
      log(logEl, `fingerprint: ${relabeled} query response(s) compared with the bare page (same body is not a real action)`);
    }
    await discardLegacyQueue();
    let work = [];
    if (opts.seed) mergeQueue(work, seeds(includeSensitive), cache);
    const harPaths = await loadHarPaths();
    if (harPaths.length) mergeQueue(work, harPaths, cache);
    if (opts.guess) {
      for (const rec of cacheRows) {
        if (rec.status === 200) mergeQueue(work, guessFrom(rec.path), cache);
      }
    }
    if (opts.probe) {
      for (const [path, method] of PROBES) {
        mergeQueue(work, [{ path, method, from: "" }], cache);
      }
    }
    if (opts.getActions) {
      mergeQueue(work, buildKnownActionProbes(), cache);
    }
    if (opts.chase) {
      const literals = (await getMeta("pathLiterals")) || [];
      mergeQueue(
        work,
        literals.map((x) => ({ path: x.path, method: "meta-path-literal", from: x.from || "" })),
        cache
      );
    }
    work = prioritizeQueue(pruneQueue(work.filter(keepWorkItem), cache));
    const ahead = work.filter((q) => queueRank(q) < 6).length;
    phase(
      2,
      `${work.length} paths this Run (${ahead} ahead of name guesses). Bare pages and the invalid-action control go first.`
    );

    let network = 0;
    let skipped = 0;
    const session = [];
    while (work.length) {
      const item = work[0];
      if (!includeSensitive && SENSITIVE.has(item.path)) {
        work.shift();
        session.push({ ...item, status: "skipped", note: "sensitive checkbox off" });
        continue;
      }
      const cached = cache.get(item.path);
      if (isTerminalCached(cache, item.path)) {
        work.shift();
        skipped += 1;
        if (splitRequestKey(item.path).action) {
          await ensureNormSha(cached);
          classifyAction(cached, cache);
        }
        const quiet = QUIET_OUTCOMES.has(cached.outcome);
        if (cached.status === 200 && cached.body && !quiet) {
          if (!cached.binary) await mergeOffHostUrls(extractOffHostFromText(cached.body, item.path, "chase-cache"));
          if (chase) {
            const found = extractRefs(cached.body, item.path);
            const n = mergeQueue(work, found.refs, cache);
            if (n) log(logEl, `from cache ${item.path} +${n} paths`);
            if (found.actions.length || found.actionHints?.length) {
              cached.actions = [...new Set([...(cached.actions || []), ...found.actions])];
              cached.actionHints = [...(cached.actionHints || []), ...(found.actionHints || [])];
              await putRecord(cached);
            }
          }
          if (opts.guess) mergeQueue(work, guessFrom(item.path), cache);
        }
        continue;
      }
      if (network) await sleep(DELAY_MS);
      phase(2, `Request ${network + 1}, ${work.length} left: ${item.path}`);
      log(logEl, `GET ${item.path} (${item.method})`);
      let res;
      try {
        res = await gmGet(item.path);
      } catch (e) {
        log(logEl, `stop: ${e.message}`);
        session.push({ ...item, status: "error", note: String(e.message), at: new Date().toISOString() });
        break;
      }
      network += 1;
      if (res.status === 503) {
        log(logEl, "503 — stopped. Wait or reboot, then Run again (work list is rebuilt each time).");
        session.push({
          ...item,
          status: 503,
          bytes: (res.bytes || new Uint8Array()).length,
          note: "not cached; lockout",
          at: new Date().toISOString(),
        });
        break;
      }
      const raw = res.body || "";
      const byteLength = (res.bytes || new Uint8Array()).length;
      const sum = summarizeOutcome(res.status, raw);
      const reqAction = queryActionFromKey(item.path);
      const digest = await sha256Bytes(res.bytes || new Uint8Array());
      const rec = {
        path: item.path,
        status: res.status,
        method: item.method,
        from: item.from || "",
        requestAction: reqAction || "",
        outcome: sum.outcome,
        jsonKeys: sum.jsonKeys,
        jsonKeyPaths: sum.jsonKeyPaths,
        outcomeNotes: sum.notes,
        responseHeaders: pickHeaders(res.headers || {}),
        bytes: byteLength,
        sha256: digest,
        normSha256: res.binary ? digest : await sha256(normalizeForFingerprint(raw)),
        bodyClass: res.binary ? "binary" : classifyBody(res.status, raw),
        binary: Boolean(res.binary),
        at: new Date().toISOString(),
        body: res.status === 200 && !res.binary ? raw : "",
        bytesBody: res.status === 200 && res.binary ? res.bytes : undefined,
        missExcerpt: res.status === 200 ? "" : (res.binary ? `binary ${byteLength} bytes` : raw.slice(0, 240)),
        actions: [],
        actionHints: [],
      };
      classifyAction(rec, cache);
      await putRecord(rec);
      cache.set(rec.path, rec);
      if (!splitRequestKey(item.path).search) await relabelQueryVariants(splitRequestKey(item.path).pathname, cache);
      if (splitRequestKey(item.path).action === CONTROL_ACTION) await relabelQueryVariants(splitRequestKey(item.path).pathname, cache);
      const quiet = QUIET_OUTCOMES.has(rec.outcome);
      if (res.status === 200 && !quiet) {
        try {
          const { pathname } = splitRequestKey(item.path);
          const forms = isHtmlCapturePath(item.path) ? extractFormsFromHtml(raw, pathname) : [];
          if (forms.length) await mergeForms(forms);
          await mergePathLiterals(extractPathLiterals(raw), item.path);
          if (!res.binary) await mergeOffHostUrls(extractOffHostFromText(raw, item.path, "chase"));
          if (chase) {
            const found = extractRefs(raw, item.path);
            rec.actions = found.actions || [];
            rec.actionHints = found.actionHints || [];
            const n = mergeQueue(work, found.refs, cache);
            if (n) log(logEl, `  linked paths +${n}`);
          }
          if (opts.guess) {
            const n = mergeQueue(work, guessFrom(item.path), cache);
            if (n) log(logEl, `  similar names +${n}`);
          }
          if (rec.actions?.length || rec.actionHints?.length) await putRecord(rec);
        } catch (e) {
          log(logEl, `  saved ${item.path}, skipped link scan: ${e.message}`);
        }
      }
      cache.set(rec.path, rec);
      work.shift();
      session.push(rec);
      const act = reqAction ? ` action=${reqAction}` : "";
      const keys = rec.jsonKeys?.length ? ` keys=${rec.jsonKeys.join(",")}` : "";
      const deep = rec.jsonKeyPaths?.length > (rec.jsonKeys?.length || 0)
        ? ` deep=${rec.jsonKeyPaths.slice(0, 12).join(",")}${rec.jsonKeyPaths.length > 12 ? "…" : ""}`
        : "";
      const ct = rec.responseHeaders?.contentType ? ` ct=${rec.responseHeaders.contentType.split(";")[0]}` : "";
      const notes = rec.outcomeNotes?.length ? ` (${rec.outcomeNotes.join("; ")})` : "";
      log(logEl, `  → ${res.status} ${rec.outcome}${act}${keys}${deep}${ct}${notes} ${rec.bytes}B`);
      if (network % 5 === 0) await refreshStat(statEl);
    }
    const harPruned = await pruneHarPaths(cache);
    if (harPruned) log(logEl, `HAR: removed ${harPruned} path(s) already in cache`);
    await relabelCachedQueries(cache);
    await setMeta("lastSession", session);
    await refreshStat(statEl);
    const stoppedEarly = work.length > 0;
    phase(
      2,
      stoppedEarly
        ? `Stopped early (${work.length} paths not reached this Run). ${network} new requests, ${skipped} cache skips.`
        : `Fetch finished. ${network} new requests, ${skipped} already saved.`
    );
    const distinct = new Set(session.filter((r) => r.status === 200).map((r) => r.normSha256 || r.sha256)).size;
    const ignored = session.filter((r) => r.outcome === "IGNORED_PARAMETER").length;
    const confirmed = session.filter((r) => r.outcome === "CONFIRMED_ACTION_RESPONSE").length;
    log(
      logEl,
      `done. fetched ${network}, distinct bodies ${distinct}, ignored-action ${ignored}, confirmed-action ${confirmed}, cache skips ${skipped}${stoppedEarly ? `, not reached ${work.length}` : ""}`
    );
    return { network, skipped, stoppedEarly };
  }

  function mdEscape(s) {
    return String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
  }

  function buildReports(rows, extras = {}) {
    const traffic = extras.traffic || [];
    const forms = extras.forms || [];
    const pathLiterals = extras.pathLiterals || [];
    const offHostUrls = extras.offHostUrls || [];
    const hits = rows.filter((r) => r.status === 200);
    const misses = rows.filter((r) => r.status !== 200);
    const byMethod = {};
    for (const r of rows) {
      const k = `${r.method || "?"} / ${r.status}`;
      byMethod[k] = (byMethod[k] || 0) + 1;
    }
    const lines = [];
    lines.push("# F1 grab misses");
    lines.push("");
    lines.push(`Generated: ${new Date().toISOString()}`);
    lines.push(`Host: ${BASE}`);
    lines.push(`Misses: ${misses.length}. Hits kept in the zip under files/.`);
    lines.push("");
    lines.push("A miss is a finished GET that was not HTTP 200 (mostly 404, sometimes 403).");
    lines.push("503 is not stored here — that run stops; Run again rebuilds the work list from seeds, HAR, and chase.");
    lines.push("Method is how the path was chosen, not the HTTP verb (every probe is GET).");
    lines.push("");
    lines.push(
      "| Path | Full URL | HTTP | Request action | Outcome | Method | From | When | Bytes | SHA-256 |"
    );
    lines.push("| --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- |");
    for (const r of misses.sort((a, b) => a.path.localeCompare(b.path))) {
      const fullUrl = BASE + r.path;
      lines.push(
        `| ${mdEscape(r.path)} | ${mdEscape(fullUrl)} | ${r.status} | ${mdEscape(r.requestAction || queryActionFromKey(r.path))} | ${mdEscape(r.outcome || r.bodyClass)} | ${mdEscape(r.method)} | ${mdEscape(r.from)} | ${mdEscape(r.at)} | ${r.bytes ?? ""} | ${mdEscape((r.sha256 || "").slice(0, 16))} |`
      );
    }
    lines.push("");
    lines.push("## Notes per miss");
    lines.push("");
    for (const r of misses.sort((a, b) => a.path.localeCompare(b.path))) {
      lines.push(`### ${r.path}`);
      lines.push("");
      lines.push(`- Full URL: ${BASE}${r.path}`);
      lines.push(`- HTTP ${r.status} via GET (no query string)`);
      lines.push(`- Method: \`${r.method || "unknown"}\``);
      lines.push(`- Discovered from: ${r.from || "(seed / probe list)"}`);
      lines.push(`- When: ${r.at || ""}`);
      lines.push(`- Bytes: ${r.bytes ?? ""}`);
      lines.push(`- Body class: ${r.bodyClass || ""}`);
      lines.push(`- SHA-256: ${r.sha256 || ""}`);
      if (r.missExcerpt) {
        lines.push("- Excerpt:");
        lines.push("");
        lines.push("```");
        lines.push(r.missExcerpt.replace(/```/g, ""));
        lines.push("```");
      }
      lines.push("");
    }

    const index = [];
    index.push("# F1 grab index");
    index.push("");
    index.push(`Generated: ${new Date().toISOString()}`);
    index.push(`Hits (200): ${hits.length}`);
    index.push(`Misses: ${misses.length}`);
    index.push("");
    index.push("## Counts by method and status");
    index.push("");
    for (const k of Object.keys(byMethod).sort()) index.push(`- ${k}: ${byMethod[k]}`);
    index.push("");
    index.push("## Hits");
    index.push("");
    index.push("| Path | Request action | Outcome | JSON keys | Notes | Bytes | Method | From |");
    index.push("| --- | --- | --- | --- | --- | ---: | --- | --- |");
    for (const r of hits.sort((a, b) => a.path.localeCompare(b.path))) {
      index.push(
        `| ${mdEscape(r.path)} | ${mdEscape(r.requestAction || queryActionFromKey(r.path))} | ${mdEscape(r.outcome || r.bodyClass)} | ${mdEscape((r.jsonKeys || []).join(", "))} | ${mdEscape((r.outcomeNotes || []).join("; "))} | ${r.bytes} | ${mdEscape(r.method)} | ${mdEscape(r.from)} |`
      );
    }
    index.push("");

    const actionsMd = [];
    actionsMd.push("# Actions and form fields (from source only)");
    actionsMd.push("");
    actionsMd.push("Declared in HTML/JS bodies already fetched. Not verified on the wire unless listed in OUTCOMES.md.");
    actionsMd.push("");
    actionsMd.push("| Seen in file | Action / field | Kind |");
    actionsMd.push("| --- | --- | --- |");
    for (const r of hits.sort((a, b) => a.path.localeCompare(b.path))) {
      for (const h of r.actionHints || []) {
        actionsMd.push(`| ${mdEscape(r.path)} | ${mdEscape(h.name)} | ${mdEscape(h.kind)} |`);
      }
    }
    actionsMd.push("");

    const outcomes = [];
    outcomes.push("# GET outcomes (this grab session cache)");
    outcomes.push("");
    outcomes.push("HTTP verb is always GET. POST `action=` values appear only under ACTIONS.md unless you enable GET ?action= probes.");
    outcomes.push("");
    outcomes.push(
      "| Full URL | HTTP | Request action | Outcome | Content-Type | JSON keys | JSON paths | Notes | Source method |"
    );
    outcomes.push("| --- | ---: | --- | --- | --- | --- | --- | --- | --- |");
    for (const r of rows.sort((a, b) => a.path.localeCompare(b.path))) {
      outcomes.push(
        `| ${mdEscape(BASE + r.path)} | ${r.status} | ${mdEscape(r.requestAction || queryActionFromKey(r.path))} | ${mdEscape(r.outcome || r.bodyClass || "")} | ${mdEscape(r.responseHeaders?.contentType || "")} | ${mdEscape((r.jsonKeys || []).join(", "))} | ${mdEscape((r.jsonKeyPaths || []).join(", "))} | ${mdEscape((r.outcomeNotes || []).join("; "))} | ${mdEscape(r.method)} |`
      );
    }
    outcomes.push("");

    const leads = [];
    leads.push("# Legacy action strings (deprecated — use ACTIONS.md)");
    leads.push("");
    for (const r of hits) {
      if (!r.actions?.length) continue;
      leads.push(`## ${r.path}`);
      for (const a of r.actions) leads.push(`- \`${a}\``);
      leads.push("");
    }

    const formsMd = [];
    formsMd.push("# Forms (from fetched HTML/LP)");
    formsMd.push("");
    formsMd.push(`Entries: ${forms.length}. Field values are not stored.`);
    formsMd.push("");
    for (const f of forms) {
      formsMd.push(`## ${f.source} — \`${f.method}\` → ${f.action || "(same page)"}`);
      formsMd.push("");
      formsMd.push(`- form id: \`${f.id}\``);
      for (const field of f.fields || []) {
        formsMd.push(`- \`${field.name}\` (${field.type}${field.id ? `, id=${field.id}` : ""})`);
      }
      formsMd.push("");
    }

    const pathsMd = [];
    pathsMd.push("# Path literals (from source + chase)");
    pathsMd.push("");
    pathsMd.push("| Path | Seen in |");
    pathsMd.push("| --- | --- |");
    for (const row of pathLiterals.sort((a, b) => a.path.localeCompare(b.path))) {
      pathsMd.push(`| ${mdEscape(row.path)} | ${mdEscape(row.from)} |`);
    }
    pathsMd.push("");

    const trafficMd = [];
    trafficMd.push("# Live traffic tap (POST/XHR while UI is open)");
    trafficMd.push("");
    trafficMd.push(`Events: ${traffic.length}. Request bodies are verbatim (may contain CSRF tokens); same-host URLs only in JSONL.`);
    trafficMd.push("");
    trafficMd.push("| When | Via | Method | URL | Body (truncated) |");
    trafficMd.push("| --- | --- | --- | --- | --- |");
    for (const t of traffic.slice(-500)) {
      const body = (t.body || "").slice(0, 120);
      trafficMd.push(
        `| ${mdEscape(t.at)} | ${mdEscape(t.via)} | ${mdEscape(t.method)} | ${mdEscape(t.url)} | ${mdEscape(body)} |`
      );
    }
    trafficMd.push("");

    const trafficJsonl = traffic.map((t) => JSON.stringify(t)).join("\n");

    const externalMd = [];
    externalMd.push("# Off-host and data: URLs (recorded, not fetched)");
    externalMd.push("");
    externalMd.push(
      "These strings appeared in saved pages, CSS, JS, HAR import, or the live traffic tap. The grabber only GETs `192.168.2.1`. Follow up manually (ACS, CDN, docs)."
    );
    externalMd.push("");
    externalMd.push(`Entries: ${offHostUrls.length}`);
    externalMd.push("");
    externalMd.push("| Kind | Host / MIME | URL or preview | Via | Seen in |");
    externalMd.push("| --- | --- | --- | --- | --- |");
    for (const row of offHostUrls.sort((a, b) => (a.host || a.mime || "").localeCompare(b.host || b.mime || ""))) {
      const label = row.kind === "data" ? mdEscape(row.mime || "data") : mdEscape(row.host || "");
      const target = mdEscape(row.url || row.preview || "");
      externalMd.push(
        `| ${mdEscape(row.kind)} | ${label} | ${target} | ${mdEscape(row.via || "")} | ${mdEscape(row.from || "")} |`
      );
    }
    externalMd.push("");

    const offHostJsonl = offHostUrls.map((r) => JSON.stringify(r)).join("\n");

    return {
      misses: lines.join("\n"),
      index: index.join("\n"),
      leads: leads.join("\n"),
      actions: actionsMd.join("\n"),
      outcomes: outcomes.join("\n"),
      forms: formsMd.join("\n"),
      pathLiterals: pathsMd.join("\n"),
      externalUrls: externalMd.join("\n"),
      offHostJsonl,
      trafficMd: trafficMd.join("\n"),
      trafficJsonl,
    };
  }

  function crc32(bytes) {
    let c = ~0;
    for (let i = 0; i < bytes.length; i++) {
      c ^= bytes[i];
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    return ~c >>> 0;
  }

  function u16(n) {
    return [n & 255, (n >>> 8) & 255];
  }
  function u32(n) {
    return [n & 255, (n >>> 8) & 255, (n >>> 16) & 255, (n >>> 24) & 255];
  }

  function zipStore(files) {
    const enc = new TextEncoder();
    const parts = [];
    const central = [];
    let offset = 0;
    const now = new Date();
    const time = ((now.getHours() & 31) << 11) | ((now.getMinutes() & 63) << 5) | ((now.getSeconds() / 2) & 31);
    const date = (((now.getFullYear() - 1980) & 127) << 9) | (((now.getMonth() + 1) & 15) << 5) | (now.getDate() & 31);
    for (const f of files) {
      const name = enc.encode(f.name);
      const data = f.data;
      const crc = crc32(data);
      const local = [
        ...u32(0x04034b50),
        ...u16(20),
        ...u16(0),
        ...u16(0),
        ...u16(time),
        ...u16(date),
        ...u32(crc),
        ...u32(data.length),
        ...u32(data.length),
        ...u16(name.length),
        ...u16(0),
      ];
      parts.push(new Uint8Array(local), name, data);
      const cen = [
        ...u32(0x02014b50),
        ...u16(20),
        ...u16(20),
        ...u16(0),
        ...u16(0),
        ...u16(time),
        ...u16(date),
        ...u32(crc),
        ...u32(data.length),
        ...u32(data.length),
        ...u16(name.length),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u32(0),
        ...u32(offset),
      ];
      central.push(new Uint8Array(cen), name);
      offset += local.length + name.length + data.length;
    }
    let centralSize = 0;
    for (const c of central) centralSize += c.length;
    const end = new Uint8Array([
      ...u32(0x06054b50),
      ...u16(0),
      ...u16(0),
      ...u16(files.length),
      ...u16(files.length),
      ...u32(centralSize),
      ...u32(offset),
      ...u16(0),
    ]);
    const blobParts = [...parts, ...central, end];
    return new Blob(blobParts, { type: "application/zip" });
  }

  function fileNameFor(requestKey) {
    const { pathname } = splitRequestKey(requestKey);
    const clean = requestKey.replace(/^\//, "").replace(/\//g, "__").replace(/[?&=]/g, "_");
    if (pathname.endsWith(".lp")) return `files/${clean}.html`;
    return `files/${clean}`;
  }

  async function importHarPaths(file, logEl, onProgress) {
    const report = (msg) => {
      log(logEl, msg);
      if (onProgress) onProgress(msg);
    };
    report(`HAR: reading ${file.name} (${(file.size / 1048576).toFixed(1)} MiB)…`);
    const text = await file.text();
    report(`HAR: read ${(text.length / 1048576).toFixed(1)} MiB — scanning URLs…`);
    await tick();
    const { items, scanned, harOffHost } = await collectHarUrls(text, report);
    if (harOffHost?.length) await mergeOffHostUrls(harOffHost);
    report(`HAR: ${scanned} url fields → ${items.length} on ${HOST}`);
    const added = await mergeHarPaths(items);
    const summary = `HAR done — ${file.name}: ${scanned} url fields → ${items.length} on-host URL(s), ${added} new for next Run`;
    report(summary);
    return { added, error: "", entries: scanned, unique: items.length, name: file.name };
  }

  async function downloadPackage(logEl) {
    const purged = await ensureCacheGeneration();
    if (purged > 0) {
      log(logEl, `cache: dropped ${purged} stale response(s) — not included in this zip. Run to re-fetch.`);
    }
    const rows = await allRecords();
    const cache = new Map(rows.map((r) => [r.path, r]));
    const relabeled = await relabelCachedQueries(cache);
    if (relabeled) log(logEl, `fingerprint: relabeled ${relabeled} action response(s) before zip`);
    const traffic = await loadTraffic();
    const forms = (await getMeta("forms")) || [];
    const pathLiterals = (await getMeta("pathLiterals")) || [];
    const offHostUrls = (await getMeta("offHostUrls")) || [];
    const reports = buildReports(rows, { traffic, forms, pathLiterals, offHostUrls });
    const enc = new TextEncoder();
    const files = [
      { name: "MISSES.md", data: enc.encode(reports.misses) },
      { name: "INDEX.md", data: enc.encode(reports.index) },
      { name: "ACTIONS.md", data: enc.encode(reports.actions) },
      { name: "OUTCOMES.md", data: enc.encode(reports.outcomes) },
      { name: "FORMS.md", data: enc.encode(reports.forms) },
      { name: "PATH-LITERALS.md", data: enc.encode(reports.pathLiterals) },
      { name: "EXTERNAL-URLS.md", data: enc.encode(reports.externalUrls) },
      { name: "EXTERNAL-URLS.jsonl", data: enc.encode(reports.offHostJsonl || "") },
      { name: "TRAFFIC.md", data: enc.encode(reports.trafficMd) },
      { name: "TRAFFIC.jsonl", data: enc.encode(reports.trafficJsonl || "") },
      { name: "LEADS.md", data: enc.encode(reports.leads) },
    ];
    let zipSkipped = 0;
    for (const r of rows) {
      if (r.status !== 200) continue;
      if (!recordTrusted(r)) {
        zipSkipped += 1;
        continue;
      }
      if (r.binary && r.bytesBody) {
        const rawBytes = r.bytesBody instanceof Uint8Array ? r.bytesBody : new Uint8Array(r.bytesBody);
        files.push({ name: fileNameFor(r.path), data: rawBytes });
        continue;
      }
      if (typeof r.body !== "string") continue;
      files.push({ name: fileNameFor(r.path), data: enc.encode(r.body) });
    }
    const blob = zipStore(files);
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    GM_download({
      url,
      name: `f1-grab-${stamp}.zip`,
      onload: () => URL.revokeObjectURL(url),
      onerror: () => URL.revokeObjectURL(url),
    });
    const zipFiles = rows.filter((r) => r.status === 200 && r.body && recordTrusted(r)).length;
    log(
      logEl,
      `zip: ${zipFiles} file(s) + reports (traffic ${traffic.length} events${zipSkipped ? `; skipped ${zipSkipped} stale` : ""})`
    );
  }

  function buildPanel() {
    installTrafficTap();
    const root = document.createElement("div");
    root.id = "genesis-f1-grabber";
    root.innerHTML = `
      <h3>F1 grabber 1.8.1</h3>
      <section class="step" id="gf1-step1">
        <h4>1. Choose what to look for</h4>
        <label><input type="checkbox" id="gf1-known" checked /><span>Known pages and scripts</span></label>
        <label><input type="checkbox" id="gf1-follow" checked /><span>Chase links in files (regex + JS fetch/jQuery/XHR strings, form actions)</span></label>
        <label><input type="checkbox" id="gf1-guess" /><span>Similar names (modal.lp → matching .js, and the reverse). Off: these are mostly 404s.</span></label>
        <label><input type="checkbox" id="gf1-probe" checked /><span>A short extra list (robots.txt, overview.lp, the wireless ajax script)</span></label>
        <label><input type="checkbox" id="gf1-get-actions" checked /><span>Known read-only actions only (scheduleReboot, smartwifi, getbanksize, upgradefwstatus, session poll), each compared with the bare page and one invalid action.</span></label>
        <label><input type="checkbox" id="gf1-sensitive" /><span>Wi‑Fi QR page (can contain the Wi‑Fi key)</span></label>
        <button type="button" class="gf1-quiet" id="gf1-har">Import browser HAR (paths for next Run)</button>
        <input type="file" id="gf1-har-file" accept=".har,application/json" hidden />
        <p class="plan" id="gf1-har-status">No HAR imported this session.</p>
        <p class="plan" id="gf1-plan"></p>
      </section>
      <section class="step" id="gf1-step2">
        <h4>2. Fetch</h4>
        <button type="button" class="gf1-primary" id="gf1-run">Run</button>
        <p class="now" id="gf1-now">Nothing running. Run continues after a refresh and skips paths already saved.</p>
        <p class="stat" id="gf1-stat">Reading saved results…</p>
      </section>
      <section class="step" id="gf1-step3">
        <h4>3. Save the package</h4>
        <button type="button" id="gf1-zip">Download one zip</button>
        <p class="plan">Zip: verbatim files/ (may include CSRF tokens), reports, TRAFFIC (live XHR). Do not commit zips. Run also downloads when it finishes.</p>
        <button type="button" class="gf1-quiet" id="gf1-clear">Delete saved results</button>
      </section>
      <div class="log" id="gf1-log"></div>
    `;
    document.body.appendChild(root);
    const logEl = root.querySelector("#gf1-log");
    const statEl = root.querySelector("#gf1-stat");
    const nowEl = root.querySelector("#gf1-now");
    const planEl = root.querySelector("#gf1-plan");
    const harStatusEl = root.querySelector("#gf1-har-status");
    const steps = [...root.querySelectorAll(".step")];

    window.addEventListener("gf1-db-blocked", (ev) => {
      statEl.textContent = ev.detail || "IndexedDB blocked.";
      log(logEl, ev.detail || "IndexedDB blocked.");
    });

    function checked(id) {
      return root.querySelector(id).checked;
    }

    function describePlan() {
      const parts = [];
      if (checked("#gf1-known")) parts.push("known files");
      if (checked("#gf1-follow")) parts.push("links inside them");
      if (checked("#gf1-guess")) parts.push("similar names");
      if (checked("#gf1-probe")) parts.push("the extra list");
      if (checked("#gf1-get-actions")) parts.push("read-only action checks");
      if (checked("#gf1-sensitive")) parts.push("the Wi‑Fi QR page");
      planEl.textContent = parts.length
        ? `Run will look for ${parts.join(", ")}. Requests are 1.5s apart and stop if the gateway returns 503.`
        : "Tick at least one source above.";
    }

    function markStep(n) {
      steps.forEach((el, i) => el.classList.toggle("on", i + 1 === n));
    }

    describePlan();
    root.querySelectorAll("input[type=checkbox]").forEach((el) => el.addEventListener("change", describePlan));

    (async () => {
      await discardLegacyQueue();
      log(logEl, "Storage: no saved queue — each Run builds a fresh work list.");
      try {
        await refreshStat(statEl, { light: true });
      } catch (e) {
        log(logEl, `stat: ${e.message || e}`);
      }
      try {
        const purged = await ensureCacheGeneration();
        if (purged > 0) {
          log(
            logEl,
            `cache: cleared ${purged} old response(s) from IndexedDB (redacted or wrong format). Run to download fresh bytes.`
          );
          nowEl.textContent = "Stale cache cleared. Run (step 2) before zipping if you need full files/.";
        }
        await refreshStat(statEl);
      } catch (e) {
        log(logEl, `cache: ${e.message || e}`);
        if (statEl.textContent.startsWith("Loading")) {
          statEl.textContent = `Cache check failed: ${e.message || e}`;
        }
      }
    })();

    root.querySelector("#gf1-run").onclick = async () => {
      if (busy) return;
      if (
        !checked("#gf1-known") &&
        !checked("#gf1-follow") &&
        !checked("#gf1-guess") &&
        !checked("#gf1-probe") &&
        !checked("#gf1-get-actions")
      ) {
        nowEl.textContent = "Tick at least one source in step 1.";
        return;
      }
      busy = true;
      root.querySelectorAll("button, input").forEach((b) => (b.disabled = true));
      markStep(2);
      try {
        await processQueue(logEl, statEl, {
          sensitive: checked("#gf1-sensitive"),
          seed: checked("#gf1-known"),
          chase: checked("#gf1-follow"),
          guess: checked("#gf1-guess"),
          probe: checked("#gf1-probe"),
          getActions: checked("#gf1-get-actions"),
          onPhase: (n, text) => {
            markStep(n);
            nowEl.textContent = text;
          },
        });
        markStep(3);
        nowEl.textContent = "Fetching stopped. Saving the zip.";
        await downloadPackage(logEl);
        nowEl.textContent = "Zip downloaded.";
      } catch (e) {
        nowEl.textContent = String(e && e.message ? e.message : e);
        log(logEl, nowEl.textContent);
      } finally {
        busy = false;
        root.querySelectorAll("button, input").forEach((b) => (b.disabled = false));
        refreshStat(statEl).catch(() => {});
      }
    };

    root.querySelector("#gf1-zip").onclick = async () => {
      markStep(3);
      try {
        await downloadPackage(logEl);
        nowEl.textContent = "Zip downloaded from what is already saved. Nothing new was fetched.";
      } catch (e) {
        log(logEl, String(e));
      }
    };

    root.querySelector("#gf1-clear").onclick = async () => {
      if (busy) return;
      await clearDb();
      nowEl.textContent = "Saved results deleted. The next Run starts over.";
      await refreshStat(statEl);
    };

    const harInput = root.querySelector("#gf1-har-file");
    const harBtn = root.querySelector("#gf1-har");
    harBtn.onclick = () => harInput.click();
    harInput.onchange = async () => {
      const file = harInput.files?.[0];
      harInput.value = "";
      if (!file) return;
      harBtn.disabled = true;
      const setProgress = (msg) => {
        harStatusEl.textContent = msg;
        nowEl.textContent = msg;
      };
      setProgress(`HAR: starting ${file.name}…`);
      try {
        const result = await importHarPaths(file, logEl, setProgress);
        if (result.error) {
          setProgress(result.error);
          return;
        }
        const done = `HAR done — ${result.unique} URL(s) on ${HOST}, ${result.added} saved for next Run. Click Run.`;
        setProgress(done);
        harStatusEl.textContent = done;
        await refreshStat(statEl, { light: true });
      } catch (e) {
        const msg = e && e.message ? e.message : String(e);
        setProgress(`HAR failed: ${msg}`);
        log(logEl, msg);
      } finally {
        harBtn.disabled = false;
      }
    };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", buildPanel);
  else buildPanel();
})();
