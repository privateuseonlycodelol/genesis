#!/usr/bin/env node
/** Shim → scripts/password-encoding matrix CLI. */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), "password-encoding");
const cli = path.join(dir, "dist", "cli", "matrix.js");

const build = spawnSync("npm", ["run", "build"], { cwd: dir, encoding: "utf8" });
if (build.status !== 0) {
  process.stderr.write(build.stderr || build.stdout);
  process.exit(build.status ?? 1);
}

const run = spawnSync("node", [cli], { stdio: "inherit" });
process.exit(run.status ?? 1);
