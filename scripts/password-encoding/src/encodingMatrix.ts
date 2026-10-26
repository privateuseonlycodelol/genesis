import assert from "node:assert/strict";
import crypto from "node:crypto";
import vm from "node:vm";
import { defaultSrpMinPath, extractFunction, readSrpMinSource } from "./srpSource.js";

export type MatrixCase = {
  id: string;
  strength_level: number;
  password_utf8_vs_lowbyte_differ: boolean;
  crypt_same_for_pair: boolean | null;
  srp_identity_same_for_pair: boolean | null;
  strength_level_b?: number;
  lowbyte_strings_equal?: boolean;
};

export type MatrixResult = {
  source_sha256: string;
  cases: MatrixCase[];
};

function loadSha512Crypt(source: string): (password: string, salt: string) => string {
  const shaFunctions = [
    extractFunction(source, "function _extend(a,b){"),
    extractFunction(source, "function _sha512crypt_intermediate(a,b){"),
    extractFunction(source, "function _rstr_sha512crypt(a,b,c){"),
    extractFunction(source, "function sha512crypt(a,b){"),
  ].join("\n");
  const ctx = vm.createContext({
    rstr_sha512(binaryString: string) {
      return crypto
        .createHash("sha512")
        .update(Buffer.from(binaryString, "binary"))
        .digest("binary");
    },
  });
  vm.runInContext(`${shaFunctions}; globalThis.sha512crypt = sha512crypt;`, ctx);
  return ctx.sha512crypt as (password: string, salt: string) => string;
}

function loadUtf8Helper(source: string): (s: string) => string {
  const helperStart = source.indexOf("function SRP(){");
  assert.notEqual(helperStart, -1);
  const utf8Helper = extractFunction(source.slice(helperStart), "function a(a){");
  const ctx = vm.createContext({});
  vm.runInContext(`${utf8Helper}; globalThis.encodeUtf8 = a;`, ctx);
  return ctx.encodeUtf8 as (s: string) => string;
}

function lowByteString(s: string): string {
  let out = "";
  for (let i = 0; i < s.length; i++) out += String.fromCharCode(s.charCodeAt(i) & 0xff);
  return out;
}

const SPL_CHAR = /[\x20-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E\x80-\xFE]/;

export function passwordCheckLevel(password: string, minLen: number): number {
  let level = 0;
  if (password.match(/[a-z]/) && password.match(/[A-Z]/)) level++;
  if (password.match(/\d+/)) level++;
  if (password.match(SPL_CHAR)) level++;
  if (password.length >= minLen) level++;
  if (password.length > minLen && level === 4) level++;
  return level;
}

export function runEncodingMatrix(sourcePath = defaultSrpMinPath()): MatrixResult {
  const source = readSrpMinSource(sourcePath);
  const sha512crypt = loadSha512Crypt(source);
  const encodeUtf8 = loadUtf8Helper(source);
  const salt = "1a2b3c4d5e6f7089";
  const user = "User";

  const rows = [
    { id: "ascii_control", a: "Aa0!CtrlPass", b: null as string | null },
    { id: "latin1_e_acute", a: "Aa0!\u00e9bcdefgh", b: null },
    { id: "lowbyte_collision_0100_vs_0000", a: "Aa0!\u0100bcdefg", b: "Aa0!\u0000bcdefg" },
    { id: "lowbyte_collision_01e9_vs_00e9", a: "Aa0!\u01e9bcdefg", b: "Aa0!\u00e9bcdefg" },
    { id: "supplementary_plane", a: "Aa0!\u{1F600}bcdef", b: null },
  ];

  const cases: MatrixCase[] = [];
  for (const row of rows) {
    const entry: MatrixCase = {
      id: row.id,
      strength_level: passwordCheckLevel(row.a, 10),
      password_utf8_vs_lowbyte_differ: !Buffer.from(encodeUtf8(row.a), "binary").equals(
        Buffer.from(lowByteString(row.a), "binary")
      ),
      crypt_same_for_pair: null,
      srp_identity_same_for_pair: null,
    };
    const cryptA = sha512crypt(row.a, salt);
    if (row.b) {
      entry.crypt_same_for_pair = cryptA === sha512crypt(row.b, salt);
      const idA = Buffer.from(encodeUtf8(`${user}:${row.a}`), "binary");
      const idB = Buffer.from(encodeUtf8(`${user}:${row.b}`), "binary");
      entry.srp_identity_same_for_pair = idA.equals(idB);
      entry.strength_level_b = passwordCheckLevel(row.b, 10);
      entry.lowbyte_strings_equal = lowByteString(row.a) === lowByteString(row.b);
    }
    cases.push(entry);
  }

  return {
    source_sha256: crypto.createHash("sha256").update(source).digest("hex"),
    cases,
  };
}
