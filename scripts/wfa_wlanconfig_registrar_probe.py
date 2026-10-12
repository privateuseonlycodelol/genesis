#!/usr/bin/env python3
"""SetSelectedRegistrar after SUBSCRIBE with a live CALLBACK listener.

One SUBSCRIBE, one SetSelectedRegistrar with a one-byte NewMessage, optional
UNSUBSCRIBE. No GetDeviceInfo or WPS continuation.
"""
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wfa_wlanconfig_event_probe as event_probe
import wfa_wlanconfig_probe as surface

SERVICE = surface.SERVICE
CONTROL = event_probe.CONTROL
EVENT_PATH = event_probe.EVENT_PATH
CALLBACK_PORT = event_probe.CALLBACK_PORT


class _NotifySink(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_NOTIFY(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.end_headers()


def live():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / (
        "wfa-er-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    lan_ip = event_probe.local_lan_ip()
    callback = f"<http://{lan_ip}:{CALLBACK_PORT}/wfa-er-notify>"
    httpd = HTTPServer(("0.0.0.0", CALLBACK_PORT), _NotifySink)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    rows = []

    summary, exit_code, status, header_blob = event_probe.curl_raw(
        directory,
        1,
        "SUBSCRIBE",
        "listener on CALLBACK port",
        "SUBSCRIBE",
        EVENT_PATH,
        ["NT: upnp:event", "CALLBACK: " + callback, "Host: 192.168.2.1:49152"],
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status != 200:
        httpd.shutdown()
        return 1, directory

    sid_match = re.search(rb"^SID:\s*(uuid:[^\r]+)", header_blob, re.I | re.M)
    sid_value = sid_match.group(1).decode() if sid_match else None
    time.sleep(3)

    inner = (
        f'<u:SetSelectedRegistrar xmlns:u="{SERVICE}">'
        "<NewMessage>AA==</NewMessage></u:SetSelectedRegistrar>"
    )
    body_file = directory / "request-set-selected.private.xml"
    body_file.write_bytes(surface.soap_body("SetSelectedRegistrar", inner))
    summary, exit_code, status = surface.curl_step(
        directory,
        2,
        {
            "probe": "SetSelectedRegistrar-one-byte",
            "method": "POST",
            "url": CONTROL,
            "headers": (
                'Content-Type: text/xml; charset="utf-8"',
                f'SOAPAction: "{SERVICE}#SetSelectedRegistrar"',
            ),
            "body_file": body_file,
            "note": "after SUBSCRIBE with reachable CALLBACK",
        },
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)

    if sid_value:
        time.sleep(3)
        summary, exit_code, status, _ = event_probe.curl_raw(
            directory,
            3,
            "UNSUBSCRIBE",
            "best-effort cleanup",
            "UNSUBSCRIBE",
            EVENT_PATH,
            ["SID: " + sid_value, "Host: 192.168.2.1:49152"],
            False,
        )
        rows.append(summary)
        surface._write_summary(directory, rows)
        print(json.dumps(summary), flush=True)

    httpd.shutdown()
    print("Completed registrar probe; private evidence: " + str(directory), flush=True)
    return 0, directory


def main():
    return live()[0]


if __name__ == "__main__":
    raise SystemExit(main())
