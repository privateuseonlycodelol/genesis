#!/usr/bin/env python3
"""Bounded WFA WLANConfig surface probes on the owned F1 (TCP 49152).

Performs one SSDP read (optional), description GETs, transport HEAD/GET checks,
and exactly three negative SOAP actions with no WPS continuation, PIN, registrar
setup, or event subscription. Does not call GetDeviceInfo (allocates peer state).
Raw bodies stay in ignored private artifacts; stdout is metadata only.
"""
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
PORT = 49152
SERVICE = "urn:schemas-wifialliance-org:service:WFAWLANConfig:1"
SOAP_ENV = (
    '<?xml version="1.0"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
    "<s:Body>{body}</s:Body></s:Envelope>"
)


def soap_body(action, inner):
    return SOAP_ENV.format(body=inner).encode()


NEGATIVE_ACTIONS = {
    "SetSelectedRegistrar": (
        f'<u:SetSelectedRegistrar xmlns:u="{SERVICE}">'
        "<NewMessage></NewMessage></u:SetSelectedRegistrar>",
        "unknown external registrar; empty NewMessage",
    ),
    "PutWLANResponse": (
        f'<u:PutWLANResponse xmlns:u="{SERVICE}">'
        "<NewMessage>AA==</NewMessage></u:PutWLANResponse>",
        "missing WLANEventType/MAC; one-byte NewMessage",
    ),
    "PutMessage": (
        f'<u:PutMessage xmlns:u="{SERVICE}">'
        "<NewInMessage>AA==</NewInMessage></u:PutMessage>",
        "unparseable one-byte WPS payload; no prior GetDeviceInfo",
    ),
}


def classify_soap(body):
    result = {"soap_fault": False, "upnp_error_code": None, "response_action": None}
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        result["parse_error"] = True
        return result
    for element in root.iter():
        name = element.tag.split("}")[-1]
        if name == "Fault":
            result["soap_fault"] = True
        if name == "errorCode" and (element.text or "").isdigit():
            result["upnp_error_code"] = int(element.text)
        if name.endswith("Response") and name != "Fault":
            result["response_action"] = name
    return result


def ssdp_location(host):
    payload = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {host}:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        "ST: upnp:rootdevice\r\n"
        "\r\n"
    ).encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(4)
        sock.sendto(payload, (host, 1900))
        data = sock.recv(65535)
    match = re.search(rb"^LOCATION:\s*(.+?)\r", data, re.I | re.M)
    if not match:
        raise RuntimeError("SSDP response lacked LOCATION")
    location = match.group(1).decode().strip()
    parts = urllib.parse.urlsplit(location)
    if parts.scheme != "http" or parts.hostname != host or parts.port != PORT:
        raise RuntimeError("SSDP LOCATION host/port mismatch")
    return location


def curl_step(directory, index, row, pause):
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
        "--dump-header",
        str(prefix) + ".headers.private",
        "--output",
        str(prefix) + ".body.private",
        "--write-out",
        "%{http_code}",
    ]
    method = row.get("method", "GET")
    if method != "GET":
        command += ["-X", method]
    for header in row.get("headers", ()):
        command += ["--header", header]
    if row.get("body_file"):
        command += ["--data-binary", "@" + str(row["body_file"])]
    elif row.get("body"):
        command += ["--data-binary", row["body"]]
    command.append(row["url"])
    completed = subprocess.run(command, capture_output=True)
    body_path = Path(str(prefix) + ".body.private")
    header_path = Path(str(prefix) + ".headers.private")
    body = body_path.read_bytes() if body_path.exists() else b""
    headers = header_path.read_bytes() if header_path.exists() else b""
    status = int(completed.stdout.strip() or b"0")
    summary = {
        "request": index,
        "probe": row["probe"],
        "method": method,
        "url": row["url"],
        "curl_exit": completed.returncode,
        "status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "auth_challenge": bool(re.search(rb"^WWW-Authenticate:", headers, re.M | re.I)),
        "content_type": _header_value(headers, b"content-type"),
    }
    if row.get("note"):
        summary["note"] = row["note"]
    if method == "POST" and body:
        summary.update(classify_soap(body))
    if row.get("expect_scpd"):
        summary["scpd_valid"] = _scpd_valid(body)
    return summary, completed.returncode, status


def _header_value(headers, name):
    match = re.search(rb"^" + name + rb":\s*(.+?)\r", headers, re.I | re.M)
    return match.group(1).decode().strip() if match else None


def _scpd_valid(body):
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False
    if root.tag != "{urn:schemas-upnp-org:service-1-0}scpd":
        return False
    actions = set()
    for action in root.iter():
        if action.tag.split("}")[-1] != "action":
            continue
        for child in action:
            if child.tag.split("}")[-1] == "name" and child.text:
                actions.add(child.text.strip())
    return actions == {"GetDeviceInfo", "PutMessage", "PutWLANResponse", "SetSelectedRegistrar"}


def build_plan(location):
    base = f"http://{HOST}:{PORT}"
    device_url = location or f"{base}/wps_device.xml"
    return [
        {"probe": "device-description", "method": "GET", "url": device_url},
        {"probe": "service-description", "method": "GET", "url": f"{base}/wps_scpd.xml", "expect_scpd": True},
        {"probe": "control-head", "method": "HEAD", "url": f"{base}/wps_control"},
        {"probe": "event-head", "method": "HEAD", "url": f"{base}/wps_event"},
        {"probe": "event-get", "method": "GET", "url": f"{base}/wps_event"},
    ]


def live(skip_ssdp):
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / ("wfa-49152-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    location = None
    rows = []
    index = 0
    if not skip_ssdp:
        location = ssdp_location(HOST)
        (directory / "ssdp-location.private.txt").write_text(location + "\n")
        index += 1
        row = {"probe": "ssdp-location", "method": "GET", "url": location, "note": "from unicast M-SEARCH"}
        summary, exit_code, status = curl_step(directory, index, row, False)
        rows.append(summary)
        _write_summary(directory, rows)
        print(json.dumps(summary), flush=True)
        if exit_code or status == 503:
            return 1, directory
    for plan_row in build_plan(location):
        index += 1
        summary, exit_code, status = curl_step(directory, index, plan_row, True)
        rows.append(summary)
        _write_summary(directory, rows)
        print(json.dumps(summary), flush=True)
        if exit_code or status == 503:
            return 1, directory
        if plan_row.get("expect_scpd") and not summary.get("scpd_valid"):
            print("SCPD validation failed; stopping before SOAP negatives", flush=True)
            return 1, directory
    for action, (inner, note) in NEGATIVE_ACTIONS.items():
        index += 1
        body_file = directory / f"request-{action}.private.xml"
        body_file.write_bytes(soap_body(action, inner))
        row = {
            "probe": f"negative-{action}",
            "method": "POST",
            "url": f"http://{HOST}:{PORT}/wps_control",
            "headers": (
                'Content-Type: text/xml; charset="utf-8"',
                f'SOAPAction: "{SERVICE}#{action}"',
            ),
            "body_file": body_file,
            "note": note,
        }
        summary, exit_code, status = curl_step(directory, index, row, True)
        rows.append(summary)
        _write_summary(directory, rows)
        print(json.dumps(summary), flush=True)
        if exit_code or status == 503:
            return 1, directory
    print("Completed WFA WLANConfig surface probe; private evidence: " + str(directory), flush=True)
    return 0, directory


def _write_summary(directory, rows):
    (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-ssdp", action="store_true", help="use /wps_device.xml without a new SSDP query")
    args = parser.parse_args()
    code, directory = live(args.skip_ssdp)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
