#!/usr/bin/env python3
"""Coverage report for a local F1 HAR, using the grabber's path rules.

Prints methods, statuses, and paths only. Does not print cookies, header
values, request bodies, response text, or query values other than action names.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

HOST = "192.168.2.1"
BLOCK = {"/authenticate"}
QUERY_KEYS = {"action", "auto_update", "getSessionStatus", "requested_params"}
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:js|modals|ajax|css|img|font)/[A-Za-z0-9_./-]+\.(?:js|lp|lua|css|png|gif|jpe?g|svg|woff2?|ttf)"
    r"|(?<![A-Za-z0-9_])/(?:[A-Za-z0-9_-]+\.lp)"
)
GAP_PAGES = (
    "/modals/internet-ex-modal.lp",
    "/modals/ipv6devices-modal.lp",
    "/modals/basicview-wifissid-modal.lp",
    "/modals/basicview-wifissid5GHz-modal.lp",
    "/modals/basicview-wifipsk-modal.lp",
    "/modals/basicview-wifipsk5GHz-modal.lp",
    "/modals/basicview-wifiguest-modal.lp",
    "/modals/basicview-wifiguest5GHz-modal.lp",
    "/modals/wireless-qrcode-modal.lp",
)


def load_seeds(userscript: Path) -> set[str]:
    text = userscript.read_text(encoding="utf-8")
    seeds: set[str] = set()
    for name in ("KNOWN_JS", "KNOWN_MODALS", "SHELL_PAGES", "EXTRA_STATIC"):
        match = re.search(rf"const {name} = \[(.*?)\];", text, re.S)
        if not match:
            raise SystemExit(f"could not find {name} in {userscript}")
        seeds.update(re.findall(r'"(/[^"]+)"', match.group(1)))
    return seeds


def wanted(pathname: str) -> bool:
    if not pathname.startswith("/") or pathname in BLOCK:
        return False
    if pathname.startswith("/js/") and pathname.endswith(".js"):
        return True
    if pathname.endswith(".lp"):
        return True
    if pathname.startswith("/css/") and pathname.endswith(".css"):
        return True
    if pathname.startswith("/ajax/"):
        return True
    if pathname in {
        "/robots.txt",
        "/sitemap.xml",
        "/crossdomain.xml",
        "/favicon.ico",
        "/clientaccesspolicy.xml",
        "/.well-known/security.txt",
    }:
        return True
    if pathname.startswith("/img/") or pathname.startswith("/font/"):
        return True
    return bool(re.search(r"\.(png|gif|jpe?g|ico|svg|woff2?|ttf|eot|bin)$", pathname, re.I))


def request_key(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname != HOST:
        return None
    path = parts.path or "/"
    if not wanted(path):
        return None
    kept = []
    for name, value in parse_qsl(parts.query, keep_blank_values=True):
        if name in QUERY_KEYS and value:
            kept.append(name if name != "action" else f"action={value}")
    suffix = "&".join(kept)
    return f"{path}?{suffix}" if suffix else path


def body_text(content: dict) -> str:
    text = content.get("text") or ""
    if not text:
        return ""
    if content.get("encoding") == "base64":
        try:
            return base64.b64decode(text).decode("utf-8", "replace")
        except (ValueError, TypeError):
            return ""
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hars", nargs="+", type=Path)
    parser.add_argument(
        "--userscript",
        type=Path,
        default=Path(__file__).with_name("f1-grab-artifacts.user.js"),
    )
    args = parser.parse_args()
    seeds = load_seeds(args.userscript)

    wire: Counter[tuple[str, str, int]] = Counter()
    actions: Counter[str] = Counter()
    methods: Counter[str] = Counter()
    literals: set[str] = set()
    hosts: Counter[str] = Counter()
    bare_sha: dict[str, str] = {}
    query_sha: list[tuple[str, str, int, int, str]] = []
    entries = 0

    for har_path in args.hars:
        har = json.loads(har_path.read_text(encoding="utf-8"))
        for entry in har.get("log", {}).get("entries", []):
            entries += 1
            req = entry.get("request") or {}
            url = req.get("url") or ""
            host = urlsplit(url).hostname or ""
            if host:
                hosts[host] += 1
            method = (req.get("method") or "?").upper()
            status = int((entry.get("response") or {}).get("status") or 0)
            key = request_key(url)
            content = (entry.get("response") or {}).get("content") or {}
            mime = (content.get("mimeType") or "").split(";")[0]
            path = urlsplit(url).path or ""
            if key:
                methods[method] += 1
                wire[(key.split("?", 1)[0], method, status)] += 1
                action = ""
                if "?" in key:
                    for part in key.split("?", 1)[1].split("&"):
                        if part.startswith("action="):
                            action = part.split("=", 1)[1]
                            actions[action] += 1
                text = body_text(content)
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
                if "?" not in key and method == "GET" and status == 200 and digest:
                    bare_sha.setdefault(path, digest)
                elif "?" in key and digest:
                    query_sha.append((path, action or "(no action name)", status, len(text), digest))
            if host == HOST and (
                mime in {"text/html", "application/javascript", "text/javascript", "text/css"}
                or path.endswith((".js", ".lp", ".html", ".css"))
            ):
                for found in PATH_RE.findall(body_text(content)):
                    found = found.split("?", 1)[0]
                    if wanted(found):
                        literals.add(found)

    wire_paths = {path for path, _, _ in wire}
    print(f"files: {len(args.hars)}")
    print(f"entries: {entries}")
    print(f"hosts: {len(hosts)} distinct (counts omitted)")
    print(f"on-host wanted requests: {sum(methods.values())}")
    print("methods:", ", ".join(f"{k}={v}" for k, v in methods.most_common()))
    print(f"distinct wanted paths on the wire: {len(wire_paths)}")
    print(f"path literals inside on-host bodies: {len(literals)}")
    print(f"literals not seen as a request: {len(literals - wire_paths)}")
    print(f"seed paths: {len(seeds)}")
    print(f"seeds missing from wire: {len(seeds - wire_paths)}")
    print(f"wire paths not in seeds: {len(wire_paths - seeds)}")
    print()
    print("## action names (counts)")
    for name, count in actions.most_common():
        print(f"- {name}: {count}")
    print()
    print("## gap pages")
    for path in GAP_PAGES:
        rows = sorted((m, s, n) for (p, m, s), n in wire.items() if p == path)
        lit = "literal" if path in literals else "no-literal"
        if rows:
            shown = ", ".join(f"{m} {s} x{n}" for m, s, n in rows)
            print(f"- {path}: wire {shown}; {lit}")
        else:
            print(f"- {path}: not requested; {lit}")
    print()
    print("## seeds missing from wire")
    for path in sorted(seeds - wire_paths):
        print(f"- {path}")
    print()
    print("## wire paths outside the seed lists")
    for path in sorted(wire_paths - seeds):
        rows = sorted((m, s) for (p, m, s) in wire if p == path)
        shown = ", ".join(f"{m} {s}" for m, s in rows)
        print(f"- {path} ({shown})")
    print()
    print("## query responses vs the same path with no query")
    seen_q = set()
    same = differ = unknown = 0
    for path, action, status, size, digest in query_sha:
        mark = (path, action, digest)
        if mark in seen_q:
            continue
        seen_q.add(mark)
        base = bare_sha.get(path)
        if not base:
            unknown += 1
            print(f"- {path} action={action}: HTTP {status} {size}B, bare page not in this HAR")
        elif base == digest:
            same += 1
            print(f"- {path} action={action}: HTTP {status} {size}B, SAME as bare page (action not demonstrated)")
        else:
            differ += 1
            print(f"- {path} action={action}: HTTP {status} {size}B, DIFFERS from bare page")
    print(f"unique query fingerprints: same={same} differs={differ} bare-missing={unknown}")
    print()
    print("## literals not requested")
    for path in sorted(literals - wire_paths):
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
