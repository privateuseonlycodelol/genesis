#!/usr/bin/env python3
"""One loopback diagnostics ping, with transformer-log snapshots around it.

Destination, repetition count, and size are fixed. This does not send TRACE,
export, reboot, or any host other than 127.0.0.1. Cookie and response bodies
stay under ignored artifacts. Printed JSON omits tokens and log text that is
not the ipping_helper launch line.
"""
import argparse
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
from collections import Counter
from pathlib import Path

from f1_srp_login import SRPClient

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
REPETITIONS = "1"
BLOCK_SIZE = "56"
PROTOCOL = "IPv4"
HELPER_EXACT = "async run: /usr/bin/ipping_helper"
PING_PATH = "/modals/diagnostics-ping-modal.lp"
LOG_PATH = "/modals/logviewer-modal.lp"
STAMP_RE = re.compile(r"^[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2}$")
PROCESS_RE = re.compile(r"^transformer\[\d+\]$")
ROW_RE = re.compile(
    r"<tr>\s*<td[^>]*data-title=\"Date\">(.*?)</td>\s*"
    r"<td[^>]*data-title=\"Facility\">(.*?)</td>\s*"
    r"<td[^>]*data-title=\"Process\">(.*?)</td>\s*"
    r"<td[^>]*data-title=\"Message\">(.*?)</td>",
    re.I | re.S,
)
SPAN_RE = re.compile(r"<span id=\"([^\"]*)\"[^>]*>(.*?)</span>", re.I | re.S)
TRACE_RE = re.compile(r'id="pingtrace".*?<tbody>(.*?)</tbody>', re.I | re.S)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
INPUT_RE = re.compile(
    r"<input[^>]*name=\"ipAddress\"[^>]*value=\"([^\"]*)\"", re.I
)


class StopProbe(RuntimeError):
    pass


def _text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_log_rows(body):
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    rows = []
    for date, facility, process, message in ROW_RE.findall(body):
        rows.append(
            {
                "date": _text(date),
                "facility": _text(facility),
                "process": _text(process),
                "message": _text(message),
            }
        )
    return rows


def classify_helper(message):
    if message == HELPER_EXACT:
        return {"arguments_logged": False, "message": message}
    prefix = HELPER_EXACT + " "
    if (
        message.startswith(prefix)
        and len(message) <= 240
        and re.fullmatch(r"[\x20-\x7e]+", message)
    ):
        return {"arguments_logged": True, "message": message}
    if "ipping_helper" in message:
        return {
            "arguments_logged": None,
            "length": len(message),
            "sha256": hashlib.sha256(message.encode()).hexdigest(),
        }
    return None


def helper_events(rows):
    events = []
    for row in rows:
        classified = classify_helper(row["message"])
        if not classified:
            continue
        event = {
            "date": row["date"] if STAMP_RE.match(row["date"]) else "<unstamped>",
            "process": row["process"] if PROCESS_RE.match(row["process"]) else "<redacted-process>",
        }
        event.update(classified)
        events.append(event)
    return events


def _event_key(event):
    return (
        event.get("date"),
        event.get("process"),
        event.get("message"),
        event.get("sha256"),
        event.get("arguments_logged"),
    )


def new_events(before, after):
    later = Counter(_event_key(event) for event in after)
    earlier = Counter(_event_key(event) for event in before)
    added = later - earlier
    found = []
    for event in after:
        key = _event_key(event)
        if added[key] > 0:
            found.append(event)
            added[key] -= 1
    return found


def ping_fields(csrf):
    if not csrf or any(char in csrf for char in "\r\n\x00"):
        raise StopProbe("CSRF value is empty or unsafe to encode")
    return [
        ("action", "PING"),
        ("CSRFtoken", csrf),
        ("ProtocolVersion", PROTOCOL),
        ("ipAddress", HOST),
        ("NumberOfRepetitions", REPETITIONS),
        ("DataBlockSize", BLOCK_SIZE),
    ]


def public_request(fields):
    visible = []
    for name, value in fields:
        if name == "CSRFtoken":
            visible.append({"name": name, "present": True, "length": len(value)})
        else:
            visible.append({"name": name, "value": value})
    return {
        "method": "POST",
        "path": PING_PATH,
        "content_type": "application/x-www-form-urlencoded",
        "fields": visible,
    }


def _keep_status(value):
    value = re.sub(r"\s+", " ", value).strip()
    if value in {"", HOST, "Please enter valid ipv4/domain address"}:
        return value
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .:_-]{0,60}", value):
        return value
    if re.fullmatch(r"\d+ ms", value) or re.fullmatch(r"\d+", value):
        return value
    return "<redacted len=%d>" % len(value)


def parse_ping_result(body):
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    login = bool(re.search(r'id\s*=\s*["\']sign-me-in["\']', body, re.I))
    spans = {}
    for name, value in SPAN_RE.findall(body):
        key = _text(name)
        if key not in spans:
            spans[key] = _keep_status(_text(value))
    wanted = (
        "Status:",
        "Success Count:",
        "Failure Count:",
        "Min Resp Time:",
        "Max Resp Time:",
        "Avg Resp Time:",
    )
    echoed = INPUT_RE.search(body)
    trace = []
    match = TRACE_RE.search(body)
    if match:
        for row in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.S | re.I):
            cells = [_text(cell) for cell in CELL_RE.findall(row)]
            if len(cells) != 5:
                trace.append({"cells": len(cells), "kept": False})
                continue
            size, address, seq, ttl, elapsed = cells
            safe = (
                re.fullmatch(r"\d+", size)
                and address == HOST
                and re.fullmatch(r"\d+", seq)
                and re.fullmatch(r"\d+", ttl)
                and re.fullmatch(r"\d+(?:\.\d+)?", elapsed)
            )
            trace.append(
                {"bytes": size, "ip": address, "seq": seq, "ttl": ttl, "time": elapsed}
                if safe
                else {"cells": 5, "kept": False}
            )
    return {
        "login_marker": login,
        "diagnostics_modal": 'id="send-config_PING"' in body or "send-config_PING" in body,
        "spans": {key: spans.get(key) for key in wanted},
        "ip_echo": _keep_status(_text(echoed.group(1))) if echoed else None,
        "trace": trace,
    }


class ProbeClient(SRPClient):
    def __init__(self, directory):
        super().__init__(str(directory / "cookies.txt"), "http://192.168.2.1")
        self.directory = directory
        self.index = 0
        self.rows = []

    def open(self, url, data=None, method="GET", timeout=30):
        if self.index:
            time.sleep(2)
        self.index += 1
        try:
            code, body = super()._open(url, data, method, timeout=timeout)
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        path = urllib.parse.urlsplit(url).path
        action = None
        if data is not None:
            action = urllib.parse.parse_qs(data.decode()).get("action", [None])[0]
        if action is None:
            action = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("action", [None])[0]
        row = {
            "request": self.index,
            "method": method,
            "path": path,
            "query": urllib.parse.urlsplit(url).query,
            "action": action,
            "status": code,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "wall_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_local": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        }
        self.rows.append(row)
        (self.directory / ("response-%02d.private" % self.index)).write_bytes(body)
        (self.directory / "summary.json").write_text(json.dumps(self.rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if code == 503:
            raise StopProbe("HTTP 503: stopped immediately")
        return code, body


def _csrf(body):
    match = re.search(rb'CSRFtoken["\']\s+content\s*=\s*["\']([^"\']+)', body, re.I)
    if not match:
        raise StopProbe("CSRF meta not found")
    return match.group(1).decode()


def _login_page(body):
    return bool(re.search(rb'id\s*=\s*["\']sign-me-in["\']', body, re.I))


def _read_helpers(client, query):
    code, body = client.open(client.base + LOG_PATH + query)
    if code != 200 or _login_page(body):
        raise StopProbe("Log read was not an authenticated log page")
    text = body.decode("utf-8", "replace")
    if 'id="logviewer"' not in text:
        raise StopProbe("Log response had no log table")
    rows = parse_log_rows(text)
    return helper_events(rows), len(rows)


def _baseline(client):
    """Prefer the transformer filter. If it is empty while the full log already
    contains a helper line, the filter is hiding the event and cannot be used.
    """
    filtered, filtered_count = _read_helpers(client, "?process=transformer")
    if filtered_count:
        return "?process=transformer", filtered, filtered_count
    full, full_count = _read_helpers(client, "")
    if full:
        return "", full, full_count
    return "?process=transformer", filtered, filtered_count


def run(client, password):
    code, body = client.open(client.base + "/login.lp")
    if code != 200:
        raise StopProbe("Login page failed")
    client.csrf = _csrf(body)
    code, result = client.login("User", password)
    del password
    if code != 200 or result != "ok":
        raise StopProbe("Normal SRP login did not verify; stopped")
    code, body = client.open(client.base + "/gateway.lp")
    if code != 200 or _login_page(body):
        raise StopProbe("Authenticated page control failed")
    client.csrf = _csrf(body)
    build_231b = b"23.1.b" in body
    code, body = client.open(client.base + "/gateway.lp?auto_update=true&getSessionStatus=true")
    try:
        role = json.loads(body).get("current_role")
    except (ValueError, AttributeError):
        role = None
    if code != 200 or role != "admin":
        raise StopProbe("Authenticated admin-session control failed")

    query, before, before_count = _baseline(client)
    second, second_count = _read_helpers(client, query)
    spontaneous = new_events(before, second)
    outcome = {
        "build_label_231b": build_231b,
        "log_query": query,
        "before_helper": before,
        "before_row_count": before_count,
        "quiet_helper": second,
        "quiet_row_count": second_count,
        "spontaneous_helper": spontaneous,
        "ping_sent": False,
    }
    if spontaneous:
        outcome["conclusion"] = "spontaneous helper launch before the ping; ping was not sent"
        return outcome

    fields = ping_fields(client.csrf)
    request = public_request(fields)
    (client.directory / "request-ping.json").write_text(json.dumps(request, indent=2) + "\n")
    data = urllib.parse.urlencode(fields).encode()
    code, body = client.open(client.base + PING_PATH, data, "POST", timeout=45)
    outcome["ping_sent"] = True
    outcome["ping_status"] = code
    outcome["ping"] = parse_ping_result(body)
    if code != 200 or outcome["ping"]["login_marker"]:
        outcome["conclusion"] = "ping POST did not return the diagnostics modal"
        after, after_count = _read_helpers(client, query)
        outcome["after_helper"] = after
        outcome["after_row_count"] = after_count
        outcome["new_helper"] = new_events(second, after)
        return outcome

    after, after_count = _read_helpers(client, query)
    added = new_events(second, after)
    if not added:
        retry, retry_count = _read_helpers(client, query)
        outcome["after_retry_helper"] = retry
        outcome["after_retry_row_count"] = retry_count
        added = new_events(second, retry)
        after, after_count = retry, retry_count
    outcome["after_helper"] = after
    outcome["after_row_count"] = after_count
    outcome["new_helper"] = added
    ping = outcome["ping"]
    result_for_host = any(row.get("ip") == HOST for row in ping["trace"])
    if added and result_for_host:
        outcome["conclusion"] = "PING response contained the loopback result and a new ipping_helper log line"
    elif added and not result_for_host:
        outcome["conclusion"] = "new ipping_helper log line without a loopback result row in the POST body"
    elif result_for_host and not added:
        outcome["conclusion"] = "loopback ping result returned and the helper log line did not change"
    else:
        outcome["conclusion"] = "no new helper line and no loopback result row"
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "ipping-control-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    client = ProbeClient(directory)
    try:
        password = args.password_file.read_text().strip("\n")
        outcome = run(client, password)
        (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(json.dumps({"result": outcome["conclusion"], "artifacts": str(directory)}), flush=True)
        return 0
    except (StopProbe, urllib.error.URLError, TimeoutError) as error:
        print(
            "Stopped: " + (str(error) if isinstance(error, StopProbe) else type(error).__name__),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
