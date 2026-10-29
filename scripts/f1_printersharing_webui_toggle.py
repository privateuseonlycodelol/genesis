#!/usr/bin/env python3
"""Set uci.printersharing.config.webui via /modals/printersharing-modal.lp, then re-check CUPS :631.

Only `printersharing_webui` changes. `printersharing_enabled` is re-sent at the value passed
in `--enabled`, which the operator must read from the device first (the script does not
parse it, so it cannot verify the value itself). Evidence goes to a timestamped folder under
artifacts/ (private, not committed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from f1_secrets import read_password_file, validate_router_base
from f1_session_store import ensure_admin_session, refresh_csrf_from_modal

MODAL = "/modals/printersharing-modal.lp"
ROOT = Path(__file__).resolve().parent.parent


def fetch(url: str, timeout: float = 10.0) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def build_post_fields(enabled: str, webui: str, csrf: str) -> dict[str, str]:
    """Form fields for the modal POST. `enabled` must be the device's current Enabled value."""
    if enabled not in ("0", "1") or webui not in ("0", "1"):
        raise ValueError("enabled and webui must be '0' or '1'")
    fields = {"printersharing_enabled": enabled, "printersharing_webui": webui}
    if csrf:
        fields["CSRFtoken"] = csrf
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://192.168.1.1")
    parser.add_argument("--password-file", type=Path, default=ROOT / "artifacts/secrets/f1-admin.password")
    parser.add_argument("--value", choices=["0", "1"], required=True, help="webui value to post")
    parser.add_argument(
        "--enabled",
        choices=["0", "1"],
        required=True,
        help="current printersharing_enabled value, read from the device beforehand (re-sent unchanged)",
    )
    parser.add_argument("--dry-run", action="store_true", help="login + CSRF only, no POST")
    args = parser.parse_args()

    base = validate_router_base(args.base)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "artifacts" / "management" / f"printersharing-webui-{args.value}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    record: dict = {"base": base, "value": args.value, "enabled": args.enabled, "dry_run": args.dry_run}

    cups_url = f"http://{urllib.parse.urlparse(base).hostname}:631/"
    code, body = fetch(cups_url)
    record["cups_before"] = {"status": code, "bytes": len(body)}

    password = read_password_file(args.password_file)
    try:
        client, how = ensure_admin_session(password, base=base)
    except RuntimeError as err:
        print(json.dumps({"error": str(err)}))
        return 2
    del password
    record["session"] = how
    # Carry the saved session cookie: a cookie-less request takes a session slot (per-IP cap 10).
    code, _ = client._open(client.base + "/login.lp", None, "GET")
    record["login_lp"] = code
    if code != 200:
        print(json.dumps({"error": "login_lp_not_200", "status": code}))
        return 2
    # This modal serves no CSRF token (checked 2026-10-29), so the POST carries none unless one is found.
    try:
        refresh_csrf_from_modal(client, MODAL)
        record["csrf"] = "found"
    except RuntimeError:
        client.csrf = ""
        record["csrf"] = "absent"

    fields = build_post_fields(args.enabled, args.value, client.csrf)
    if args.dry_run:
        record["would_post"] = {k: v for k, v in fields.items() if k != "CSRFtoken"}
        print(json.dumps(record, indent=2))
        (out / "record.json").write_text(json.dumps(record, indent=2))
        return 0

    data = urllib.parse.urlencode(fields).encode()
    try:
        code, resp = client._open(client.base + MODAL, data, "POST")
    except urllib.error.HTTPError as err:
        code, resp = err.code, err.read()
    record["post"] = {"status": code, "bytes": len(resp), "preview": resp[:300].decode("utf-8", "replace")}

    time.sleep(5)
    code, body = fetch(cups_url)
    record["cups_after"] = {"status": code, "bytes": len(body), "preview": body[:200].decode("utf-8", "replace")}

    (out / "record.json").write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
