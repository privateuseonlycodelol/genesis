#!/usr/bin/env python3
"""Bounded live test: password change with non-ASCII, web re-login, optional revert.

Requires --password-file and --new-password (or --revert with --new-password as current).
Does not print passwords or hashes. Evidence under artifacts/management/password-encoding-<ts>/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f1_password_blob import generate_password_blob, run_reference_blob_tests
from f1_secrets import read_password_file
from f1_session_store import ensure_admin_session
from f1_srp_login import SRPClient, crypto_prepare, crypto_proof


def srp_password_proof(client: SRPClient, username: str, password: str) -> tuple[int, str]:
    prep = crypto_prepare()
    post1 = urllib.parse.urlencode(
        {"CSRFtoken": client.csrf, "I": username, "A": prep["A_hex"]}
    ).encode()
    code1, body1 = client._open(f"{client.base}/password", post1, "POST")
    if code1 != 200:
        return code1, "identify_http"
    try:
        r1 = json.loads(body1.decode())
    except json.JSONDecodeError:
        return code1, "identify_json"
    salt, b_hex = r1.get("s"), r1.get("B")
    if not salt or not b_hex:
        return code1, "identify_fields"
    proof = crypto_proof(
        prep["F"], prep["A_hex"], prep["A_int"], username, password, salt, b_hex
    )
    post2 = urllib.parse.urlencode({"CSRFtoken": client.csrf, "M": proof["M"]}).encode()
    code2, body2 = client._open(f"{client.base}/password", post2, "POST")
    if code2 != 200:
        return code2, "verify_http"
    try:
        r2 = json.loads(body2.decode())
    except json.JSONDecodeError:
        return code2, "verify_json"
    if r2.get("M", "").upper() != proof["v"].upper():
        return 401, "verify_mismatch"
    return 200, "ok"


def post_new_credentials(client: SRPClient, blob: dict) -> tuple[int, str]:
    fields = {
        "CSRFtoken": client.csrf,
        "salt": blob["salt"],
        "verifier": blob["verifier"],
        "cryptedpassword": blob["cryptedpassword"],
    }
    post = urllib.parse.urlencode(fields).encode()
    try:
        code, body = client._open(f"{client.base}/password", post, "POST")
    except Exception as exc:
        return getattr(exc, "code", 0) or -1, type(exc).__name__
    try:
        r = json.loads(body.decode())
    except json.JSONDecodeError:
        return code, "change_non_json"
    if r.get("success"):
        return 200, "changed"
    return code, r.get("error", "change_failed")


def try_login(username: str, password: str, jar_path: Path) -> str:
    client = SRPClient(str(jar_path), "http://192.168.2.1")
    code, body = client._open(client.base + "/login.lp")
    if code != 200:
        return f"login_page_{code}"
    client.load_csrf(body.decode())
    code, result = client.login(username, password)
    return "ok" if code == 200 and result == "ok" else f"fail_{code}_{result}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--new-password", required=True, help="target password for change or revert")
    parser.add_argument("--username", default="User")
    parser.add_argument("--revert", action="store_true", help="change from --new-password back using file password as target")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--ack-lockout-risk",
        action="store_true",
        help="required for live run: mis-generated verifier can brick web login",
    )
    args = parser.parse_args()
    if not args.dry_run and not args.ack_lockout_risk:
        print(
            json.dumps(
                {
                    "error": "refused",
                    "reason": "pass --ack-lockout-risk after scripts/verify_password_encoding_tooling.sh",
                }
            )
        )
        return 2

    current = read_password_file(args.password_file)
    username = args.username
    if args.revert:
        new_password = current
        current_for_proof = args.new_password
    else:
        new_password = args.new_password
        current_for_proof = current

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = ROOT / "artifacts" / "management" / f"password-encoding-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {"dry_run": args.dry_run, "revert": args.revert, "username": username}

    run_reference_blob_tests()
    blob = generate_password_blob(username, new_password, run_tests=False)
    summary["blob_field_lengths"] = {
        k: len(blob[k]) for k in ("salt", "verifier", "cryptedpassword")
    }
    summary["crypted_prefix"] = blob["cryptedpassword"][:7]  # $6$ only, no hash body

    if args.dry_run:
        summary["stopped"] = "dry_run"
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))
        return 0

    jar = out_dir / "session.cookies.txt"
    admin_client, how = ensure_admin_session(current, jar_path=jar)
    summary["admin_session"] = how
    code, body = admin_client._open(admin_client.base + "/password.lp")
    if code != 200:
        summary["error"] = f"password_lp_{code}"
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))
        return 1
    admin_client.load_csrf(body.decode())
    client = admin_client

    proof_code, proof_msg = srp_password_proof(client, username, current_for_proof)
    summary["current_password_proof"] = {"code": proof_code, "msg": proof_msg}
    if proof_code != 200:
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))
        return 1

    ch_code, ch_msg = post_new_credentials(client, blob)
    summary["change"] = {"code": ch_code, "msg": ch_msg}

    login_jar = out_dir / "login-test.cookies.txt"
    summary["login_with_new"] = try_login(username, new_password, login_jar)

    if not args.revert and ch_code == 200:
        summary["login_with_old_should_fail"] = try_login(username, current, out_dir / "old-login.cookies.txt")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0 if ch_code == 200 and summary["login_with_new"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
