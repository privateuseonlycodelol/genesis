#!/usr/bin/env python3
"""Read-only LAN probes for config-key / RIP material via the Homeware UI surface.

Uses normal admin SRP login. Does not send reboot, reset, import, upload, or BOOTP.
Prints only path, status, size, sha256 prefix, and safe classification flags.
Bodies go to a private ignored directory.
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

from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://192.168.2.1"
GAP = 2.0
CONTROL = "gf1nosuchaction"

# Candidate GET surfaces (path only; query built separately).
PATHS = [
    "/gateway.lp",
    "/modals/system-config-modal.lp",
    "/modals/system-info-modal.lp",
    "/modals/logviewer-modal.lp",
    "/modals/gateway-modal.lp",
    "/home.lp",
    "/overview.lp",
    "/system.lp",
    "/api",
    "/api/v1",
    "/api/rip",
    "/api/config",
    "/ajax/wirelesscard.lua",
    "/ajax/rip.lua",
    "/ajax/config.lua",
    "/ajax/system.lua",
    "/ajax/debug.lua",
    "/proc/rip/0108",
    "/rip/0108",
    "/debug/rip",
    "/download/config.bin",
    "/config.bin",
    "/backup/config.bin",
]

ACTIONS = [
    "scheduleReboot",
    "getbanksize",
    "upgradefwstatus",
    "smartwifi",
    "lastaccess",
    "redirect",
    "URL",
    "export_config",
    "import_config",
    "backup",
    "backup_config",
    "download_config",
    "get_config",
    "config_export",
    "rip",
    "ripkey",
    "getrip",
    "getRipKey",
    "debug",
    "generate_debug",
    "techsupport",
    "support",
    "mtd",
    "eripv2",
    "random_key",
    "RANDOM_KEY_B",
    "0108",
    "CIPHERKEY",
    "GW",
]

TRAVERSAL_SUFFIXES = [
    "?action=..%2f..%2f..%2fproc%2frip%2f0108",
    "?action=....//....//proc/rip/0108",
    "/..%2f..%2f..%2fproc%2frip%2f0108",
]


def classify(body: bytes) -> dict[str, bool]:
    login = bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I))
    json_ok = False
    try:
        parsed = json.loads(body)
        json_ok = isinstance(parsed, (dict, list))
    except (ValueError, UnicodeDecodeError):
        pass
    thenc = body.startswith(b"PREAMBLE=THENC")
    rip_size = len(body) in (64, 32, 16, 48, 256)
    high_entropy = len(body) > 100 and len(set(body[:256])) > 200
    return {
        "login_form": login,
        "json": json_ok,
        "thenc_export": thenc,
        "suspicious_fixed_size": rip_size and not login and len(body) < 512,
        "high_entropy_small": high_entropy and len(body) < 4096,
    }


def build_requests() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for path in PATHS:
        out.append((path, "GET"))
    for path in ("/gateway.lp", "/modals/system-config-modal.lp", "/modals/gateway-modal.lp"):
        for action in ACTIONS:
            out.append((f"{path}?action={urllib.parse.quote(action)}", "GET"))
        out.append((f"{path}?action={CONTROL}", "GET"))
    for suffix in TRAVERSAL_SUFFIXES:
        out.append((f"/modals/system-config-modal.lp{suffix}", "GET"))
        out.append((f"/gateway.lp{suffix}", "GET"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    password = args.password_file.read_text().strip()
    os.umask(0o077)
    out_dir = ROOT / "artifacts" / "ui" / ("key-probe-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    out_dir.mkdir(parents=True, exist_ok=False)
    client = SRPClient(str(out_dir / "cookies.txt"), BASE)
    code, body = client._open(f"{BASE}/login.lp")
    if code != 200:
        raise SystemExit("login_page_failed")
    client.load_csrf(body.decode("utf-8", errors="replace"))
    code, result = client.login("User", password)
    if code != 200 or result != "ok":
        raise SystemExit("srp_login_failed")

    rows = []
    interesting = []
    for index, (url_path, method) in enumerate(build_requests(), start=1):
        if index > 1:
            time.sleep(GAP)
        try:
            code, body = client._open(BASE + url_path, method=method)
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        flags = classify(body)
        row = {
            "n": index,
            "path": url_path.split("?")[0],
            "action": urllib.parse.parse_qs(urllib.parse.urlsplit(url_path).query).get("action", [None])[0],
            "status": code,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            **flags,
        }
        rows.append(row)
        (out_dir / f"body-{index:03d}.private").write_bytes(body)
        if flags["thenc_export"] or (flags["suspicious_fixed_size"] and not flags["login_form"]):
            interesting.append(row)
        if code == 503:
            print(json.dumps({"error": "http_503", "at": index}))
            break
        if index % 25 == 0:
            print(json.dumps({"progress": index, "total": len(build_requests())}), flush=True)

    summary = {"total": len(rows), "interesting_count": len(interesting), "rows": rows}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"out_dir": str(out_dir), "interesting_count": len(interesting)}))
    for row in interesting:
        print(json.dumps({k: row[k] for k in ("n", "path", "action", "status", "bytes", "sha256", "thenc_export", "suspicious_fixed_size")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
