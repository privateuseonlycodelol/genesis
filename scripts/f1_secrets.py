"""Shared secret and router-target guards for F1 lab scripts."""
from __future__ import annotations

import ipaddress
import os
import stat
import urllib.parse
from pathlib import Path

DEFAULT_ROUTER_BASE = "http://192.168.2.1"


def _allow_remote_base() -> bool:
    return os.environ.get("F1_ALLOW_REMOTE_BASE", "").lower() in ("1", "true", "yes")


def _host_allowed(host: str | None) -> bool:
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        addr = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def validate_router_base(base: str, allow_remote: bool | None = None) -> str:
    """Return normalized base URL; refuse non-LAN targets unless explicitly allowed."""
    base = base.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"invalid router base URL: {base}")
    remote = allow_remote if allow_remote is not None else _allow_remote_base()
    if not remote and not _host_allowed(parsed.hostname):
        raise ValueError(
            f"router base must be a private/LAN address (got {base!r}); "
            "set F1_ALLOW_REMOTE_BASE=1 to override"
        )
    return base


def read_password_file(path: Path | str) -> str:
    """Read admin password from a file that must not be group/world accessible."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"password file not found: {path}")
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(
            f"password file must be mode 0600 (no group/other access): {path}"
        )
    return path.read_text(encoding="utf-8").strip("\n")
