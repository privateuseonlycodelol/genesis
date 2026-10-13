#!/usr/bin/env python3
"""Shared LAN pacing and login readiness — avoid nginx 503 from probe bursts.

Polls /login.lp at most once per interval (default 90s) while waiting for HTTP 200.
Does not reduce attack cases; use longer gaps between authenticated requests instead.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOST = "192.168.2.1"
LOGIN_URL = f"http://{HOST}/login.lp"

# Homeware nginx 503 often follows dozens of rapid authenticated hits; stay conservative.
DEFAULT_REQUEST_GAP_S = 3.0
LOGIN_POLL_INTERVAL_S = 90.0
LOGIN_POLL_MAX_WAIT_S = 1200.0
POST_READY_PAUSE_S = 45.0


def fetch_login_status(timeout_s: float = 10.0) -> int:
    """Single anonymous GET /login.lp; no cookie jar, no session."""
    req = urllib.request.Request(
        LOGIN_URL,
        headers={"User-Agent": "genesis-f1-pacing/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return int(resp.getcode())
    except urllib.error.HTTPError as err:
        return int(err.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def wait_until_login_ready(
    max_wait_s: float = LOGIN_POLL_MAX_WAIT_S,
    interval_s: float = LOGIN_POLL_INTERVAL_S,
    post_ready_pause_s: float = POST_READY_PAUSE_S,
) -> dict:
    """Block until login.lp is HTTP 200, polling sparingly."""
    started = time.monotonic()
    deadline = started + max_wait_s
    attempts = 0
    last_code = 0
    while time.monotonic() < deadline:
        attempts += 1
        last_code = fetch_login_status()
        elapsed = round(time.monotonic() - started, 1)
        print(
            json.dumps(
                {
                    "event": "login_poll",
                    "attempt": attempts,
                    "status": last_code,
                    "elapsed_s": elapsed,
                }
            ),
            flush=True,
        )
        if last_code == 200:
            if post_ready_pause_s > 0:
                print(
                    json.dumps(
                        {
                            "event": "post_ready_pause",
                            "seconds": post_ready_pause_s,
                        }
                    ),
                    flush=True,
                )
                time.sleep(post_ready_pause_s)
            return {
                "ready": True,
                "attempts": attempts,
                "elapsed_s": round(time.monotonic() - started, 1),
            }
        if last_code == 503:
            sleep_s = interval_s
        elif last_code == 0:
            sleep_s = min(interval_s, 60.0)
        else:
            sleep_s = interval_s
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(sleep_s, remaining))
    return {
        "ready": False,
        "attempts": attempts,
        "last_status": last_code,
        "elapsed_s": round(time.monotonic() - started, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-wait", type=float, default=LOGIN_POLL_MAX_WAIT_S)
    parser.add_argument("--interval", type=float, default=LOGIN_POLL_INTERVAL_S)
    parser.add_argument("--post-ready-pause", type=float, default=POST_READY_PAUSE_S)
    parser.add_argument("--once", action="store_true", help="single status check, no wait loop")
    args = parser.parse_args()
    if args.once:
        code = fetch_login_status()
        print(json.dumps({"status": code}))
        return 0 if code == 200 else 1
    outcome = wait_until_login_ready(
        max_wait_s=args.max_wait,
        interval_s=args.interval,
        post_ready_pause_s=args.post_ready_pause,
    )
    print(json.dumps({"outcome": outcome}), flush=True)
    return 0 if outcome["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
