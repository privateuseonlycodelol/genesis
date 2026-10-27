#!/usr/bin/env python3
"""Reuse Homeware admin session cookies across tool runs (browser-like jar).

SRP login runs only when the saved session is missing or no longer admin.
CSRF is refreshed from GET /gateway.lp (or a modal) on each ensure call — tokens
rotate and must not be cached across long periods.

Jar path default: artifacts/secrets/f1-admin.cookies.txt (gitignored, mode 0600).
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
from pathlib import Path

from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JAR = ROOT / "artifacts" / "secrets" / "f1-admin.cookies.txt"
STATUS_PATH = "/gateway.lp?auto_update=true&getSessionStatus=true"


def login_marker(body: bytes) -> bool:
    return bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I))


def csrf_from(html: bytes) -> str:
    m = re.search(rb'CSRFtoken"\s+content\s*=\s*"([^"]+)"', html, re.I)
    if not m:
        raise RuntimeError("csrf_missing")
    return m.group(1).decode()


def _fix_session_cookies(jar) -> None:
    for cookie in jar:
        if cookie.expires == 0:
            cookie.expires = None
            cookie.discard = True


def load_jar(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        os.chmod(path, 0o600)


def ensure_admin_session(
    password: str,
    jar_path: Path | None = None,
    username: str = "User",
    base: str = "http://192.168.2.1",
) -> tuple[SRPClient, str]:
    """Return (client, how) where how is 'reused' or 'srp_login'."""
    jar_path = jar_path or DEFAULT_JAR
    load_jar(jar_path)
    client = SRPClient(str(jar_path), base)
    _fix_session_cookies(client.jar)

    try:
        code, body = client._open(client.base + STATUS_PATH)
        if code == 200 and not login_marker(body):
            role = json.loads(body.decode()).get("current_role")
            if role == "admin":
                code, body = client._open(client.base + "/gateway.lp")
                if code == 200 and not login_marker(body):
                    client.csrf = csrf_from(body)
                    client.save_jar()
                    os.chmod(jar_path, 0o600)
                    return client, "reused"
    except (json.JSONDecodeError, OSError, RuntimeError, urllib.error.URLError):
        pass

    code, body = client._open(client.base + "/login.lp")
    if code != 200:
        raise RuntimeError(f"login_page_status_{code}")
    client.csrf = csrf_from(body)
    code, result = client.login(username, password)
    if code != 200 or result != "ok":
        raise RuntimeError(f"srp_failed_{code}")
    code, body = client._open(client.base + "/gateway.lp")
    if code != 200 or login_marker(body):
        raise RuntimeError("not_admin_after_login")
    client.csrf = csrf_from(body)
    client.save_jar()
    os.chmod(jar_path, 0o600)
    return client, "srp_login"


def refresh_csrf_from_modal(client: SRPClient, modal_path: str = "/modals/system-config-modal.lp") -> str:
    code, body = client._open(client.base + modal_path)
    if code != 200 or login_marker(body):
        raise RuntimeError("modal_not_authenticated")
    client.csrf = csrf_from(body)
    return client.csrf

