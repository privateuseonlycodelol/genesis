import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function defaultSrpMinPath(): string {
  const env = process.env.F1_PASSWORD_SRP_JS;
  if (env) return path.resolve(env);
  return path.join(os.homedir(), "Downloads", "f1-grab_js_srp-min.js");
}

export function readSrpMinSource(filePath = defaultSrpMinPath()): string {
  return fs.readFileSync(filePath, "utf8");
}

export function sha256File(filePath: string): string {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

/** Extract a top-level `function name(...){` block from minified vendor JS. */
export function extractFunction(text: string, marker: string): string {
  const start = text.indexOf(marker);
  assert.notEqual(start, -1, `missing: ${marker}`);
  const open = text.indexOf("{", start);
  assert.notEqual(open, -1, "missing function body");
  let depth = 0;
  let quote: string | null = null;
  let escaped = false;
  for (let i = open; i < text.length; i++) {
    const ch = text[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") {
      quote = ch;
      continue;
    }
    if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) return text.slice(start, i + 1);
  }
  throw new Error(`unterminated: ${marker}`);
}
