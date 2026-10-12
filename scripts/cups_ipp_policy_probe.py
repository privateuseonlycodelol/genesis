#!/usr/bin/env python3
"""Unauthenticated CUPS IPP policy discriminators (no job creation, no queue creation).

Uses malformed or non-existent targets so handlers should not mutate state.
"""
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from cups_ipp_readonly_matrix import HOST, PORT, IPP_TAG_URI, build_ipp_request, decode_ipp_status

ROOT = Path(__file__).resolve().parents[1]
PACING = 3

PROBES = (
    (
        "CUPS-Add-Modify-Printer-bad-uri",
        0x4004,
        (("printer-uri", f"ipp://{HOST}:{PORT}/not-printers/bad", IPP_TAG_URI),),
        "bad-request",
    ),
    (
        "CUPS-Add-Modify-Printer-invalid-name",
        0x4004,
        (("printer-uri", f"ipp://{HOST}:{PORT}/printers/bad/name", IPP_TAG_URI),),
        "bad-request",
    ),
    (
        "CUPS-Delete-Printer-missing",
        0x4006,
        (("printer-uri", f"ipp://{HOST}:{PORT}/printers/nosuchqueue", IPP_TAG_URI),),
        "not-found",
    ),
    (
        "CUPS-Set-Default-missing",
        0x4005,
        (("printer-uri", f"ipp://{HOST}:{PORT}/printers/nosuchqueue", IPP_TAG_URI),),
        "not-found",
    ),
    (
        "CUPS-Get-Classes-bad-uri",
        0x4003,
        (("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),),
        "bad-request",
    ),
    (
        "CUPS-Get-Classes-valid-form",
        0x4003,
        (("printer-uri", f"ipp://{HOST}:{PORT}/classes/nosuch", IPP_TAG_URI),),
        "not-found-or-empty",
    ),
    (
        "CUPS-Create-Local-Printer-remote",
        0x4028,
        (
            ("printer-uri", f"ipp://{HOST}:{PORT}/", IPP_TAG_URI),
            ("requesting-user-name", "genesis", 0x42),
            ("printer-name", "genesisprobe", 0x42),
            ("device-uri", "ipp://127.0.0.1/invalid", 0x45),
        ),
        "forbidden",
    ),
)


def main():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / ("cups-ipp-policy-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    rows = []

    for index, (name, op_id, attrs, expect) in enumerate(PROBES, 1):
        if index > 1:
            time.sleep(PACING)
        body = build_ipp_request(op_id, attrs)
        prefix = directory / f"probe-{index:02d}"
        req = prefix.with_suffix(".request.private")
        req.write_bytes(body)
        hdr = str(prefix) + ".headers.private"
        out = str(prefix) + ".body.private"
        completed = subprocess.run(
            [
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
                hdr,
                "--output",
                out,
                "--write-out",
                "%{http_code}",
                "-H",
                "Content-Type: application/ipp",
                "--data-binary",
                f"@{req}",
                f"http://{HOST}:{PORT}/",
            ],
            capture_output=True,
        )
        body_bytes = Path(out).read_bytes() if Path(out).exists() else b""
        headers = Path(hdr).read_bytes() if Path(hdr).exists() else b""
        http_status = int(completed.stdout.strip() or b"0")
        ipp_code, ipp_name = decode_ipp_status(body_bytes)
        snippet = re.sub(rb"[^\x20-\x7e]+", b" ", body_bytes).strip()[:120].decode("ascii", "replace")
        row = {
            "probe": name,
            "ipp_operation_id": f"0x{op_id:04x}",
            "expect_class": expect,
            "curl_exit": completed.returncode,
            "http_status": http_status,
            "bytes": len(body_bytes),
            "sha256": hashlib.sha256(body_bytes).hexdigest(),
            "auth_challenge": bool(re.search(rb"^WWW-Authenticate:", headers, re.M | re.I)),
            "ipp_status_code": ipp_code,
            "ipp_status_name": ipp_name,
            "snippet": snippet,
        }
        rows.append(row)
        (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if completed.returncode or http_status == 503:
            print("Stopped on transport error or HTTP 503; " + str(directory))
            return 1

    print("Completed policy probes; private evidence: " + str(directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
