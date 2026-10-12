#!/usr/bin/env python3
"""Wireless QR modal: bare GET vs contextual URLs from the live AP modal.

Authenticated GET only. Does not print QR payloads, PSKs, or CSRF values.
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

from f1_ipping_control import ProbeClient, StopProbe, _csrf, _login_page, parse_log_rows

ROOT = Path(__file__).resolve().parents[1]
BARE_PATH = "/modals/wireless-qrcode-modal.lp"
AP_PATH = "/modals/wireless-ap-modal-newEM.lp"
LOG_PATH = "/modals/logviewer-modal.lp"
QR_REMOTE_RE = re.compile(
    r'data-remote\s*=\s*["\']([^"\']*wireless-qrcode-modal\.lp[^"\']*)["\']',
    re.I,
)
NGINX_500_SHA = "9e93ecf12d78a8c4c278708706bd249fe086983fb28f82eb880f5c7795043962"


def normalize_remote(remote: str) -> str:
    remote = remote.strip()
    if remote.startswith("/"):
        path = remote
    else:
        path = "/" + remote.lstrip("/")
    parts = urllib.parse.urlsplit(path)
    return parts.path + (("?" + parts.query) if parts.query else "")


def extract_qr_targets(html: str) -> list[str]:
    seen = set()
    out = []
    for match in QR_REMOTE_RE.findall(html):
        url = normalize_remote(match)
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def classify_body(code: int, body: bytes) -> dict:
    text = body.decode("utf-8", "replace")
    sha = hashlib.sha256(body).hexdigest()
    login = bool(re.search(r'id\s*=\s*["\']sign-me-in["\']', text, re.I))
    generic_500 = (
        code == 500
        and len(body) <= 600
        and ("Internal Server Error" in text or sha == NGINX_500_SHA)
    )
    ap_modal = "wireless-ap-modal-newEM" in text and "wpa_psk" in text
    qrcode_hint = "wireless-qrcode" in text.lower() or "qrcode" in text.lower()
    has_lua_trace = "wireless_qr" in text or ".lua:" in text
    return {
        "status": code,
        "bytes": len(body),
        "sha256": sha,
        "login_marker": login,
        "generic_nginx_500": generic_500,
        "looks_like_ap_modal": ap_modal,
        "qrcode_page_hint": qrcode_hint and not login and not generic_500,
        "lua_trace_in_body": has_lua_trace,
    }


def log_hits(body: bytes) -> list[dict]:
    rows = parse_log_rows(body)
    hits = []
    for row in rows:
        msg = row["message"]
        if "wireless_qr" in msg or "qrcode" in msg.lower():
            hits.append(
                {
                    "date": row["date"],
                    "process": row["process"],
                    "message_sha256": hashlib.sha256(msg.encode()).hexdigest(),
                    "length": len(msg),
                }
            )
    return hits


def run_probe(client: ProbeClient, password: str) -> dict:
    code, body = client.open(client.base + "/login.lp")
    if code != 200:
        raise StopProbe("Login page failed")
    client.csrf = _csrf(body)
    code, result = client.login("User", password)
    del password
    if code != 200 or result != "ok":
        raise StopProbe("SRP login did not verify")
    code, body = client.open(client.base + "/gateway.lp")
    if code != 200 or _login_page(body):
        raise StopProbe("Authenticated gateway check failed")
    client.csrf = _csrf(body)

    log_before_code, log_before_body = client.open(client.base + LOG_PATH + "?process=transformer")
    log_before_hits = log_hits(log_before_body) if log_before_code == 200 else []

    code, bare_body = client.open(client.base + BARE_PATH)
    bare = classify_body(code, bare_body)

    code, ap_body = client.open(client.base + AP_PATH)
    if code != 200 or _login_page(ap_body):
        raise StopProbe("AP modal GET failed or returned login")
    targets = extract_qr_targets(ap_body.decode("utf-8", "replace"))
    if not targets:
        raise StopProbe("No wireless-qrcode data-remote links in AP modal")

    contextual = []
    for target in targets:
        code, body = client.open(client.base + target)
        contextual.append({"path_query": target.split("?", 1)[0] + ("?" + target.split("?", 1)[1] if "?" in target else ""), "query_keys": sorted(urllib.parse.parse_qs(urllib.parse.urlsplit(target).query).keys()), **classify_body(code, body)})

    log_after_code, log_after_body = client.open(client.base + LOG_PATH + "?process=transformer")
    log_after_hits = log_hits(log_after_body) if log_after_code == 200 else []

    any_200_qr = any(c.get("qrcode_page_hint") for c in contextual)
    all_500 = all(c.get("generic_nginx_500") or c.get("status") == 500 for c in contextual)
    if any_200_qr:
        conclusion = "contextual GET returned a non-login QR-related page"
    elif bare.get("generic_nginx_500") and all_500:
        conclusion = "bare and contextual GETs all returned generic nginx 500"
    elif bare.get("generic_nginx_500") and not all_500:
        conclusion = "contextual GET differed from bare 500 baseline"
    else:
        conclusion = "mixed responses; see per-request classification"

    return {
        "bare": bare,
        "ap_path": AP_PATH,
        "contextual_count": len(contextual),
        "contextual": contextual,
        "log_before_qr_hits": log_before_hits,
        "log_after_qr_hits": log_after_hits,
        "conclusion": conclusion,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / "artifacts" / "ui" / (
        "qrcode-context-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    client = ProbeClient(directory)
    try:
        password = args.password_file.read_text().strip("\n")
        outcome = run_probe(client, password)
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
