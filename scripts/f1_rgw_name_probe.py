#!/usr/bin/env python3
"""Bounded filename check against Telia's RGW host for a 23.1.b RBI.

Candidates are derived from the 19.x names that already resolved on this host
(`1940507x4581025.rbi` returned 200 per findings/gcnt-x-19x-deep.md):
    <major><minor><build4>x<buildno>.rbi
with the 23.1.b.0448 version and build numbers seen in the Telia Finland
threads (7241004, 7241016) and the owned unit (7241017).

Each request is a one-byte ranged GET, so a hit never downloads the image.
A 200 is reported only; fetching the body needs a separate, approved step.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

HOST = "https://rgw.teliacompany.com:7547/"
MAX_REQUESTS = 8
PACING_SECONDS = 5.0
TIMEOUT_SECONDS = 15.0

VERSION_PREFIXES = ["2310448x", "231b0448x"]
BUILD_NUMBERS = ["7241017", "7241016", "7241004"]


def candidates():
    """Return the bounded list of filenames, in request order, capped."""
    names = [f"{prefix}{build}.rbi" for build in BUILD_NUMBERS for prefix in VERSION_PREFIXES]
    names.append("2310448-gcnt-x-7241017.rbi")
    names.append("231b0448-gcnt-x-7241017.rbi")
    return names[:MAX_REQUESTS]


def probe(name):
    """One ranged GET. Returns (status, content_length_or_reason)."""
    req = urllib.request.Request(HOST + name, headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, resp.headers.get("Content-Length", "")
    except urllib.error.HTTPError as err:
        return err.code, err.reason
    except (urllib.error.URLError, OSError) as err:
        return "ERR", type(err).__name__


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="print candidates and exit, no requests")
    parser.add_argument(
        "--name",
        action="append",
        help="probe this filename instead of the built-in list; repeat for several (cap %d)" % MAX_REQUESTS,
    )
    args = parser.parse_args(argv)

    names = args.name if args.name else candidates()
    if len(names) > MAX_REQUESTS:
        parser.error(f"{len(names)} names exceeds the cap of {MAX_REQUESTS}")
    if args.list:
        for name in names:
            print(HOST + name)
        print(f"# {len(names)} candidates (cap {MAX_REQUESTS}), {PACING_SECONDS}s apart", file=sys.stderr)
        return 0

    for index, name in enumerate(names):
        if index:
            time.sleep(PACING_SECONDS)
        status, detail = probe(name)
        print(f"{index + 1}/{len(names)} {status} {detail} {HOST + name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
