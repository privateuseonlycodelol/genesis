#!/usr/bin/env python3
"""Paced GET probes on TCP 8080 — fixed path list, no discovery flood."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
PORT = 8080
GAP = 2.0

PATHS = [
    "/",
    "/login.lp",
    "/gateway.lp",
    "/home.lp",
    "/api",
    "/api/v1",
    "/error.lp",
    "/modals/system-config-modal.lp",
    "/modals/system-config-modal.lp?action=getbanksize",
    "/authenticate",
    "/favicon.ico",
]


def classify(body: bytes) -> dict:
    return {
        "login_marker": bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I)),
        "nginx_404": b"404 Not Found" in body or b"<center>nginx" in body,
        "html": bool(re.search(rb"<(?:!doctype|html)\b", body, re.I)),
    }


def main() -> None:
    os.umask(0o077)
    out_dir = ROOT / "artifacts" / "management" / time.strftime("port8080-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, path in enumerate(PATHS, 1):
        if index > 1:
            time.sleep(GAP)
        prefix = out_dir / f"response-{index:02d}"
        cmd = [
            "curl", "--noproxy", "*", "--silent", "--show-error",
            "--connect-timeout", "4", "--max-time", "12", "--max-filesize", "1048576",
            "--dump-header", str(prefix) + ".headers.private",
            "--output", str(prefix) + ".body.private",
            "--write-out", "%{http_code}",
            f"http://{HOST}:{PORT}{path}",
        ]
        completed = subprocess.run(cmd, capture_output=True)
        body_path = Path(str(prefix) + ".body.private")
        body = body_path.read_bytes() if body_path.exists() else b""
        status = int((completed.stdout or b"0").strip() or 0)
        rows.append({
            "path": path,
            "status": status,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            **classify(body),
        })
    (out_dir / "summary.json").write_text(json.dumps({"rows": rows}, indent=2) + "\n")
    print(json.dumps({"rows": rows}, indent=2))


if __name__ == "__main__":
    main()
