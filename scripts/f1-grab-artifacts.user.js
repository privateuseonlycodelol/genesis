// ==UserScript==
// @name         Genesis F1 artifact grabber
// @namespace    https://github.com/privateuseonlycodelol/genesis
// @version      1.3.0
// @description  Cache F1 UI fetches, chase and guess paths, save one zip with a 404 markdown log.
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
  const DB_NAME = "genesis-f1-grab";
  const MAX_NEW_GETS = 80;

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
  ];

  const SHELL_PAGES = ["/gateway.lp", "/login.lp", "/password.lp", "/home.lp"];
  const EXTRA_STATIC = ["/css/gw.css", "/css/responsive.css"];
  const SENSITIVE = new Set(["/modals/wireless-qrcode-modal.lp"]);
  const BLOCK = new Set(["/authenticate"]);

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
  ];

  let busy = false;
  let dbPromise = null;

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

  function redact(text) {
    if (typeof text !== "string") return text;
    return text
      .replace(/(<meta[^>]*name\s*=\s*["']CSRFtoken["'][^>]*content\s*=\s*["'])[^"']+(["'])/gi, "$1REDACTED$2")
      .replace(/(CSRFtoken["']?\s*[:=]\s*["']?)[^"'&\s]+/gi, "$1REDACTED");
  }

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains("records")) db.createObjectStore("records", { keyPath: "path" });
        if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta");
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  function putRecord(rec) {
    return openDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("records", "readwrite");
          tx.objectStore("records").put(rec);
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

  async function sha256(text) {
    if (!crypto?.subtle) return "";
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text || ""));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  function terminal(status) {
    return status === 200 || status === 404 || status === 403;
  }

  function isWanted(path) {
    if (!path || !path.startsWith("/") || BLOCK.has(path)) return false;
    if (path.startsWith("/js/") && path.endsWith(".js")) return true;
    if (path.endsWith(".lp")) return true;
    if (path.startsWith("/css/") && path.endsWith(".css")) return true;
    if (path.startsWith("/ajax/") && path.endsWith(".lua")) return true;
    if (path === "/robots.txt" || path === "/sitemap.xml" || path === "/crossdomain.xml") return true;
    if (path === "/clientaccesspolicy.xml" || path === "/.well-known/security.txt") return true;
    return false;
  }

  function classifyBody(status, body) {
    const n = (body || "").length;
    const head = (body || "").slice(0, 180).replace(/\s+/g, " ");
    if (status === 404 && n === 146 && /404/.test(body || "")) return "nginx-404-stub";
    if (status === 403) return "forbidden";
    if (status === 503) return "nginx-503-lockout";
    if (/<title>\s*Login/i.test(body || "") && n < 8000) return "login-html-not-modal";
    if (status === 200 && pathLooksJs(body)) return "javascript";
    return status === 200 ? "http-200" : `http-${status}`;
  }

  function pathLooksJs(body) {
    return /^\s*(?:function|var |const |let |\/\*|!function|\(function)/.test(body || "");
  }

  function normalizePath(href, basePath) {
    if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("data:")) return null;
    try {
      const u = new URL(href, BASE + (basePath || "/"));
      if (u.hostname !== HOST) return null;
      return u.pathname || null;
    } catch (_) {
      return null;
    }
  }

  function resolveLp(name, fromPath) {
    if (!name) return null;
    if (name.startsWith("/")) return name;
    if (name.startsWith("modals/")) return "/" + name;
    const dir = fromPath && fromPath.includes("/") ? fromPath.replace(/\/[^/]+$/, "/") : "/";
    try {
      return new URL(name, BASE + dir).pathname;
    } catch (_) {
      return null;
    }
  }

  function extractRefs(text, fromPath) {
    const out = [];
    const push = (path, method) => {
      if (path && isWanted(path)) out.push({ path, method, from: fromPath || "" });
    };
    if (!text) return { refs: out, actions: [] };
    for (const p of text.match(/\/js\/[A-Za-z0-9_.-]+\.js/g) || []) push(p, "chase-regex-js");
    for (const p of text.match(/\/modals\/[A-Za-z0-9_.-]+\.lp/g) || []) push(p, "chase-regex-modal");
    for (const p of text.match(/\/ajax\/[A-Za-z0-9._/-]+\.lua/g) || []) push(p, "chase-regex-ajax");
    for (const p of text.match(/\/css\/[A-Za-z0-9_.-]+\.css/g) || []) push(p, "chase-regex-css");
    const reLp = /(?:^|["'(=\s])([A-Za-z0-9_./-]+\.lp)/g;
    let m;
    while ((m = reLp.exec(text))) {
      push(resolveLp(m[1], fromPath), "chase-regex-lp");
    }
    if (text.includes("<")) {
      const doc = new DOMParser().parseFromString(text, "text/html");
      doc.querySelectorAll("script[src], link[href], a[href], form[action]").forEach((el) => {
        const attr = el.getAttribute("src") || el.getAttribute("href") || el.getAttribute("action");
        push(normalizePath(attr, fromPath), "chase-html-attr");
      });
    }
    const actions = new Set();
    for (const a of text.match(/action[=:]["'\s]*[A-Za-z0-9_-]+/g) || []) actions.add(a.slice(0, 80));
    return { refs: out, actions: [...actions] };
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
      if (stem.includes("-modal-")) {
        add(`/js/${stem}.js`, "guess-modal-to-js");
      }
    }
    if (path.startsWith("/js/") && base.endsWith(".js")) {
      const stem = base.replace(/\.js$/, "").replace(/-min$/, "");
      add(`/modals/${stem}-modal.lp`, "guess-js-to-modal");
      add(`/modals/${stem}.lp`, "guess-js-to-modal");
    }
    return out;
  }

  function gmGet(path) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: "GET",
        url: BASE + path,
        responseType: "text",
        timeout: 15000,
        onload(res) {
          resolve({
            path,
            status: res.status,
            body: typeof res.responseText === "string" ? res.responseText : "",
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

  async function loadQueue() {
    const q = await getMeta("queue");
    return Array.isArray(q) ? q : [];
  }

  async function saveQueue(q) {
    await setMeta("queue", q);
  }

  function mergeQueue(queue, items) {
    const list = Array.isArray(items) ? items : items && Array.isArray(items.refs) ? items.refs : [];
    const seen = new Set(queue.map((x) => x.path));
    let added = 0;
    for (const item of list) {
      if (!item?.path || seen.has(item.path) || BLOCK.has(item.path)) continue;
      if (!isWanted(item.path)) continue;
      queue.push({ path: item.path, method: item.method || "unknown", from: item.from || "" });
      seen.add(item.path);
      added += 1;
    }
    return added;
  }

  async function refreshStat(el) {
    const rows = await allRecords();
    const q = await loadQueue();
    const ok = rows.filter((r) => r.status === 200).length;
    const miss = rows.filter((r) => r.status === 404 || r.status === 403).length;
    el.textContent = `Saved on this browser: ${ok} files, ${miss} misses. Waiting to fetch: ${q.length}.`;
    return { ok, miss, waiting: q.length };
  }

  async function processQueue(logEl, statEl, opts) {
    const includeSensitive = opts.sensitive;
    const chase = opts.chase;
    const phase = opts.onPhase || (() => {});
    phase(1, "Building the list of paths");
    const cacheRows = await allRecords();
    const cache = new Map(cacheRows.map((r) => [r.path, r]));
    let queue = await loadQueue();
    if (opts.seed) mergeQueue(queue, seeds(includeSensitive));
    if (opts.guess) {
      for (const rec of cacheRows) {
        if (rec.status === 200) mergeQueue(queue, guessFrom(rec.path));
      }
    }
    if (opts.probe) {
      for (const [path, method] of PROBES) mergeQueue(queue, [{ path, method, from: "" }]);
    }
    await saveQueue(queue);
    phase(2, `${queue.length} paths on the list. Fetching up to ${MAX_NEW_GETS} that are not saved yet.`);

    let network = 0;
    let skipped = 0;
    const session = [];
    while (queue.length && network < MAX_NEW_GETS) {
      const item = queue[0];
      if (!includeSensitive && SENSITIVE.has(item.path)) {
        queue.shift();
        session.push({ ...item, status: "skipped", note: "sensitive checkbox off" });
        continue;
      }
      const cached = cache.get(item.path);
      if (cached && terminal(cached.status)) {
        queue.shift();
        skipped += 1;
        if (cached.status === 200 && cached.body) {
          if (chase) {
            const found = extractRefs(cached.body, item.path);
            const n = mergeQueue(queue, found.refs);
            if (n) log(logEl, `from cache ${item.path} +${n} paths`);
            if (found.actions.length) {
              cached.actions = [...new Set([...(cached.actions || []), ...found.actions])];
              await putRecord(cached);
            }
          }
          if (opts.guess) mergeQueue(queue, guessFrom(item.path));
        }
        continue;
      }
      if (network) await sleep(DELAY_MS);
      phase(2, `Request ${network + 1} of ${MAX_NEW_GETS}: ${item.path}`);
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
        log(logEl, "503 — stopped. Queue kept. Wait or reboot before resume.");
        session.push({
          ...item,
          status: 503,
          bytes: (res.body || "").length,
          note: "not cached; lockout",
          at: new Date().toISOString(),
        });
        break;
      }
      const body = res.status === 200 ? redact(res.body) : res.body || "";
      const rec = {
        path: item.path,
        status: res.status,
        method: item.method,
        from: item.from || "",
        bytes: body.length,
        sha256: await sha256(body),
        bodyClass: classifyBody(res.status, body),
        at: new Date().toISOString(),
        body: res.status === 200 ? body : "",
        missExcerpt: res.status === 200 ? "" : body.slice(0, 240),
        actions: [],
      };
      await putRecord(rec);
      if (res.status === 200) {
        try {
          if (chase) {
            const found = extractRefs(body, item.path);
            rec.actions = found.actions || [];
            const n = mergeQueue(queue, found.refs);
            if (n) log(logEl, `  linked paths +${n}`);
          }
          if (opts.guess) {
            const n = mergeQueue(queue, guessFrom(item.path));
            if (n) log(logEl, `  similar names +${n}`);
          }
          if (rec.actions?.length) await putRecord(rec);
        } catch (e) {
          log(logEl, `  saved ${item.path}, skipped link scan: ${e.message}`);
        }
      }
      cache.set(rec.path, rec);
      queue.shift();
      session.push(rec);
      log(logEl, `  ${res.status} ${rec.bodyClass} ${rec.bytes}B`);
      if (network % 5 === 0) {
        await saveQueue(queue);
        await refreshStat(statEl);
      }
    }
    if (network >= MAX_NEW_GETS && queue.length) {
      log(logEl, `paused after ${MAX_NEW_GETS} new GETs; ${queue.length} still queued`);
    }
    await saveQueue(queue);
    await setMeta("lastSession", session);
    await refreshStat(statEl);
    phase(2, `Fetch finished. ${network} new requests, ${skipped} already saved, ${queue.length} still waiting.`);
    log(logEl, `done. new GETs ${network}, cache skips ${skipped}, queue ${queue.length}`);
    return { network, skipped, waiting: queue.length };
  }

  function mdEscape(s) {
    return String(s ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ");
  }

  function buildReports(rows, queue) {
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
    lines.push("503 is not stored here — that run stops and leaves the path queued.");
    lines.push("Method is how the path was chosen, not the HTTP verb (every probe is GET).");
    lines.push("");
    lines.push("| Path | HTTP | Method | Discovered from | When | Bytes | Body class | SHA-256 |");
    lines.push("| --- | ---: | --- | --- | --- | ---: | --- | --- |");
    for (const r of misses.sort((a, b) => a.path.localeCompare(b.path))) {
      lines.push(
        `| ${mdEscape(r.path)} | ${r.status} | ${mdEscape(r.method)} | ${mdEscape(r.from)} | ${mdEscape(r.at)} | ${r.bytes ?? ""} | ${mdEscape(r.bodyClass)} | ${mdEscape((r.sha256 || "").slice(0, 16))} |`
      );
    }
    lines.push("");
    lines.push("## Notes per miss");
    lines.push("");
    for (const r of misses.sort((a, b) => a.path.localeCompare(b.path))) {
      lines.push(`### ${r.path}`);
      lines.push("");
      lines.push(`- HTTP ${r.status} via GET`);
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
    index.push(`Still queued: ${queue.length}`);
    index.push("");
    index.push("## Counts by method and status");
    index.push("");
    for (const k of Object.keys(byMethod).sort()) index.push(`- ${k}: ${byMethod[k]}`);
    index.push("");
    index.push("## Hits");
    index.push("");
    index.push("| Path | Bytes | Method | From | Class | SHA-256 |");
    index.push("| --- | ---: | --- | --- | --- | --- |");
    for (const r of hits.sort((a, b) => a.path.localeCompare(b.path))) {
      index.push(
        `| ${mdEscape(r.path)} | ${r.bytes} | ${mdEscape(r.method)} | ${mdEscape(r.from)} | ${mdEscape(r.bodyClass)} | ${(r.sha256 || "").slice(0, 16)} |`
      );
    }
    index.push("");
    index.push("## Queued (not fetched yet)");
    index.push("");
    for (const q of queue) index.push(`- \`${q.path}\` — ${q.method} from ${q.from || "seed"}`);
    index.push("");

    const leads = [];
    leads.push("# Action strings seen in HTTP 200 bodies");
    leads.push("");
    leads.push("These are client-side strings. They are not proof the server accepts them.");
    leads.push("");
    for (const r of hits) {
      if (!r.actions?.length) continue;
      leads.push(`## ${r.path}`);
      leads.push("");
      for (const a of r.actions) leads.push(`- \`${a}\``);
      leads.push("");
    }
    return {
      misses: lines.join("\n"),
      index: index.join("\n"),
      leads: leads.join("\n"),
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

  function fileNameFor(path) {
    const clean = path.replace(/^\//, "").replace(/\//g, "__");
    if (path.endsWith(".lp")) return `files/${clean}.html`;
    return `files/${clean}`;
  }

  async function downloadPackage(logEl) {
    const rows = await allRecords();
    const queue = await loadQueue();
    const reports = buildReports(rows, queue);
    const enc = new TextEncoder();
    const files = [
      { name: "MISSES.md", data: enc.encode(reports.misses) },
      { name: "INDEX.md", data: enc.encode(reports.index) },
      { name: "LEADS.md", data: enc.encode(reports.leads) },
    ];
    for (const r of rows) {
      if (r.status !== 200 || !r.body) continue;
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
    log(logEl, `zip: ${rows.filter((r) => r.status === 200).length} files + MISSES.md`);
  }

  function buildPanel() {
    const root = document.createElement("div");
    root.id = "genesis-f1-grabber";
    root.innerHTML = `
      <h3>F1 grabber</h3>
      <section class="step" id="gf1-step1">
        <h4>1. Choose what to look for</h4>
        <label><input type="checkbox" id="gf1-known" checked /><span>Known pages and scripts</span></label>
        <label><input type="checkbox" id="gf1-follow" checked /><span>New paths linked inside those files</span></label>
        <label><input type="checkbox" id="gf1-guess" checked /><span>Similar names (modal.lp → matching .js, and the reverse)</span></label>
        <label><input type="checkbox" id="gf1-probe" checked /><span>A short extra list (robots.txt, overview.lp, the wireless ajax script)</span></label>
        <label><input type="checkbox" id="gf1-sensitive" /><span>Wi‑Fi QR page (can contain the Wi‑Fi key)</span></label>
        <p class="plan" id="gf1-plan"></p>
      </section>
      <section class="step" id="gf1-step2">
        <h4>2. Fetch</h4>
        <button type="button" class="gf1-primary" id="gf1-run">Run</button>
        <p class="now" id="gf1-now">Nothing running. Run continues after a refresh and skips paths already saved.</p>
        <p class="stat" id="gf1-stat">Loading saved results…</p>
      </section>
      <section class="step" id="gf1-step3">
        <h4>3. Save the package</h4>
        <button type="button" id="gf1-zip">Download one zip</button>
        <p class="plan">The zip holds the files plus MISSES.md (every 404 and 403, and how that path was chosen). Run also downloads this zip when it finishes.</p>
        <button type="button" class="gf1-quiet" id="gf1-clear">Delete saved results</button>
      </section>
      <div class="log" id="gf1-log"></div>
    `;
    document.body.appendChild(root);
    const logEl = root.querySelector("#gf1-log");
    const statEl = root.querySelector("#gf1-stat");
    const nowEl = root.querySelector("#gf1-now");
    const planEl = root.querySelector("#gf1-plan");
    const steps = [...root.querySelectorAll(".step")];

    function checked(id) {
      return root.querySelector(id).checked;
    }

    function describePlan() {
      const parts = [];
      if (checked("#gf1-known")) parts.push("known files");
      if (checked("#gf1-follow")) parts.push("links inside them");
      if (checked("#gf1-guess")) parts.push("similar names");
      if (checked("#gf1-probe")) parts.push("the extra list");
      if (checked("#gf1-sensitive")) parts.push("the Wi‑Fi QR page");
      planEl.textContent = parts.length
        ? `Run will look for ${parts.join(", ")}. At most ${MAX_NEW_GETS} new requests, then the zip.`
        : "Tick at least one source above.";
    }

    function markStep(n) {
      steps.forEach((el, i) => el.classList.toggle("on", i + 1 === n));
    }

    describePlan();
    root.querySelectorAll("input").forEach((el) => el.addEventListener("change", describePlan));
    refreshStat(statEl).catch((e) => log(logEl, String(e)));

    root.querySelector("#gf1-run").onclick = async () => {
      if (busy) return;
      if (!checked("#gf1-known") && !checked("#gf1-follow") && !checked("#gf1-guess") && !checked("#gf1-probe")) {
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
          onPhase: (n, text) => {
            markStep(n);
            nowEl.textContent = text;
          },
        });
        markStep(3);
        nowEl.textContent = "Fetching stopped. Saving the zip.";
        await downloadPackage(logEl);
        nowEl.textContent = "Zip downloaded. Run again to continue anything still waiting.";
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
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", buildPanel);
  else buildPanel();
})();
