# F1 password-encoding (TypeScript)

Offline tools for the UTF-8 SRP vs low-byte `sha512crypt` investigation.

**Live device password changes must use `referencePasswordBlob()`** (vendor `generateSaltAndVerifierTheCallback` in a VM). Do not reimplement SRP verifier math by hand.

Repo gate (run from genesis root):

```sh
./scripts/verify_password_encoding_tooling.sh
```

Python entry: `scripts/f1_password_blob.py` → shim `f1_password_blob.mjs` → this package.

```sh
cd scripts/password-encoding
npm install
npm test          # golden tests (needs ~/Downloads/f1-grab_js_srp-min.js or F1_PASSWORD_SRP_JS)
npm run matrix    # encoding matrix JSON
echo '{"username":"User","newPassword":"Aa0!CtrlPass9"}' | npm run blob
```

Parent shims: `scripts/f1_password_blob.mjs`, `scripts/f1_password_encoding_matrix.mjs`.
