#!/usr/bin/env python3
"""Print a sanitized, metadata-only summary of a browser HAR file.

The output intentionally excludes hosts, arbitrary query parameters, headers,
cookies, request bodies, response text, and JSON values. Only allowlisted
``action`` query values are retained in paths.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl


ALLOWED_ACTIONS = {
    "scheduleReboot",
    "smartwifi",
    "upgradefwstatus",
    "getbanksize",
}
SAFE_MIME = re.compile(r"^[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+$")
KNOWN_PATHS = {
    "/",
    "/css/gw.css",
    "/css/responsive.css",
    "/js/main-min.js",
    "/js/jquery-eval-patch.js",
    "/js/srp-min.js",
    "/js/login.js",
    "/img/logo.png",
    "/font/fontawesome//fontawesome-webfont.woff",
    "/favicon.ico",
    "/gateway.lp",
    "/login.lp",
    "/authenticate",
    "/modals/parental-modal.lp",
    "/modals/system-config-modal.lp",
}
KNOWN_JSON_KEYS = {
    "B",
    "M",
    "s",
    "alertMsg",
    "banksize",
    "current_phase",
    "current_role",
    "current_state",
    "errorcode",
    "popupHeader",
    "rebootTime",
    "success",
    "systemTime",
}
KNOWN_MIMES = {
    "application/javascript",
    "application/json",
    "application/octet-stream",
    "font/woff",
    "image/png",
    "text/css",
    "text/html",
}


def safe_path(url: object) -> str:
    """Return an exact known path and only an allowlisted action query value."""
    if not isinstance(url, str):
        return "/"
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "/"

    # Exact known-route matching prevents short or oddly formatted IDs in a
    # path from leaking through a heuristic component scrubber.
    path = parsed.path if parsed.path in KNOWN_PATHS else "<redacted>"
    if path == "<redacted>":
        return path

    # Preserve only a small set of static action labels. All other query
    # fields, including auto_update/session parameters, are deliberately lost.
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "action" and value in ALLOWED_ACTIONS:
            path += "?action=" + value
            break
    return path


def response_bytes(content: object) -> bytes:
    if not isinstance(content, dict):
        return b""
    text = content.get("text")
    if not isinstance(text, str):
        return b""
    if content.get("encoding") == "base64":
        try:
            return base64.b64decode(text, validate=False)
        except (ValueError, base64.binascii.Error):
            return b""
    return text.encode("utf-8", errors="replace")


def mime_type(content: object) -> str:
    if not isinstance(content, dict):
        return ""
    raw = content.get("mimeType")
    if not isinstance(raw, str):
        return ""
    value = raw.split(";", 1)[0].strip()
    if value in KNOWN_MIMES and SAFE_MIME.fullmatch(value):
        return value
    return "other"


def response_size(content: object, body: bytes) -> int | None:
    if isinstance(content, dict):
        size = content.get("size")
        if isinstance(size, int) and size >= 0:
            return size
    return len(body) if body else None


def login_markers(body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="ignore").lower()
    markers = []
    if re.search(r"<form\b[^>]*\bid\s*=\s*['\"]login(?:-form)?['\"]", text):
        markers.append("login_form")
    if re.search(r"<form\b[^>]*\baction\s*=\s*['\"][^'\"]*authenticate", text):
        markers.append("authenticate_form")
    if re.search(r"<meta\b[^>]*\bname\s*=\s*['\"]csrftoken['\"]", text):
        markers.append("csrf_meta")
    if re.search(r"\bid\s*=\s*['\"]sign-me-in['\"]", text):
        markers.append("sign_me_in")
    return markers


def top_level_json_keys(body: bytes) -> list[str]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(value, dict):
        return []
    keys = []
    for key in value:
        if isinstance(key, str) and key in KNOWN_JSON_KEYS:
            keys.append(key)
        else:
            keys.append("<redacted>")
    return sorted(set(keys))


def summarize_entry(entry: object) -> dict[str, object]:
    entry = entry if isinstance(entry, dict) else {}
    request = entry.get("request")
    request = request if isinstance(request, dict) else {}
    response = entry.get("response")
    response = response if isinstance(response, dict) else {}
    content = response.get("content")
    content = content if isinstance(content, dict) else {}
    body = response_bytes(content)

    method = request.get("method")
    method = method.upper() if isinstance(method, str) else "OTHER"
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
        method = "OTHER"

    status = response.get("status")
    if not isinstance(status, int):
        status = None

    return {
        "path": safe_path(request.get("url")),
        "method": method,
        "status": status,
        "mime": mime_type(content),
        "response_size": response_size(content, body),
        "login_markers": sorted(login_markers(body)),
        "json_top_level_keys": top_level_json_keys(body),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("har", type=Path, help="HAR file to inspect")
    args = parser.parse_args()
    try:
        root = json.loads(args.har.read_text(encoding="utf-8"))
        entries = root["log"]["entries"]
        if not isinstance(entries, list):
            raise ValueError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        print("Could not read a valid HAR entry list.", file=sys.stderr)
        return 2

    for entry in entries:
        print(json.dumps(summarize_entry(entry), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
