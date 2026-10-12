#!/usr/bin/env python3
"""Fixed, paced GET-only boundary controls against the owned F1.

No path discovery, redirects, login attempts, settings, or provisioning actions.
Raw responses and cookie jars stay in ignored artifacts with private permissions.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
STATUS = "/gateway.lp?auto_update=true&getSessionStatus=true"
BANK = "/modals/system-config-modal.lp?action=getbanksize"


def classify(body):
    result = {"login_marker": bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I)),
              "html": bool(re.search(rb'<(?:!doctype|html)\b', body, re.I))}
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError):
        value = None
    result["json_object"] = isinstance(value, dict)
    if isinstance(value, dict):
        if value.get("current_role") in ("admin", "guest", "user", "anonymous"):
            result["current_role"] = value["current_role"]
        result["bank_metadata"] = (value.get("success") in (True, "true")
                                   and value.get("banksize") == "134217728")
    return result


def main():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    directory.mkdir(parents=True, exist_ok=False)
    old = ROOT / "artifacts/ui/readonly-control-20261012T021317Z/cookies.txt"
    saved = directory / "saved.cookies.txt"
    if old.exists():
        shutil.copyfile(old, saved)
    anonymous = directory / "anonymous.cookies.txt"
    cases = [(80, "/login.lp", "fresh-anonymous"),
             (80, STATUS, "none"), (80, BANK, "none"),
             (80, STATUS, "fresh-anonymous"), (80, BANK, "fresh-anonymous"),
             (80, BANK, "invalid")]
    if saved.exists():
        cases.append((80, STATUS, "saved-session-control"))
    cases.extend([(8080, "/", "none"), (8080, "/login.lp", "none"),
                  (8080, BANK, "none"), (631, "/", "none"),
                  (631, "/admin/", "none"), (631, "/printers/", "none")])
    rows = []
    for index, (port, path, state) in enumerate(cases, 1):
        if index > 1:
            time.sleep(3)
        prefix = directory / f"response-{index:02d}"
        command = ["curl", "--noproxy", "*", "--silent", "--show-error",
                   "--connect-timeout", "4", "--max-time", "12", "--max-filesize", "1048576",
                   "--dump-header", str(prefix) + ".headers.private",
                   "--output", str(prefix) + ".body.private", "--write-out", "%{http_code}"]
        if state == "fresh-anonymous":
            command += ["--cookie", str(anonymous), "--cookie-jar", str(anonymous)]
        elif state == "invalid":
            command += ["--cookie", "sessionID=00000000000000000000000000000000"]
        elif state == "saved-session-control":
            command += ["--cookie", str(saved)]
        command.append(f"http://{HOST}:{port}{path}")
        completed = subprocess.run(command, capture_output=True)
        body_path = Path(str(prefix) + ".body.private")
        header_path = Path(str(prefix) + ".headers.private")
        body = body_path.read_bytes() if body_path.exists() else b""
        headers = header_path.read_bytes() if header_path.exists() else b""
        status = int(completed.stdout.strip() or b"0")
        row = {"request": index, "port": port, "path": path, "cookie_state": state,
               "curl_exit": completed.returncode, "status": status, "bytes": len(body),
               "sha256": hashlib.sha256(body).hexdigest(), **classify(body),
               "auth_challenge": bool(re.search(rb'^WWW-Authenticate:', headers, re.M | re.I)),
               "redirect": bool(re.search(rb'^Location:', headers, re.M | re.I))}
        rows.append(row)
        (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if completed.returncode or status == 503:
            print("Stopped on transport error or HTTP 503; private evidence: " + str(directory))
            return 1
    print("Completed fixed GET controls; private evidence: " + str(directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
