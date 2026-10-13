#!/usr/bin/env python3
"""One authenticated POST system_reboot (same as UI Restart). Disrupts LAN/Wi-Fi briefly."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
from pathlib import Path

from f1_pacing import fetch_login_status
from f1_session_store import ensure_admin_session, refresh_csrf_from_modal

MODAL = "/modals/system-config-modal.lp"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="login + CSRF only, no reboot POST")
    args = parser.parse_args()
    if fetch_login_status() != 200:
        print(json.dumps({"error": "login_lp_not_200"}), file=sys.stderr)
        return 2
    import os

    os.umask(0o077)
    password = args.password_file.read_text().strip("\n")
    try:
        client, how = ensure_admin_session(password)
    except RuntimeError as err:
        print(json.dumps({"error": str(err)}))
        return 2
    del password
    refresh_csrf_from_modal(client, MODAL)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_post": "system_reboot", "session": how}))
        return 0
    data = urllib.parse.urlencode(
        {"action": "system_reboot", "CSRFtoken": client.csrf}
    ).encode()
    try:
        code, body = client._open(client.base + MODAL, data, "POST")
    except urllib.error.HTTPError as err:
        code, body = err.code, err.read()
    print(
        json.dumps(
            {
                "action": "system_reboot",
                "session": how,
                "status": code,
                "bytes": len(body),
                "body_preview": body[:200].decode("utf-8", "replace"),
            }
        )
    )
    return 0 if code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
