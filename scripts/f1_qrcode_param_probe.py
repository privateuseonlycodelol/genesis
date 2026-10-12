#!/usr/bin/env python3
"""Bounded query-parameter probes on wireless-qrcode-modal.lp.

Authenticated by default; --unauthenticated uses a fresh cookie jar only.
Does not print response bodies or secrets.
"""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
from pathlib import Path

from f1_ipping_control import ProbeClient, StopProbe, _csrf, _login_page
from f1_qrcode_context_probe import BARE_PATH, NGINX_500_SHA, classify_body

ROOT = Path(__file__).resolve().parents[1]
BASELINE_QUERY = {
    "iface": "cred0",
    "broadcastiface": "cred0",
    "ispremium": "false",
    "splitState": "1",
    "isCompatibility": "nil",
    "band6gOnly": "1",
}
MARKER = "genesis-qr-probe"


def _build_query(overrides=None, omit=()):
    q = dict(BASELINE_QUERY)
    if overrides:
        q.update(overrides)
    for key in omit:
        q.pop(key, None)
    return urllib.parse.urlencode(q, doseq=True)


def _cases():
    yield "baseline", _build_query()
    yield "bare_path", None
    yield "iface_only", _build_query(omit=("broadcastiface", "ispremium", "splitState", "isCompatibility", "band6gOnly"))
    yield "iface_cred99", _build_query({"iface": "cred99", "broadcastiface": "cred99"})
    yield "iface_newline", _build_query({"iface": "cred0\n" + MARKER})
    yield "isCompatibility_subst", _build_query({"isCompatibility": "$(printf cred0)"})
    yield "isCompatibility_lt", _build_query({"isCompatibility": "<probe>"})
    yield "splitState_semicolon", _build_query({"splitState": "1;logger " + MARKER})
    yield "band6gOnly_quote", _build_query({"band6gOnly": "1'"})
    yield "legacy_ap_param", _build_query({"ap": "0"})
    yield "iface_duplicate", None  # special: two iface keys


CASE_ORDER = [name for name, _ in _cases()]


def login_flow(client, password):
    code, body = client.open(client.base + "/login.lp")
    if code != 200:
        raise StopProbe("Login page failed")
    client.csrf = _csrf(body)
    code, result = client.login("User", password)
    if code != 200 or result != "ok":
        raise StopProbe("SRP login failed")
    code, body = client.open(client.base + "/gateway.lp")
    if code != 200 or _login_page(body):
        raise StopProbe("Gateway check failed")


def request_case(client, name, query_string):
    if name == "bare_path":
        url = client.base + BARE_PATH
        code, body = client.open(url)
    elif name == "iface_duplicate":
        # cred0 then injected iface
        pairs = [
            ("iface", "cred0"),
            ("broadcastiface", "cred0"),
            ("ispremium", "false"),
            ("splitState", "1"),
            ("isCompatibility", "nil"),
            ("band6gOnly", "1"),
            ("iface", "cred0\n" + MARKER),
        ]
        url = client.base + BARE_PATH + "?" + urllib.parse.urlencode(pairs)
        code, body = client.open(url)
    else:
        url = client.base + BARE_PATH + "?" + query_string
        code, body = client.open(url)

    text = body.decode("utf-8", "replace")
    marker_echo = MARKER in text
    nil_password_err = "password' (a nil value)" in text or "password (a nil value)" in text
    row = classify_body(code, body)
    row["case"] = name
    row["marker_echo"] = marker_echo
    row["nil_password_in_body"] = nil_password_err
    return row


def run(password=None, unauthenticated=False):
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "qrcode-param-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=False, exist_ok=False)
    client = ProbeClient(directory)
    if not unauthenticated:
        login_flow(client, password)
        del password
    else:
        code, body = client.open(client.base + "/login.lp")
        if code == 503:
            raise StopProbe("HTTP 503 on login page")

    results = []
    for name, query in _cases():
        results.append(request_case(client, name, query))

    any_marker = any(r["marker_echo"] for r in results)
    any_200_qr = any(r.get("qrcode_page_hint") for r in results)
    all_auth_gated = unauthenticated and all(
        r["login_marker"] or r["status"] in (401, 403) for r in results if r["case"] != "bare_path"
    )
    if unauthenticated and all_auth_gated:
        conclusion = "unauthenticated contextual GETs returned login or deny; no QR leak without session"
    elif any_marker:
        conclusion = "marker string appeared in at least one response body"
    elif any_200_qr:
        conclusion = "some variants still returned QR pages; see per-case status"
    else:
        conclusion = "no QR page and no marker echo on tested variants"

    outcome = {
        "unauthenticated": unauthenticated,
        "cases": results,
        "conclusion": conclusion,
    }
    (directory / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return directory, outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--unauthenticated", action="store_true")
    args = parser.parse_args()
    if not args.unauthenticated and not args.password_file:
        parser.error("--password-file required unless --unauthenticated")
    password = None
    if args.password_file:
        password = args.password_file.read_text().strip("\n")
    try:
        directory, outcome = run(password=password, unauthenticated=args.unauthenticated)
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
