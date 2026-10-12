#!/usr/bin/env python3
"""Follow-up CUPS probes: ipptool read tests and safe write-boundary discriminators.

Uses paced requests, no credentials, no job creation, no Add-Modify-Printer.
"""
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from cups_ipp_readonly_matrix import HOST, PORT, build_ipp_request, decode_ipp_status

ROOT = Path(__file__).resolve().parents[1]
URI = f"ipp://{HOST}:{PORT}/"
PACING = 3

IPPTOOL_TESTS = (
    "get-printers.test",
    "get-jobs.test",
    "get-completed-jobs.test",
    "get-ppds.test",
    "get-devices.test",
)


def run_ipptool(directory, index, test_name):
    test_path = Path(f"/usr/share/cups/ipptool/{test_name}")
    out = directory / f"ipptool-{index:02d}.stdout.private"
    err = directory / f"ipptool-{index:02d}.stderr.private"
    command = [
        "/usr/bin/ipptool",
        "-4",
        "-L",
        "-t",
        "-v",
        "-T",
        "12",
        "-V",
        "1.1",
        URI,
        str(test_path),
    ]
    completed = subprocess.run(command, capture_output=True, timeout=30, env={**os.environ, "LC_ALL": "C"})
    out.write_bytes(completed.stdout)
    err.write_bytes(completed.stderr)
    combined = completed.stdout + completed.stderr
    statuses = re.findall(rb"status-code\s*=\s*([^\s,]+)", combined)
    row = {
        "kind": "ipptool",
        "test": test_name,
        "ipptool_exit": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "status_tokens": [s.decode("ascii", "replace") for s in statuses[:6]],
        "forbidden": b"Forbidden" in combined,
        "unauthorized": b"Unauthorized" in combined,
        "pass": b"[PASS]" in combined,
        "fail": b"[FAIL]" in combined,
    }
    return row, completed.returncode


def ipp_post(directory, index, name, op_id, attrs):
    body = build_ipp_request(op_id, attrs)
    prefix = directory / f"ipp-{index:02d}"
    req = prefix.with_suffix(".request.private")
    req.write_bytes(body)
    hdr = str(prefix) + ".headers.private"
    out = str(prefix) + ".body.private"
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
    ]
    completed = subprocess.run(command, capture_output=True)
    body_bytes = Path(out).read_bytes() if Path(out).exists() else b""
    headers = Path(hdr).read_bytes() if Path(hdr).exists() else b""
    http_status = int(completed.stdout.strip() or b"0")
    ipp_code, ipp_name = decode_ipp_status(body_bytes)
    snippet = re.sub(rb"[^\x20-\x7e]+", b" ", body_bytes).strip()[:100].decode("ascii", "replace")
    row = {
        "kind": "ipp",
        "operation": name,
        "ipp_operation_id": f"0x{op_id:04x}",
        "curl_exit": completed.returncode,
        "http_status": http_status,
        "bytes": len(body_bytes),
        "sha256": hashlib.sha256(body_bytes).hexdigest(),
        "auth_challenge": bool(re.search(rb"^WWW-Authenticate:", headers, re.M | re.I)),
        "ipp_status_code": ipp_code,
        "ipp_status_name": ipp_name,
        "snippet": snippet,
    }
    return row, completed.returncode, http_status


def main():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / ("cups-ipp-followup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    step = 0

    for test_name in IPPTOOL_TESTS:
        if step:
            time.sleep(PACING)
        step += 1
        row, exit_code = run_ipptool(directory, step, test_name)
        rows.append(row)
        (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if exit_code == 124:
            print("Stopped on ipptool timeout; " + str(directory))
            return 1

    # CUPS-Get-Classes: upstream allows missing printer-uri; include requested-attributes.
    from cups_ipp_readonly_matrix import IPP_TAG_KEYWORD

    extra_reads = (
        (
            "CUPS-Get-Classes",
            0x4003,
            (("requested-attributes", "member-names", IPP_TAG_KEYWORD),),
        ),
        (
            "CUPS-Get-PPDs",
            0x400F,
            (("printer-uri", URI, 0x45), ("requested-attributes", "ppd-name", IPP_TAG_KEYWORD)),
        ),
        (
            "CUPS-Get-PPD",
            0x400E,
            (("printer-uri", URI, 0x45), ("ppd-name", "drv:///sample.drv/sample.ppd", 0x42)),
        ),
    )
    for name, op, attrs in extra_reads:
        time.sleep(PACING)
        step += 1
        row, curl_exit, http_status = ipp_post(directory, step, name, op, attrs)
        rows.append(row)
        (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if curl_exit or http_status == 503:
            print("Stopped on transport error or HTTP 503; " + str(directory))
            return 1

    # Write-boundary discriminators that should not mutate state when no queue exists.
    write_probes = (
        (
            "CUPS-Create-Local-Printer",
            0x4028,
            (
                ("printer-uri", URI, 0x45),
                ("requesting-user-name", "genesis", 0x42),
                ("printer-name", "genesisprobe", 0x42),
                ("device-uri", "ipp://127.0.0.1/invalid", 0x45),
            ),
        ),
        (
            "Pause-Printer",
            0x0010,
            (("printer-uri", f"ipp://{HOST}:{PORT}/printers/nosuch", 0x45),),
        ),
        (
            "CUPS-Set-Default",
            0x4005,
            (("printer-uri", f"ipp://{HOST}:{PORT}/printers/nosuch", 0x45),),
        ),
    )
    for name, op, attrs in write_probes:
        time.sleep(PACING)
        step += 1
        row, curl_exit, http_status = ipp_post(directory, step, name, op, attrs)
        rows.append(row)
        (directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if curl_exit or http_status == 503:
            print("Stopped on transport error or HTTP 503; " + str(directory))
            return 1

    print("Completed CUPS follow-up; private evidence: " + str(directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
