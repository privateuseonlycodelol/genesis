#!/usr/bin/env python3
"""Bounded LAN probe for USP/CWMP reachability and IPPing.Host bypass hypothesis.

Does not impersonate the ISP ACS. Checks TCP listeners, minimal CWMP SOAP on 7547,
authenticated Homeware paths, and whether obuspa_retriever leaves a log fingerprint.
If no management Set path exists, records BLOCKED and does not spray ping payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from f1_ipping_control import LOG_PATH, StopProbe, _csrf, _login_page, parse_log_rows
from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
TCP_PORTS = (
    7547,
    7557,
    7577,
    1883,
    8883,
    5683,
    61613,
    61614,
    443,
    8443,
)
HTTP_PATHS = (
    "/usp",
    "/USP",
    "/cwmp",
    "/tr069",
    "/obuspa",
    "/agent/usp",
    "/mqtt",
    "/modals/gateway-modal.lp",
)
CWMP_SOAP = (
    b'<?xml version="1.0"?>\n'
    b'<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" '
    b'xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" '
    b'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    b'xmlns:cwmp="urn:dslforum-org:cwmp-1-0">\n'
    b"<soap-env:Body><cwmp:GetRPCMethods/></soap-env:Body></soap-env:Envelope>"
)
OBUSPA_MARK = "obuspa_retriever"
IPPING_MARKERS = ("IPPing", "diagping", "uci.ipping", "Device.IP.Diagnostics")


def tcp_state(port: int, timeout: float = 2.0) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((HOST, port))
        return "open"
    except (TimeoutError, OSError):
        return "closed"
    finally:
        sock.close()


def cwmp_probe() -> dict:
    out = {"port": 7547, "state": tcp_state(7547)}
    if out["state"] != "open":
        out["soap"] = "skipped"
        return out
    req = urllib.request.Request(
        f"http://{HOST}:7547/",
        data=CWMP_SOAP,
        method="POST",
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(4096)
            out["soap"] = {
                "status": resp.status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
    except urllib.error.HTTPError as error:
        body = error.read(512)
        out["soap"] = {
            "status": error.code,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    except urllib.error.URLError as error:
        out["soap"] = {"error": error.reason.__class__.__name__}
    return out


def _login_client(directory: Path, password: str) -> SRPClient:
    wait_login_ready(900)
    client = SRPClient(str(directory / "cookies.txt"), f"http://{HOST}")
    for attempt in range(8):
        if attempt:
            time.sleep(45)
            wait_login_ready(180)
        try:
            code, body = client._open(client.base + "/login.lp")
        except urllib.error.HTTPError as error:
            if error.code == 503:
                continue
            raise StopProbe(f"login.lp HTTP {error.code}") from error
        if code == 503:
            continue
        if code != 200:
            raise StopProbe("Login page failed")
        client.csrf = _csrf(body)
        code, result = client.login("User", password)
        if code != 200 or result != "ok":
            raise StopProbe("SRP login failed")
        code, body = client._open(client.base + "/gateway.lp")
        if code == 503:
            continue
        if code != 200 or _login_page(body):
            raise StopProbe("Gateway session failed")
        client.csrf = _csrf(body)
        del password
        return client
    raise StopProbe("Could not complete login through nginx cooldown")


def _get(client: SRPClient, path: str) -> tuple[int, bytes]:
    try:
        return client._open(client.base + path)
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def log_snapshot(client: SRPClient) -> dict:
    code, body = _get(client, LOG_PATH)
    if code != 200 or _login_page(body):
        raise StopProbe("Log read failed")
    text = body.decode("utf-8", "replace")
    rows = parse_log_rows(text)
    obuspa = [r for r in rows if OBUSPA_MARK in r["message"]]
    ipping = [r for r in rows if "ipping" in r["message"].lower()]
    return {
        "row_count": len(rows),
        "obuspa_rows": len(obuspa),
        "ipping_rows": len(ipping),
        "latest_obuspa": obuspa[0]["date"] if obuspa else None,
    }


def scan_http_paths(client: SRPClient) -> list[dict]:
    rows = []
    for path in HTTP_PATHS:
        code, body = _get(client, path)
        text = body.decode("utf-8", "replace")
        hits = [m for m in IPPING_MARKERS if m in text]
        rows.append(
            {
                "path": path,
                "status": code,
                "bytes": len(body),
                "login_marker": _login_page(body),
                "marker_hits": hits,
            }
        )
    return rows


def wait_login_ready(max_wait: int = 900) -> None:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://{HOST}/login.lp", timeout=15) as resp:
                body = resp.read()
            if resp.status == 200 and len(body) > 500 and b"sign-me-in" in body:
                return
        except urllib.error.HTTPError as error:
            if error.code != 503:
                raise StopProbe(f"login.lp HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise StopProbe(str(error.reason)) from error
        time.sleep(30)
    raise StopProbe("login.lp still unavailable after wait")


def run(password: str, wait_obuspa: int, login_wait: int) -> dict:
    outcome = {
        "tcp": {str(p): tcp_state(p) for p in TCP_PORTS},
        "cwmp": cwmp_probe(),
        "http_paths": [],
        "log_before": None,
        "log_after_wait": None,
        "conclusion": None,
    }
    wait_login_ready(login_wait)
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "usp-ipping-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    client = _login_client(directory, password)
    outcome["http_paths"] = scan_http_paths(client)
    outcome["log_before"] = log_snapshot(client)
    if wait_obuspa > 0:
        time.sleep(wait_obuspa)
        outcome["log_after_wait"] = log_snapshot(client)
    open_ports = [p for p, st in outcome["tcp"].items() if st == "open"]
    if "7547" not in open_ports and outcome["cwmp"]["state"] != "open":
        outcome["conclusion"] = (
            "LAN CWMP/USP transports closed; no local Set path for IPPing.Host was exercised"
        )
    else:
        outcome["conclusion"] = "unexpected open management port; inspect artifacts"
    (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument(
        "--wait-obuspa",
        type=int,
        default=65,
        help="Seconds to wait for cron obuspa_retriever (0 to skip)",
    )
    parser.add_argument(
        "--login-wait",
        type=int,
        default=900,
        help="Max seconds to poll for login.lp HTTP 200 before giving up",
    )
    args = parser.parse_args()
    try:
        password = args.password_file.read_text().strip("\n")
        outcome = run(password, args.wait_obuspa, args.login_wait)
        print(
            json.dumps(
                {"conclusion": outcome["conclusion"], "tcp_open": [p for p, s in outcome["tcp"].items() if s == "open"]}
            ),
            flush=True,
        )
        return 0
    except (StopProbe, urllib.error.URLError, TimeoutError) as error:
        print("Stopped:", error, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
