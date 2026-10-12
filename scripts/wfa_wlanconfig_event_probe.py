#!/usr/bin/env python3
"""UPnP event-plane probes for WFA WLANConfig on :49152.

One negative SUBSCRIBE, one SUBSCRIBE with a LAN callback URL (no listener),
one SetSelectedRegistrar negative, then UNSUBSCRIBE cleanup. Does not send
NOTIFY consumers, WPS messages, or GetDeviceInfo. SID values stay private.
"""
import hashlib
import json
import os
import re
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wfa_wlanconfig_probe as surface

HOST = surface.HOST
PORT = surface.PORT
SERVICE = surface.SERVICE
EVENT_PATH = f"http://{HOST}:{PORT}/wps_event"
CONTROL = f"http://{HOST}:{PORT}/wps_control"
CALLBACK_PORT = 19000


def local_lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((HOST, PORT))
        return sock.getsockname()[0]


def curl_raw(directory, index, probe, note, method, url, headers, pause):
    if pause:
        time.sleep(3)
    prefix = directory / f"response-{index:02d}"
    command = [
        "curl",
        "--noproxy",
        "*",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "4",
        "--max-time",
        "12",
        "--max-filesize",
        "1048576",
        "-X",
        method,
        "--dump-header",
        str(prefix) + ".headers.private",
        "--output",
        str(prefix) + ".body.private",
        "--write-out",
        "%{http_code}",
    ]
    for header in headers:
        command += ["--header", header]
    command.append(url)
    completed = __import__("subprocess").run(command, capture_output=True)
    body_path = Path(str(prefix) + ".body.private")
    header_path = Path(str(prefix) + ".headers.private")
    body = body_path.read_bytes() if body_path.exists() else b""
    headers_blob = header_path.read_bytes() if header_path.exists() else b""
    status = int(completed.stdout.strip() or b"0")
    summary = {
        "request": index,
        "probe": probe,
        "method": method,
        "url": url,
        "curl_exit": completed.returncode,
        "status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "auth_challenge": bool(re.search(rb"^WWW-Authenticate:", headers_blob, re.M | re.I)),
        "note": note,
    }
    sid = re.search(rb"^SID:\s*uuid:([0-9a-f-]+)", headers_blob, re.I | re.M)
    if sid:
        summary["sid_sha256"] = hashlib.sha256(sid.group(1)).hexdigest()
    if method == "POST" and body:
        summary.update(surface.classify_soap(body))
    return summary, completed.returncode, status, headers_blob


def live():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / (
        "wfa-event-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    lan_ip = local_lan_ip()
    callback = f"<http://{lan_ip}:{CALLBACK_PORT}/wfa-upnp-notify>"
    rows = []
    index = 0

    index += 1
    summary, exit_code, status, _ = curl_raw(
        directory,
        index,
        "SUBSCRIBE-missing-callback",
        "NT present, no CALLBACK (expect 412)",
        "SUBSCRIBE",
        EVENT_PATH,
        ["NT: upnp:event", "Host: " + f"{HOST}:{PORT}"],
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    index += 1
    summary, exit_code, status, header_blob = curl_raw(
        directory,
        index,
        "SUBSCRIBE-lan-callback",
        f"CALLBACK to unused high port on local LAN client ({CALLBACK_PORT})",
        "SUBSCRIBE",
        EVENT_PATH,
        [
            "NT: upnp:event",
            "CALLBACK: " + callback,
            "Host: " + f"{HOST}:{PORT}",
        ],
        True,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    sid_match = re.search(rb"^SID:\s*(uuid:[0-9a-f-]+)\r", header_blob, re.I | re.M)
    sid_value = sid_match.group(1).decode() if sid_match else None
    if status != 200 or not sid_value:
        print("SUBSCRIBE did not return SID; skipping registrar/unsubscribe follow-ups", flush=True)
        return 0, directory

    index += 1
    inner = (
        f'<u:SetSelectedRegistrar xmlns:u="{SERVICE}">'
        "<NewMessage></NewMessage></u:SetSelectedRegistrar>"
    )
    body_file = directory / "request-set-selected.private.xml"
    body_file.write_bytes(surface.soap_body("SetSelectedRegistrar", inner))
    summary, exit_code, status = surface.curl_step(
        directory,
        index,
        {
            "probe": "SetSelectedRegistrar-after-SUBSCRIBE",
            "method": "POST",
            "url": CONTROL,
            "headers": (
                'Content-Type: text/xml; charset="utf-8"',
                f'SOAPAction: "{SERVICE}#SetSelectedRegistrar"',
            ),
            "body_file": body_file,
            "note": "empty NewMessage; client now has event subscription",
        },
        True,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    index += 1
    summary, exit_code, status, _ = curl_raw(
        directory,
        index,
        "UNSUBSCRIBE-cleanup",
        "drop subscription created above",
        "UNSUBSCRIBE",
        EVENT_PATH,
        ["SID: " + sid_value, "Host: " + f"{HOST}:{PORT}"],
        True,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    print("Completed event-plane probe; private evidence: " + str(directory), flush=True)
    return 0, directory


def main():
    return live()[0]


if __name__ == "__main__":
    raise SystemExit(main())
