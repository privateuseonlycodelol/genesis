#!/usr/bin/env python3
"""Fix Chrome HAR exports that use serverIPAddress \"\" so REA har-schema accepts them."""
import argparse
import json
import sys
from pathlib import Path


def sanitize(data: dict) -> int:
    fixed = 0
    fallback = "192.168.2.1"
    for entry in data.get("log", {}).get("entries", []):
        ip = entry.get("serverIPAddress")
        if ip is None or ip == "":
            entry["serverIPAddress"] = fallback
            fixed += 1
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_har", type=Path)
    parser.add_argument("output_har", type=Path)
    parser.add_argument(
        "--fallback-ip",
        default="192.168.2.1",
        help="IPv4 to use when serverIPAddress is missing or empty",
    )
    args = parser.parse_args()
    data = json.loads(args.input_har.read_text())
    fixed = 0
    fallback = args.fallback_ip
    for entry in data.get("log", {}).get("entries", []):
        ip = entry.get("serverIPAddress")
        if ip is None or ip == "":
            entry["serverIPAddress"] = fallback
            fixed += 1
    args.output_har.parent.mkdir(parents=True, exist_ok=True)
    args.output_har.write_text(json.dumps(data))
    print(f"fixed={fixed} entries={len(data.get('log', {}).get('entries', []))} -> {args.output_har}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
