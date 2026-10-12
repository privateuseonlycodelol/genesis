#!/usr/bin/env python3
"""One loopback TRACE with transformer log diff (igd_traceroute_helper oracle)."""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
from pathlib import Path

from f1_ipping_control import ProbeClient, StopProbe, _csrf, _login_page, parse_log_rows


def _diff(before, after):
    seen = {json.dumps(e, sort_keys=True) for e in before}
    return [e for e in after if json.dumps(e, sort_keys=True) not in seen]

ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = "/modals/diagnostics-ping-modal.lp"
LOG_PATH = "/modals/logviewer-modal.lp"
TRACE_HELPER = "async run: /usr/bin/igd_traceroute_helper"
IPPING_HELPER = "async run: /usr/bin/ipping_helper"
ASYNC_RE = re.compile(r"async run: (.+)")


def classify_line(message):
    if message == TRACE_HELPER:
        return {"helper": "igd_traceroute_helper", "arguments_logged": False}
    if message == IPPING_HELPER:
        return {"helper": "ipping_helper", "arguments_logged": False}
    if message.startswith(TRACE_HELPER + " "):
        return {"helper": "igd_traceroute_helper", "arguments_logged": True, "message": message}
    if message.startswith(IPPING_HELPER + " "):
        return {"helper": "ipping_helper", "arguments_logged": True, "message": message}
    m = ASYNC_RE.search(message)
    if m:
        cmd = m.group(1)
        if len(cmd) > 180:
            cmd = "<redacted len=%d>" % len(cmd)
        return {"helper": "other", "command": cmd}
    return None


def log_events(rows):
    out = []
    for row in rows:
        c = classify_line(row["message"])
        if c:
            out.append({"date": row["date"], **c})
    return out


def _read_log(client):
    code, body = client.open(client.base + LOG_PATH + "?process=transformer")
    if code != 200 or _login_page(body):
        raise StopProbe("Log read failed")
    return log_events(parse_log_rows(body))


def trace_fields(csrf):
    return [
        ("action", "TRACE"),
        ("CSRFtoken", csrf),
        ("ProtocolVersionTrace", "IPv4"),
        ("ipAddressTrace", "127.0.0.1"),
        ("MaxHopCount", "1"),
        ("MaxSize", "46"),
    ]


def run(client, password):
    code, body = client.open(client.base + "/login.lp")
    if code != 200:
        raise StopProbe("Login page failed")
    client.csrf = _csrf(body)
    code, result = client.login("User", password)
    del password
    if code != 200 or result != "ok":
        raise StopProbe("Login failed")
    code, body = client.open(client.base + "/gateway.lp")
    if code != 200 or _login_page(body):
        raise StopProbe("Gateway failed")
    client.csrf = _csrf(body)

    before = _read_log(client)
    time.sleep(2)
    quiet = _read_log(client)
    if _diff(before, quiet):
        return {"conclusion": "spontaneous log activity; TRACE not sent", "quiet": quiet}

    data = urllib.parse.urlencode(trace_fields(client.csrf)).encode()
    code, body = client.open(client.base + TRACE_PATH, data, "POST", timeout=60)
    after = _read_log(client)
    added = _diff(quiet, after)

    login = _login_page(body)
    rejected = b"Please enter valid ipv4/domain address" in body

    return {
        "trace_status": code,
        "trace_bytes": len(body),
        "trace_sha256": hashlib.sha256(body).hexdigest(),
        "login_marker": bool(login),
        "rejected_phrase": rejected,
        "quiet_before": quiet,
        "after": after,
        "new_events": added,
        "conclusion": (
            "TRACE added igd_traceroute_helper"
            if any(e.get("helper") == "igd_traceroute_helper" for e in added)
            else "TRACE did not add igd_traceroute_helper in log window"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "trace-control-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=False, exist_ok=False)
    client = ProbeClient(directory)
    try:
        password = args.password_file.read_text().strip("\n")
        outcome = run(client, password)
        (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(json.dumps({"result": outcome["conclusion"], "artifacts": str(directory)}), flush=True)
        return 0
    except (StopProbe, urllib.error.URLError, TimeoutError) as error:
        print("Stopped: " + str(error), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
