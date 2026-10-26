import crypto from "node:crypto";
import vm from "node:vm";
import type { PasswordBlob, PasswordBlobInput, SaltOverride } from "./types.js";
import { readSrpMinSource } from "./srpSource.js";

const H_INJECT =
  'function h(a){if(typeof globalThis.__f1_h_override==="function"){var o=globalThis.__f1_h_override(a);if(o)return o;}1>a';

const MODPOW_PATCH = `BigInteger.prototype.modPowPromise=function(e,m){var self=this;var result={done:function(fn){try{fn(self.modPow(e,m));}catch(err){throw err;}return result;},then:function(fn){return this.done(fn);},fail:function(){return result;}};return result;};`;

type SrpCtor = new () => {
  generateSaltAndVerifierTheCallback: (
    username: string,
    password: string,
    cb: (salt: string, verifier: string, crypted: string) => void
  ) => void;
};

function prepareSource(raw: string): string {
  if (!raw.includes("function h(a){1>a")) {
    throw new Error("srp-min.js: expected h() helper; pin a matching baseline");
  }
  let out = raw.replace("function h(a){1>a", H_INJECT);
  out = out.replace("window.jsSHA=function", "jsSHA=function");
  return `var jsSHA;\n${out}`;
}

function createSandbox(saltOverride?: SaltOverride): vm.Context {
  const windowStub = {
    postMessage: () => {},
    addEventListener: () => {},
    setTimeout: (fn: () => void) => {
      fn();
      return 0;
    },
  };
  const ctx: Record<string, unknown> = {
    console,
    navigator: { appName: "Netscape" },
    window: windowStub,
    alert: () => {},
    $: { post: () => {} },
    require: (id: string) => {
      if (id === "./lib/sha512.js") {
        return {
          rstr_sha512: (s: string) =>
            crypto.createHash("sha512").update(Buffer.from(s, "binary")).digest("binary"),
        };
      }
      throw new Error(`require blocked: ${id}`);
    },
    exports: {},
    __f1_h_override: saltOverride,
  };
  ctx.globalThis = ctx;
  return vm.createContext(ctx);
}

/**
 * Generate password-change fields using the vendor generateSaltAndVerifierTheCallback
 * (sync modPowPromise patch). This is the only implementation that may feed a live device.
 */
export function referencePasswordBlob(
  input: PasswordBlobInput,
  options?: { source?: string; saltOverride?: SaltOverride }
): PasswordBlob {
  const raw = options?.source ?? readSrpMinSource();
  const patched = prepareSource(raw);
  const ctx = createSandbox(options?.saltOverride ?? makeFixedSaltOverride(input));
  vm.runInContext(patched + "\n" + MODPOW_PATCH, ctx);
  const SRP = vm.runInContext("SRP", ctx) as SrpCtor;
  const srp = new SRP();

  let out: PasswordBlob | undefined;
  srp.generateSaltAndVerifierTheCallback(input.username, input.newPassword, (salt, verifier, crypted) => {
    out = { salt, verifier, cryptedpassword: crypted };
  });
  if (!out) throw new Error("generateSaltAndVerifierTheCallback produced no output");
  return out;
}

function makeFixedSaltOverride(input: PasswordBlobInput): SaltOverride | undefined {
  if (!input.srpSaltHex && !input.cryptSaltHex) return undefined;
  return (quartets: number) => {
    if (quartets === 8 && input.srpSaltHex) return input.srpSaltHex;
    if (quartets === 16 && input.cryptSaltHex) return input.cryptSaltHex;
    return undefined;
  };
}
