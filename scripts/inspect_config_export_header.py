#!/usr/bin/env python3
"""Print allowlisted metadata from a saved F1 config export; never print values.

This deliberately narrow helper is for offline inspection. Unknown field names,
field values, raw bytes, and the input path are never emitted.
"""

from __future__ import annotations

import argparse
from pathlib import Path


KNOWN_FIELDS = (
    "PREAMBLE",
    "BACKUPVERSION",
    "BOARDMNEMONIC",
    "PRODUCTNAME",
    "SERIALNUMBER",
    "MAC",
    "BUILDVERSION",
    "CIPHERKEY",
    "SIGNATUREKEY",
)
KNOWN_FIELD_SET = set(KNOWN_FIELDS)

# Exact conventional size/length labels only. These are used for comparison,
# never printed, and intentionally exclude names such as CIPHERKEY.
LENGTH_FIELD_NAMES = {
    "LEN",
    "LENGTH",
    "SIZE",
    "BYTES",
    "OFFSET",
    "COUNT",
    "TOTAL",
    "PAYLOADLEN",
    "PAYLOADLENGTH",
    "CIPHERLEN",
    "CIPHERLENGTH",
    "FILESIZE",
    "FILELENGTH",
    "HEADERLEN",
    "HEADERLENGTH",
    "PAYLOAD_LEN",
    "PAYLOAD_LENGTH",
    "CIPHER_LEN",
    "CIPHER_LENGTH",
    "FILE_SIZE",
    "FILE_LENGTH",
    "HEADER_LEN",
    "HEADER_LENGTH",
}


def inspect(data: bytes) -> dict[str, object]:
    """Return sanitized facts from the line header and candidate framing spans."""
    delimiter = data.find(b"\n\n")
    if delimiter < 0:
        raise ValueError("header separator not found")

    header = data[:delimiter]
    parsed: list[tuple[str, bytes]] = []
    unknown_fields = 0
    for line in header.split(b"\n"):
        if not line:
            continue
        equals = line.find(b"=")
        colon = line.find(b":")
        positions = [position for position in (equals, colon) if position >= 0]
        if not positions:
            continue
        split_at = min(positions)
        try:
            name = line[:split_at].decode("ascii")
        except UnicodeDecodeError:
            unknown_fields += 1
            continue
        if not name or not all(char.isalnum() or char in "_.-" for char in name):
            unknown_fields += 1
            continue
        parsed.append((name.upper(), line[split_at + 1 :]))
        if name.upper() not in KNOWN_FIELD_SET:
            unknown_fields += 1

    total = len(data)
    body_start = delimiter + 2
    spans = {
        "total": total,
        "header_end": delimiter,
        "after_header": total - body_start,
        "after_header_minus20": total - body_start - 20,
        "candidate_ciphertext": total - body_start - 16 - 20,
        "trailer_offset": total - 20,
    }

    lengths: list[int] = []
    for name, raw_value in parsed:
        if name not in LENGTH_FIELD_NAMES or not raw_value or not raw_value.isdigit():
            continue
        lengths.append(int(raw_value))

    return {
        "field_names": [name for name, _ in parsed if name in KNOWN_FIELD_SET],
        "unknown_field_count": unknown_fields,
        "delimiter_offset": delimiter,
        "body_start_offset": body_start,
        "length_field_count": sum(name in LENGTH_FIELD_NAMES for name, _ in parsed),
        "numeric_declared_length_count": len(lengths),
        "span_matches": {
            name: any(length == span for length in lengths)
            for name, span in spans.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="saved export file to inspect offline")
    args = parser.parse_args()
    try:
        result = inspect(args.file.read_bytes())
    except (OSError, ValueError):
        # Do not echo paths or exception text; either could contain sensitive data.
        print("inspection_failed=true")
        return 2

    print("field_names=" + "|".join(result["field_names"]))
    print(f"unknown_field_count={result['unknown_field_count']}")
    print(f"delimiter_offset={result['delimiter_offset']}")
    print(f"body_start_offset={result['body_start_offset']}")
    print(f"length_field_count={result['length_field_count']}")
    print(f"numeric_declared_length_count={result['numeric_declared_length_count']}")
    print("span_matches=" + ",".join(
        f"{name}:{str(matches).lower()}"
        for name, matches in result["span_matches"].items()
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
