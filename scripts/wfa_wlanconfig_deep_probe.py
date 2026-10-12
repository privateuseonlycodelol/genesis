#!/usr/bin/env python3
"""NOTIFY capture during SUBSCRIBE, then GetDeviceInfo + shell M2 PutMessage.

Runs on owned F1 :49152 only. One event subscription with a local CALLBACK
listener, then one WPS peer and one non-completing M2-shaped PutMessage.
No PIN, crypto completion, or persistent registrar role claim.
"""
import base64
import hashlib
import json
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wfa_wlanconfig_event_probe as event_probe
import wfa_wlanconfig_peer_probe as peer
import wfa_wlanconfig_probe as surface
import wps_device_info as wps

HOST = surface.HOST
PORT = surface.PORT
SERVICE = surface.SERVICE
EVENT_PATH = event_probe.EVENT_PATH
CALLBACK_PORT = event_probe.CALLBACK_PORT
PAUSE = 3


class NotifyCapture(BaseHTTPRequestHandler):
    server_version = "WfaNotifyCapture/1.0"
    store = []

    def log_message(self, *_args):
        return

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def do_NOTIFY(self):
        body = self._read_body()
        NotifyCapture.store.append(
            {
                "method": "NOTIFY",
                "path": self.path,
                "headers": {k: v for k, v in self.headers.items()},
                "body": body,
            }
        )
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        body = self._read_body()
        NotifyCapture.store.append(
            {
                "method": "POST",
                "path": self.path,
                "headers": {k: v for k, v in self.headers.items()},
                "body": body,
            }
        )
        self.send_response(200)
        self.end_headers()


def _out_message_type(soap_body):
    try:
        root = ET.fromstring(soap_body)
        for element in root.iter():
            if element.tag.split("}")[-1] != "NewOutMessage":
                continue
            payload = base64.b64decode("".join((element.text or "").split()), validate=True)
            offset = 0
            while offset < len(payload):
                kind, length = struct.unpack_from("!HH", payload, offset)
                offset += 4
                value = payload[offset : offset + length]
                offset += length
                if kind == 0x1022 and length == 1:
                    return value[0]
    except (ET.ParseError, ValueError, struct.error):
        return None
    return None


def shell_m2(enrollee_nonce, registrar_nonce=None):
    if registrar_nonce is None:
        registrar_nonce = bytes(16)
    if len(enrollee_nonce) != 16 or len(registrar_nonce) != 16:
        raise ValueError("nonces must be 16 bytes")
    return (
        peer.wps_tlv(0x104a, b"\x10")
        + peer.wps_tlv(0x1022, b"\x05")
        + peer.wps_tlv(0x101a, enrollee_nonce)
        + peer.wps_tlv(0x1039, registrar_nonce)
    )


def save_notify(directory, captures):
    rows = []
    for index, item in enumerate(captures, 1):
        body = item["body"]
        path = directory / f"notify-{index:02d}.body.private"
        path.write_bytes(body)
        headers_path = directory / f"notify-{index:02d}.headers.private"
        header_lines = [f"{k}: {v}" for k, v in item["headers"].items()]
        headers_path.write_text("\n".join(header_lines) + "\n")
        rows.append(
            {
                "notify": index,
                "http_method": item["method"],
                "path": item["path"],
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "content_type": item["headers"].get("Content-Type"),
                "nt": item["headers"].get("NT"),
                "sid_present": bool(item["headers"].get("SID")),
            }
        )
    return rows


def live():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / (
        "wfa-deep-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    index = 0
    lan_ip = event_probe.local_lan_ip()
    callback = f"<http://{lan_ip}:{CALLBACK_PORT}/wfa-upnp-notify>"

    NotifyCapture.store = []
    httpd = HTTPServer(("0.0.0.0", CALLBACK_PORT), NotifyCapture)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    index += 1
    summary, exit_code, status, header_blob = event_probe.curl_raw(
        directory,
        index,
        "SUBSCRIBE-with-listener",
        "expect immediate NOTIFY to CALLBACK",
        "SUBSCRIBE",
        EVENT_PATH,
        [
            "NT: upnp:event",
            "CALLBACK: " + callback,
            "Host: " + f"{HOST}:{PORT}",
        ],
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503 or status != 200:
        httpd.shutdown()
        return 1, directory

    sid_match = re.search(rb"^SID:\s*(uuid:[0-9a-f-]+)\r", header_blob, re.I | re.M)
    sid_value = sid_match.group(1).decode() if sid_match else None

    deadline = time.time() + 8
    while time.time() < deadline and not NotifyCapture.store:
        time.sleep(0.2)
    notify_rows = save_notify(directory, NotifyCapture.store)
    rows.append(
        {
            "request": "notify-wait",
            "probe": "CALLBACK-traffic",
            "notify_count": len(notify_rows),
            "notifies": notify_rows,
        }
    )
    surface._write_summary(directory, rows)
    print(json.dumps(rows[-1]), flush=True)

    if sid_value:
        time.sleep(PAUSE)
        index += 1
        summary, exit_code, status, _ = event_probe.curl_raw(
            directory,
            index,
            "UNSUBSCRIBE-cleanup",
            "after NOTIFY capture",
            "UNSUBSCRIBE",
            EVENT_PATH,
            ["SID: " + sid_value, "Host: " + f"{HOST}:{PORT}"],
            False,
        )
        rows.append(summary)
        surface._write_summary(directory, rows)
        print(json.dumps(summary), flush=True)
        if exit_code or status == 503:
            httpd.shutdown()
            return 1, directory

    httpd.shutdown()

    time.sleep(PAUSE)
    index += 1
    (directory / "request-get-device-info.private.xml").write_bytes(wps.SOAP)
    summary, exit_code, status = surface.curl_step(
        directory,
        index,
        {
            "probe": "GetDeviceInfo",
            "method": "POST",
            "url": f"http://{HOST}:{PORT}/wps_control",
            "headers": (
                'Content-Type: text/xml; charset="utf-8"',
                f'SOAPAction: "{SERVICE}#GetDeviceInfo"',
            ),
            "body_file": directory / "request-get-device-info.private.xml",
            "note": "fresh peer before shell M2 PutMessage",
        },
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503 or status != 200:
        return 1, directory

    body = (directory / f"response-{index:02d}.body.private").read_bytes()
    nonce = peer.enrollee_nonce_from_get_device_info(body)
    m2_shell = shell_m2(nonce)
    b64 = base64.b64encode(m2_shell).decode()
    inner = peer.put_message_inner(b64)

    time.sleep(PAUSE)
    index += 1
    summary, exit_code, status = peer.post_put_message(
        directory,
        index,
        "PutMessage-shell-M2-matched-nonce",
        "Version+M2 type+enrollee/registrar nonces only; no DH/crypto",
        inner,
        False,
    )
    summary["wps_in_bytes"] = len(m2_shell)
    summary["wps_in_sha256"] = hashlib.sha256(m2_shell).hexdigest()
    summary["enrollee_nonce_sha256"] = hashlib.sha256(nonce).hexdigest()
    out_type = _out_message_type((directory / f"response-{index:02d}.body.private").read_bytes())
    if out_type is not None:
        summary["out_message_type_byte"] = out_type
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    time.sleep(PAUSE)
    index += 1
    summary, exit_code, status = peer.post_put_message(
        directory,
        index,
        "PutMessage-no-peer-after-NACK",
        "one-byte control after shell M2 NACK response",
        peer.put_message_inner("AA=="),
        False,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    print("Completed deep WFA probe; private evidence: " + str(directory), flush=True)
    return 0, directory


def main():
    return live()[0]


if __name__ == "__main__":
    raise SystemExit(main())
