#!/usr/bin/env node
/**
 * Compute SRP M/v using router srp-min.js (no HTTP). Uses fresh random A from JS.
 * Usage: F1_PASSWORD=... F1_CSRF=... node f1_srp_node.mjs auth-identify.json
 */
import fs from "fs";
import vm from "vm";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const server = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const password = process.env.F1_PASSWORD || "";
const username = process.env.F1_USER || "User";
const csrf = process.env.F1_CSRF || "dummy";

if (!password) process.exit(2);

const srpCode = fs.readFileSync(path.join(root, "artifacts/ui/srp-min.js"), "utf8");

function createDeferred() {
  const d = { _cb: [] };
  d.promise = () => d;
  d.done = (fn) => {
    d._cb.push(fn);
    return d;
  };
  d.then = (fn) => d.done(fn);
  d.fail = () => d;
  d.resolve = (val) => {
    for (const fn of d._cb) fn(val);
  };
  return d;
}

const zeroQueue = [];
const sandbox = {
  window: {},
  console,
  setInterval: () => 0,
  clearInterval: () => {},
  setTimeout: (fn, _ms) => {
    zeroQueue.push(fn);
    return 0;
  },
  navigator: { appName: "Netscape" },
  postMessage: (msg) => {
    if (msg === "zero-timeout-message" && zeroQueue.length) {
      const fn = zeroQueue.shift();
      fn();
    }
  },
  addEventListener: (type, handler) => {
    if (type === "message") sandbox._msgHandler = handler;
  },
};
sandbox.window = sandbox;
sandbox.postMessage = (msg) => {
  if (msg === "zero-timeout-message" && zeroQueue.length && sandbox._msgHandler) {
    sandbox._msgHandler({ source: sandbox.window, data: msg, stopPropagation: () => {} });
  }
};
sandbox.window.postMessage = sandbox.postMessage.bind(sandbox);

const $ = (sel) => ({
  attr: (name) => (name === "content" ? csrf : undefined),
  filter: () => ({ attr: () => csrf }),
});
$.Deferred = createDeferred;
$.post = (url, data, success) => {
  if (data.A) {
    success(server);
    return;
  }
  if (data.M) {
    sandbox.__clientM = data.M;
    return;
  }
};
sandbox.$ = $;

vm.createContext(sandbox);
vm.runInContext(srpCode, sandbox);

const script = `
var srp = new SRP();
var done = false;
srp.success = function() {
  done = true;
  __out = { M: __clientM, v: srp.key() };
};
srp.identify("/authenticate", ${JSON.stringify(username)}, ${JSON.stringify(password)});
`;

vm.runInContext("var __out=null; var __clientM=null;" + script, sandbox);

while (zeroQueue.length) {
  const fn = zeroQueue.shift();
  fn();
}

if (!sandbox.__clientM) {
  console.error("SRP did not complete");
  process.exit(1);
}
console.log(JSON.stringify({ M: sandbox.__clientM }));
