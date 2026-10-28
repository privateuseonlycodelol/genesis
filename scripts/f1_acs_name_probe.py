#!/usr/bin/env python3
"""Bounded filename check against Telia ACS-style hosts for an F1 RBI.

Sibling of scripts/f1_rgw_name_probe.py. That script is fixed to
rgw.teliacompany.com:7547; this one takes the base URL so the community-listed
`/TCH/` directory on acs.telia.se:8888 and acs.telia.lt:8888 can be probed the
same way (findings/decomp-kickoff.md).

Each request is a one-byte ranged GET, so a hit never downloads the image.
A 200 is reported only; fetching the body needs a separate, approved step.
Pacing and the request cap are fixed in the code, not left to the caller.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

PACING_SECONDS = 5.0
TIMEOUT_SECONDS = 15.0
MAX_REQUESTS = 6

KNOWN_BASES = [
    "http://acs.telia.se:8888/TCH/",
    "http://acs.telia.lt:8888/TCH/",
]

# Control first: a 19.x name already listed in the repo for this directory.
# The 23.1.b name uses the same EWA1330_F1_gcnt-x_<version>-<build> shape.
NAMES = [
    "EWA1330_F1_gcnt-x_19.4.0856-4581012.rbi",
    "EWA1330_F1_gcnt-x_23.1.b.0448-7241017.rbi",
]


def targets(bases, names):
    """Return the full URL list, host-major, capped at MAX_REQUESTS."""
    urls = [base + name for base in bases for name in names]
    return urls[:MAX_REQUESTS]


def probe(url):
    """One ranged GET. Returns (status, content_length_or_reason)."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, resp.headers.get("Content-Length", "")
    except urllib.error.HTTPError as err:
        return err.code, err.reason
    except (urllib.error.URLError, OSError) as err:
        return "ERR", type(err).__name__


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="print targets and exit, no requests")
    args = parser.parse_args(argv)

    urls = targets(KNOWN_BASES, NAMES)
    if args.list:
        for url in urls:
            print(url)
        print(f"# {len(urls)} targets (cap {MAX_REQUESTS}), {PACING_SECONDS}s apart", file=sys.stderr)
        return 0

    for index, url in enumerate(urls):
        if index:
            time.sleep(PACING_SECONDS)
        status, detail = probe(url)
        print(f"{index + 1}/{len(urls)} {status} {detail} {url}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
