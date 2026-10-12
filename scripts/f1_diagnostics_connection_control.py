#!/usr/bin/env python3
"""One diagnostics Connection RESTART with transformer log diff."""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
from collections import Counter
from pathlib import Path

from f1_ipping_control import (
    HELPER_EXACT,
    ProbeClient,
    StopProbe,
    _csrf,
    _login_page,
    classify_helper,
    new_events,
    parse_log_rows,
)

ROOT = Path(__file__).resolve().parents[1]
CONN_PATH = "/modals/diagnostics-connection-modal.lp"
LOG_PATH = "/modals/logviewer-modal.lp"
ASYNC_RE = re.compile(r"async run: (.+)")


def helper_events(rows):
    events = []
    for row in rows:
        msg = row["message"]
        if "ipping_helper" in msg:
            classified = classify_helper(msg)
            if classified:
                events.append({"kind": "ipping_helper", **classified, "date": row["date"]})
            continue
        match = ASYNC_RE.search(msg)
        if match:
            cmd = match.group(1)
            if len(cmd) > 200:
                cmd = "<redacted len=%d>" % len(cmd)
            events.append({"kind": "async_run", "command": cmd, "date": row["date"]})
    return events


def _read_log(client, query="?process=transformer"):
    code, body = client.open(client.base + LOG_PATH + query)
    if code != 200 or _login_page(body):
        raise StopProbe("Log read failed")
    return helper_events(parse_log_rows(body))


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
    before2 = _read_log(client)
    spontaneous = new_events(before, before2)
    if spontaneous:
        return {"conclusion": "spontaneous log activity; RESTART not sent", "spontaneous": spontaneous}

    fields = [
        ("action", "SAVE"),
        ("operation", "RESTART"),
        ("CSRFtoken", client.csrf),
    ]
    data = urllib.parse.urlencode(fields).encode()
    code, body = client.open(client.base + CONN_PATH, data, "POST", timeout=45)
    post_ok = code == 200 and not _login_page(body) and "diagnostics-connection" in body.decode("utf-8", "replace").lower()

    after = _read_log(client)
    added = new_events(before2, after)

    return {
        "post_status": code,
        "post_bytes": len(body),
        "post_sha256": hashlib.sha256(body).hexdigest(),
        "post_modal": post_ok,
        "before_async": before2,
        "new_async": added,
        "conclusion": "RESTART added async log lines" if added else "RESTART did not add transformer async lines",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "diag-connection-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
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
