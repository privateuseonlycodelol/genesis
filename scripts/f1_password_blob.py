"""Password-change blob generation via vendor srp-min.js (TypeScript reference).

Never reimplement SRP verifier math in Python. Live device scripts must call
``generate_password_blob`` after ``run_reference_blob_tests`` succeeds.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

SCRIPTS = Path(__file__).resolve().parent
PASSWORD_ENCODING_PKG = SCRIPTS / "password-encoding"
BLOB_SHIM = SCRIPTS / "f1_password_blob.mjs"


class PasswordBlob(TypedDict):
    salt: str
    verifier: str
    cryptedpassword: str


class PasswordBlobInput(TypedDict, total=False):
    username: str
    newPassword: str
    srpSaltHex: str
    cryptSaltHex: str


def _tests_skipped_by_env() -> bool:
    return os.environ.get("F1_SKIP_PASSWORD_BLOB_TESTS", "").lower() in (
        "1",
        "true",
        "yes",
    )


def run_reference_blob_tests() -> None:
    """Run golden tests in scripts/password-encoding (needs baseline srp-min.js)."""
    if _tests_skipped_by_env():
        return
    if not PASSWORD_ENCODING_PKG.is_dir():
        raise RuntimeError(f"missing package: {PASSWORD_ENCODING_PKG}")
    proc = subprocess.run(
        ["npm", "test"],
        cwd=PASSWORD_ENCODING_PKG,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-800:]
        raise RuntimeError(f"password_encoding_tests_failed:\n{tail}")


def generate_password_blob(
    username: str,
    new_password: str,
    *,
    run_tests: bool = True,
) -> PasswordBlob:
    if run_tests:
        run_reference_blob_tests()
    payload: PasswordBlobInput = {
        "username": username,
        "newPassword": new_password,
    }
    proc = subprocess.run(
        ["node", str(BLOB_SHIM)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"blob_generator_failed: {(proc.stderr or proc.stdout)[:400]}")
    data = json.loads(proc.stdout)
    for key in ("salt", "verifier", "cryptedpassword"):
        if key not in data or not isinstance(data[key], str):
            raise RuntimeError(f"blob_missing_field:{key}")
    return data  # type: ignore[return-value]
