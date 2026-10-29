#!/usr/bin/env python3
"""GET-only read of /modals/printersharing-modal.lp: save the body and print printersharing controls.

No POST is sent. The full body goes to a timestamped folder under artifacts/ (private).
Only the lines that name a printersharing control are printed.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from f1_secrets import read_password_file, validate_router_base
from f1_session_store import ensure_admin_session, login_marker

MODAL = "/modals/printersharing-modal.lp"
ROOT = Path(__file__).resolve().parent.parent
CONTROL = re.compile(r"<(input|select|option|textarea)\b[^>]*printersharing[^>]*>", re.I)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://192.168.1.1")
    parser.add_argument("--password-file", type=Path, default=ROOT / "artifacts/secrets/f1-admin.password")
    args = parser.parse_args()

    base = validate_router_base(args.base)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "artifacts" / "management" / f"printersharing-read-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    password = read_password_file(args.password_file)
    client, how = ensure_admin_session(password, base=base)
    del password
    print(f"session: {how}")

    code, _ = client._open(client.base + "/login.lp", None, "GET")
    print(f"login.lp: {code}")
    if code != 200:
        print("stopped: login.lp not 200 (possible 503 lockout); no modal read")
        return 2

    code, body = client._open(client.base + MODAL, None, "GET")
    print(f"modal: {code} {len(body)} B")
    if code != 200 or login_marker(body):
        print("stopped: modal not served as an authenticated page")
        return 2
    (out / "modal.html").write_bytes(body)
    print(f"saved: {out / 'modal.html'}")

    text = body.decode("utf-8", "replace")
    controls = [m.group(0) for m in CONTROL.finditer(text)]
    print(f"printersharing controls: {len(controls)}")
    for tag in controls:
        print(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
