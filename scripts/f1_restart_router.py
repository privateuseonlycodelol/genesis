#!/usr/bin/env python3
"""Restart the F1 through its web UI, using the saved admin session or an SRP login.

Sends one POST with action=system_reboot to the system-config modal, which is the
request the UI's Restart button sends. Never sends system_softReset or a factory
reset. Refuses to send unless --yes is passed. Prints status codes and login
markers only, never response bodies or cookies.

Usage: f1_restart_router.py --base http://192.168.1.1 --yes
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
from pathlib import Path

from f1_secrets import read_password_file
from f1_session_store import DEFAULT_JAR, csrf_from, ensure_admin_session, login_marker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PASSWORD_FILE = ROOT / "artifacts" / "secrets" / "f1-admin.password"
MODAL_PATH = "/modals/system-config-modal.lp"
RESTART_ACTION = "system_reboot"
FORBIDDEN_ACTIONS = frozenset({"system_softReset", "system_factory_reset", "system_reset"})


def build_restart_body(csrf: str) -> bytes:
    """Form body for the restart request. Refuses any action other than system_reboot."""
    if RESTART_ACTION in FORBIDDEN_ACTIONS or RESTART_ACTION != "system_reboot":
        raise ValueError("restart action must be system_reboot")
    return urllib.parse.urlencode({"action": RESTART_ACTION, "CSRFtoken": csrf}).encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://192.168.1.1", help="Router base URL")
    parser.add_argument("--password-file", default=str(DEFAULT_PASSWORD_FILE))
    parser.add_argument("--jar", default=str(DEFAULT_JAR))
    parser.add_argument("--username", default="User")
    parser.add_argument("--yes", action="store_true", help="Required. Confirms the restart is intended.")
    args = parser.parse_args()
    if not args.yes:
        print("refusing to restart without --yes", file=sys.stderr)
        return 2

    password = read_password_file(Path(args.password_file))
    client, how = ensure_admin_session(password, Path(args.jar), args.username, base=args.base)
    print(f"session: {how}")
    # The modal is an HTML fragment without the CSRF meta tag; read it from the full page.
    code, page = client._open(client.base + "/gateway.lp")
    if code != 200 or login_marker(page):
        raise RuntimeError("not_admin_before_restart")
    csrf = csrf_from(page)
    body = build_restart_body(csrf)
    try:
        code, resp = client._open(client.base + MODAL_PATH, body, "POST")
    except (urllib.error.URLError, ConnectionError, OSError) as exc:
        # A restart can drop the connection before a response arrives. That is expected.
        print(f"restart sent; connection ended: {type(exc).__name__}")
        return 0
    print(f"restart POST: HTTP {code}, login_marker={login_marker(resp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
