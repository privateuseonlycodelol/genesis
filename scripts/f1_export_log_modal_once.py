#!/usr/bin/env python3
"""One export_log POST to the F1 logviewer modal, with the page-level CSRF token.

Single request by design: refuses to run without --confirm so a stray rerun cannot
stack requests (the 2026-10-12 bursts caused nginx 503s). Saves the body under
artifacts/exports/ (gitignored) and never prints the admin password or the token.

Usage: python3 scripts/f1_export_log_modal_once.py --confirm --out-name <dir-name>
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from f1_session_store import ensure_admin_session, refresh_csrf_from_modal  # noqa: E402

BASE = "http://192.168.1.1"
PASSWORD_FILE = ROOT / "artifacts" / "secrets" / "f1-admin.password"
EXPORT_PATH = "/modals/logviewer-modal.lp"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="required: acknowledges one live POST")
    ap.add_argument("--out-name", required=True, help="directory name under artifacts/exports/")
    args = ap.parse_args()
    if not args.confirm:
        print("refusing: pass --confirm to send the single export_log POST", file=sys.stderr)
        return 2

    out_dir = ROOT / "artifacts" / "exports" / args.out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    password = PASSWORD_FILE.read_text().strip()
    client, how = ensure_admin_session(password, base=BASE)
    del password
    print("session:", how)

    time.sleep(5)  # pacing before the token fetch
    csrf = refresh_csrf_from_modal(client, "/gateway.lp")
    print("csrf length:", len(csrf))

    time.sleep(5)  # pacing before the POST
    body = urllib.parse.urlencode({"action": "export_log", "CSRFtoken": csrf}).encode()
    req = urllib.request.Request(BASE + EXPORT_PATH, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Referer", BASE + "/gateway.lp")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(client.jar))
    try:
        with opener.open(req, timeout=30) as resp:
            code, headers, data = resp.getcode(), dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        code, headers, data = err.code, dict(err.headers), err.read()

    (out_dir / "response.bin").write_bytes(data)
    meta = [f"status={code}", f"bytes={len(data)}"]
    meta += [f"{k}={headers.get(k)}" for k in ("Content-Type", "Content-Disposition", "Content-Length")]
    (out_dir / "meta.txt").write_text("\n".join(meta) + "\n")
    client.save_jar()
    print("\n".join(meta))
    return 0 if code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
