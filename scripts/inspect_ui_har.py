#!/usr/bin/env python3
"""Print a sanitized, metadata-only summary of a browser HAR file.

The output intentionally excludes hosts, arbitrary query parameters, headers,
cookies, request-body values, response text, and JSON values. It reports only
exact allowlisted paths/actions, a coarse request-body class, CSRF-field/header
presence, response markers, sizes, and allowlisted JSON key names.
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
    "lastaccess",
    "redirect",
}
ALLOWED_BODY_ACTIONS = {
    "export_config",
    "import_config",
    "schedulerebootset",
    "system_bootp",
    "system_reboot",
    "upgradefw",
    "languageChanged",
    "lastaccess",
    "redirect",
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
    "/password.lp",
    "/home.lp",
    "/authenticate",
    "/modals/basicview-accesscode-modal.lp",
    "/modals/broadband-modal.lp",
    "/modals/contentsharing-modal.lp",
    "/modals/device-modal.lp",
    "/modals/diagnostics-connection-modal.lp",
    "/modals/diagnostics-igmpproxy-modal.lp",
    "/modals/diagnostics-network-modal.lp",
    "/modals/diagnostics-ping-modal.lp",
    "/modals/dmz-modal.lp",
    "/modals/dyndns-wanservices-modal.lp",
    "/modals/ethernet-modal.lp",
    "/modals/firewall-modal.lp",
    "/modals/internet-modal.lp",
    "/modals/l2tp-ipsec-server-modal.lp",
    "/modals/logviewer-modal.lp",
    "/modals/parental-modal.lp",
    "/modals/system-config-modal.lp",
    "/modals/system-info-modal.lp",
    "/modals/time-management-modal.lp",
    "/modals/tod-modal.lp",
    "/modals/wanservices-modal.lp",
    "/modals/wireless-ap-modal-newEM.lp",
    "/modals/wireless-radio-modal-newEM.lp",
    "/modals/wireless-wps-modal-newEM.lp",
    "/js/004_wireless.js",
    "/js/asmcrypto-min.js",
    "/js/chart-min.js",
    "/js/device-min.js",
    "/js/dmz-modal-min.js",
    "/js/ethernet-min.js",
    "/js/firewall-min.js",
    "/js/gateway.js",
    "/js/internet-dns-min.js",
    "/js/internet-routed-settings-min.js",
    "/js/logviewer-min.js",
    "/js/media-min.js",
    "/js/password.js",
    "/js/system-config-min.js",
    "/js/tod-modal-min.js",
    "/js/wanservices-min.js",
    "/js/wireless-ap-modal-newEM.js",
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


def header_presence(headers: object, accepted_names: set[str]) -> bool:
    """Check only header names; never return or inspect their values."""
    if not isinstance(headers, list):
        return False
    return any(
        isinstance(header, dict)
        and isinstance(header.get("name"), str)
        and header["name"].lower() in accepted_names
        for header in headers
    )


def request_body_metadata(request: object) -> tuple[str, str, bool]:
    """Return body class, allowlisted action marker, and CSRF-field presence."""
    if not isinstance(request, dict):
        return "none", "", False
    post_data = request.get("postData")
    if not isinstance(post_data, dict):
        return "none", "", False

    raw_mime = post_data.get("mimeType")
    mime = raw_mime.split(";", 1)[0].strip().lower() if isinstance(raw_mime, str) else ""
    if mime == "application/x-www-form-urlencoded":
        body_class = "form"
    elif mime == "multipart/form-data":
        body_class = "multipart"
    elif mime == "application/json":
        body_class = "json"
    else:
        body_class = "other"

    pairs: list[tuple[object, object]] = []
    params = post_data.get("params")
    if isinstance(params, list):
        for item in params:
            if isinstance(item, dict):
                pairs.append((item.get("name"), item.get("value")))
    text = post_data.get("text")
    if isinstance(text, str) and mime == "application/x-www-form-urlencoded":
        from urllib.parse import parse_qsl
        pairs.extend(parse_qsl(text, keep_blank_values=True))
    elif isinstance(text, str) and mime == "application/json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            pairs.extend(obj.items())

    csrf_present = any(
        isinstance(name, str) and name.lower() in {"csrftoken", "csrf_token"}
        for name, _ in pairs
    )
    actions = {
        value
        for name, value in pairs
        if isinstance(name, str)
        and name.lower() == "action"
        and isinstance(value, str)
    }
    if not actions:
        action = ""
    elif len(actions) == 1:
        value = next(iter(actions))
        action = value if value in ALLOWED_BODY_ACTIONS else "<redacted>"
    else:
        action = "<multiple>"
    return body_class, action, csrf_present


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

    body_class, post_action, body_csrf_present = request_body_metadata(request)
    request_headers = request.get("headers")
    response_headers = response.get("headers")

    return {
        "path": safe_path(request.get("url")),
        "method": method,
        "status": status,
        "mime": mime_type(content),
        "response_size": response_size(content, body),
        "login_markers": sorted(login_markers(body)),
        "json_top_level_keys": top_level_json_keys(body),
        "request_body_class": body_class,
        "request_action": post_action,
        "request_body_csrf_present": body_csrf_present,
        "request_csrf_header_present": header_presence(
            request_headers, {"csrf", "csrftoken", "x-csrf-token", "x-csrftoken"}
        ),
        "request_cookie_header_present": header_presence(request_headers, {"cookie"}),
        "response_set_cookie_header_present": header_presence(response_headers, {"set-cookie"}),
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

    for index, entry in enumerate(entries, start=1):
        summary = summarize_entry(entry)
        summary["index"] = index
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
