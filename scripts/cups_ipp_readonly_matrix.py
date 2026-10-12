#!/usr/bin/env python3
"""Paced, unauthenticated CUPS HTTP and read-only IPP operation matrix on the owned F1.

No credentials, cookies, job creation, or administrative write operations. Raw
responses stay in ignored artifacts with private permissions; stdout is metadata.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "192.168.2.1"
PORT = 631
PACING_SEC = 3

IPP_TAG_OPERATION = 0x01
IPP_TAG_END = 0x03
IPP_TAG_CHARSET = 0x47
IPP_TAG_LANGUAGE = 0x48
IPP_TAG_URI = 0x45
IPP_TAG_KEYWORD = 0x44
IPP_TAG_INTEGER = 0x21
IPP_TAG_NAME = 0x42

IPP_STATUS = {
    0x0000: "successful-ok",
    0x0400: "client-error-bad-request",
    0x0401: "client-error-forbidden",
    0x0403: "client-error-not-found",
    0x0404: "client-error-not-found-alt",
    0x0405: "client-error-not-possible",
    0x0406: "client-error-not-found-cups",
    0x0408: "client-error-request-value",
    0x0409: "client-error-not-found-resource",
    0x0410: "client-error-not-found-destination",
    0x0500: "server-error-internal",
    0x0501: "server-error-operation-not-supported",
    0x0503: "server-error-version-not-supported",
    0x0504: "server-error-device-error",
}

READ_OPERATIONS = (
    ("CUPS-Get-Printers", 0x4002, (("requested-attributes", "printer-state", IPP_TAG_KEYWORD),)),
    ("CUPS-Get-Default", 0x4001, ()),
    ("CUPS-Get-Classes", 0x4003, ()),
    ("CUPS-Get-Devices", 0x400B, ()),
    ("CUPS-Get-PPDs", 0x400F, ()),
    ("CUPS-Get-PPD", 0x400E, (("ppd-name", "everywhere", IPP_TAG_NAME),)),
    ("Get-Printer-Attributes", 0x000B, (("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),)),
    ("Get-Jobs", 0x000A, (("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),)),
    (
        "Get-Job-Attributes",
        0x0009,
        (
            ("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),
            ("job-id", 1, IPP_TAG_INTEGER),
        ),
    ),
    (
        "Get-Printer-Supported-Values",
        0x0013,
        (
            ("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),
            ("requested-attributes", "media", IPP_TAG_KEYWORD),
        ),
    ),
    ("Get-Subscriptions", 0x000C, ()),
    (
        "Get-Subscription-Attributes",
        0x000D,
        (("subscription-id", 1, IPP_TAG_INTEGER),),
    ),
    (
        "Get-Notifications",
        0x000E,
        (
            ("notify-subscription-ids", 1, IPP_TAG_INTEGER),
            ("notify-sequence-numbers", 0, IPP_TAG_INTEGER),
        ),
    ),
)

HTTP_CONTROLS = (
    ("GET", "/"),
    ("GET", "/admin/"),
    ("GET", "/printers/"),
    ("GET", "/admin/conf/cupsd.conf"),
    ("HEAD", "/"),
    ("POST", "/", "text/plain"),
)


def _string_attr(tag, name, value):
    name_b = name.encode("ascii")
    value_b = value.encode("utf-8")
    return (
        bytes([tag])
        + struct.pack(">H", len(name_b))
        + name_b
        + struct.pack(">H", len(value_b))
        + value_b
    )


def _integer_attr(name, value):
    name_b = name.encode("ascii")
    return bytes([IPP_TAG_INTEGER]) + struct.pack(">H", len(name_b)) + name_b + struct.pack(">Hi", 4, int(value))


def build_ipp_request(operation_id, extra_attrs=(), request_id=0x13579bdf):
    parts = [
        b"\x01\x01",
        struct.pack(">H", operation_id),
        struct.pack(">I", request_id),
        bytes([IPP_TAG_OPERATION]),
        _string_attr(IPP_TAG_CHARSET, "attributes-charset", "utf-8"),
        _string_attr(IPP_TAG_LANGUAGE, "attributes-natural-language", "en"),
    ]
    for item in extra_attrs:
        if len(item) == 3:
            name, value, tag = item
            if tag == IPP_TAG_INTEGER:
                parts.append(_integer_attr(name, value))
            else:
                parts.append(_string_attr(tag, name, str(value)))
        else:
            raise ValueError("unexpected attribute tuple")
    parts.append(bytes([IPP_TAG_END]))
    return b"".join(parts)


def decode_ipp_status(body):
    if len(body) < 4 or body[0:2] != b"\x01\x01":
        return None, None
    code = struct.unpack(">H", body[2:4])[0]
    return code, IPP_STATUS.get(code, f"status-0x{code:04x}")


def ascii_snippets(body, limit=120):
    text = re.sub(rb"[^\x20-\x7e]+", b" ", body).strip()
    if len(text) > limit:
        text = text[: limit - 3] + b"..."
    return text.decode("ascii", "replace")


def curl_exchange(directory, index, method, path, data=None, content_type="application/ipp"):
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
    if method == "HEAD":
        command.append("--head")
    if data is not None:
        req_path = prefix.with_suffix(".request.private")
        req_path.write_bytes(data)
        command += ["--header", f"Content-Type: {content_type}", "--data-binary", f"@{req_path}"]
    command.append(f"http://{HOST}:{PORT}{path}")
    if method == "POST" and data is None:
        command.insert(1, "-X")
        command.insert(2, "POST")
    completed = subprocess.run(command, capture_output=True)
    body_path = Path(str(prefix) + ".body.private")
    header_path = Path(str(prefix) + ".headers.private")
    body = body_path.read_bytes() if body_path.exists() else b""
    headers = header_path.read_bytes() if header_path.exists() else b""
    status = int(completed.stdout.strip() or b"0")
    content = ""
    match = re.search(rb"^Content-Type:\s*([^\r\n]+)", headers, re.M | re.I)
    if match:
        content = match.group(1).decode("ascii", "replace").strip()
    ipp_code, ipp_name = decode_ipp_status(body)
    row = {
        "request": index,
        "method": method,
        "path": path,
        "curl_exit": completed.returncode,
        "http_status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": content,
        "auth_challenge": bool(re.search(rb"^WWW-Authenticate:", headers, re.M | re.I)),
        "ipp_status_code": ipp_code,
        "ipp_status_name": ipp_name,
        "ipp_snippet": ascii_snippets(body) if content.startswith("application/ipp") else "",
        "cups_version_marker": bool(re.search(rb"CUPS v2\.2\.10", body)),
    }
    return row, completed.returncode, status


def main():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / ("cups-ipp-matrix-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    index = 0

    for control in HTTP_CONTROLS:
        if index:
            time.sleep(PACING_SEC)
        index += 1
        method, path = control[0], control[1]
        payload = None
        content_type = "application/ipp"
        if len(control) > 2:
            content_type = control[2]
            payload = b"probe"
        row, curl_exit, http_status = curl_exchange(directory, index, method, path, payload, content_type)
        row["kind"] = "http"
        row["operation"] = f"{method} {path}"
        rows.append(row)
        _write_summary(directory, rows, row)
        if curl_exit or http_status == 503:
            print("Stopped on transport error or HTTP 503; private evidence: " + str(directory))
            return 1

    for name, op_id, attrs in READ_OPERATIONS:
        time.sleep(PACING_SEC)
        index += 1
        payload = build_ipp_request(op_id, attrs)
        row, curl_exit, http_status = curl_exchange(directory, index, "POST", "/", payload)
        row["kind"] = "ipp"
        row["operation"] = name
        row["ipp_operation_id"] = f"0x{op_id:04x}"
        rows.append(row)
        _write_summary(directory, rows, row)
        if curl_exit or http_status == 503:
            print("Stopped on transport error or HTTP 503; private evidence: " + str(directory))
            return 1

    print("Completed CUPS read-only matrix; private evidence: " + str(directory))
    return 0


def _write_summary(directory, rows, last_row):
    (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(last_row), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
