#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pkg = path.join(path.dirname(fileURLToPath(import.meta.url)), "password-encoding");
const srp = path.join(os.homedir(), "Downloads", "f1-grab_js_srp-min.js");

if (!fs.existsSync(srp)) {
  console.log("skip: baseline srp-min.js not present");
  process.exit(0);
}

const test = spawnSync("npm", ["test"], {
  cwd: pkg,
  encoding: "utf8",
  env: { ...process.env, F1_PASSWORD_SRP_JS: srp },
});
if (test.status !== 0) {
  process.stderr.write(test.stderr || test.stdout);
  process.exit(test.status ?? 1);
}
console.log("ok");
