import assert from "node:assert/strict";
import { describe, it } from "node:test";
import fs from "node:fs";
import { defaultSrpMinPath } from "../srpSource.js";
import { referencePasswordBlob } from "../referencePasswordBlob.js";

const baseline = defaultSrpMinPath();

describe("referencePasswordBlob", () => {
  it("is deterministic for fixed salts", { skip: !fs.existsSync(baseline) }, () => {
    const fixed = {
      username: "User",
      newPassword: "Aa0!\u00e9bcdefgh",
      srpSaltHex: "abcd1234",
      cryptSaltHex: "1a2b3c4d5e6f7089",
    };
    const a = referencePasswordBlob(fixed);
    const b = referencePasswordBlob(fixed);
    assert.equal(a.salt, fixed.srpSaltHex);
    assert.equal(a.verifier.toLowerCase(), b.verifier.toLowerCase());
    assert.equal(a.cryptedpassword, b.cryptedpassword);
    assert.match(a.cryptedpassword, /^\$6\$/);
    assert.equal(a.verifier.length, 512);
  });

  it("ASCII and non-ASCII produce different verifiers", { skip: !fs.existsSync(baseline) }, () => {
    const salts = { srpSaltHex: "cafebabe", cryptSaltHex: "feedface01234567" };
    const ascii = referencePasswordBlob({
      username: "User",
      newPassword: "Aa0!CtrlPass9",
      ...salts,
    });
    const latin = referencePasswordBlob({
      username: "User",
      newPassword: "Aa0!\u00e9bcdefgh",
      ...salts,
    });
    assert.notEqual(ascii.verifier.toLowerCase(), latin.verifier.toLowerCase());
  });
});
