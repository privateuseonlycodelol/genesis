#!/usr/bin/env python3
"""Normal authenticated F1 read/export controls; no settings or upgrade actions.

Password is read from the terminal without echo. Private responses and cookies
are stored under ignored artifacts with restrictive permissions. Output is
metadata only. Export is optional because it may create temporary server state.
"""
import argparse
import getpass
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


class StopProbe(RuntimeError):
    pass


class ControlClient(SRPClient):
    def __init__(self, directory):
        super().__init__(str(directory / "cookies.txt"), "http://192.168.2.1")
        self.directory = directory
        self.index = 0
        self.rows = []

    def _open(self, url, data=None, method="GET"):
        if self.index:
            time.sleep(2)
        self.index += 1
        try:
            code, body = super()._open(url, data, method)
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        path = urllib.parse.urlsplit(url).path
        query = urllib.parse.urlsplit(url).query
        action = urllib.parse.parse_qs(query).get("action", [None])[0]
        if data is not None:
            action = urllib.parse.parse_qs(data.decode()).get("action", [action])[0]
        login = bool(re.search(rb'id\s*=\s*[\"\']sign-me-in[\"\']', body, re.I))
        keys = []
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                allowed = {"current_role", "success", "banksize", "s", "B", "M", "errorcode"}
                keys = sorted(k if k in allowed else "<redacted>" for k in parsed)
        except (ValueError, UnicodeError):
            pass
        row = {"request": self.index, "method": method, "path": path,
               "action": action, "status": code, "bytes": len(body),
               "login_marker": login, "json_keys": keys,
               "sha256": hashlib.sha256(body).hexdigest()}
        self.rows.append(row)
        (self.directory / f"response-{self.index:02d}.private").write_bytes(body)
        (self.directory / "summary.json").write_text(json.dumps(self.rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if code == 503:
            raise StopProbe("HTTP 503: stopped immediately")
        return code, body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true", help="try normal configuration export after valid session control")
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / ("readonly-control-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    client = ControlClient(directory)
    try:
        code, body = client._open(client.base + "/login.lp")
        if code != 200:
            raise StopProbe("Login page failed")
        match = re.search(rb'CSRFtoken[\"\']\s+content\s*=\s*[\"\']([^\"\']+)', body, re.I)
        if not match:
            raise StopProbe("CSRF meta not found")
        client.csrf = match.group(1).decode()
        password = getpass.getpass("Router password (not echoed): ")
        code, result = client.login("User", password)
        del password
        if code != 200 or result != "ok":
            raise StopProbe("Normal SRP login did not verify; stopped")
        code, body = client._open(client.base + "/gateway.lp")
        if code != 200 or client.rows[-1]["login_marker"]:
            raise StopProbe("Base authenticated page control failed")
        match = re.search(rb'CSRFtoken[\"\']\s+content\s*=\s*[\"\']([^\"\']+)', body, re.I)
        if not match:
            raise StopProbe("Authenticated-page CSRF meta not found")
        # Normal login can rotate the token. Never export with the login-page token.
        client.csrf = match.group(1).decode()
        code, body = client._open(client.base + "/gateway.lp?auto_update=true&getSessionStatus=true")
        try:
            role = json.loads(body).get("current_role")
        except (ValueError, AttributeError):
            role = None
        if code != 200 or role != "admin":
            raise StopProbe("Authenticated admin-session control failed")
        code, body = client._open(client.base + "/modals/system-config-modal.lp?action=getbanksize")
        try:
            metadata = json.loads(body)
            bank_size = int(metadata.get("banksize", 0))
            bank_ok = metadata.get("success") in (True, "true") and bank_size > 0
        except (ValueError, TypeError, AttributeError):
            bank_ok = False
        if code != 200 or not bank_ok:
            raise StopProbe("Bank-size metadata was not verified; stopped before export")
        if args.export:
            data = urllib.parse.urlencode({"action": "export_config", "CSRFtoken": client.csrf}).encode()
            code, body = client._open(client.base + "/modals/system-config-modal.lp", data, "POST")
            boundary = body.find(b"\n\n", 0, 4096)
            header = body[:boundary].splitlines() if boundary >= 0 else []
            # Recognize only the observed outer envelope. This is not a
            # cryptographic authenticity or decrypted-content check.
            envelope_ok = (len(header) >= 2 and all(b"=" in line for line in header)
                           and boundary >= 0 and len(body) - boundary - 2 >= 52
                           and (len(body) - boundary - 2 - 36) % 16 == 0)
            if code != 200 or client.rows[-1]["login_marker"] or not envelope_ok:
                raise StopProbe("Export did not return the observed binary envelope; response preserved privately")
        print("Completed normal read controls; private artifacts: " + str(directory), flush=True)
        return 0
    except (StopProbe, urllib.error.URLError, TimeoutError) as error:
        # Do not include raw exception bodies or auth responses.
        print("Stopped: " + (str(error) if isinstance(error, StopProbe) else type(error).__name__), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
