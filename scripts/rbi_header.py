#!/usr/bin/env python3
"""Parse Homeware BLI2 RBI static + TLV header (offline)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

TLV_NAMES = {
    0x02: "timestamp",
    0x08: "boardname",
    0x09: "prodname",
    0x0a: "varname",
    0x20: "tagpparserversion",
    0x81: "flashaddress",
}


def parse_header(data: bytes) -> dict[str, str]:
    if len(data) < 48:
        raise ValueError("file too small for BLI header")
    magic, fim, fia = struct.unpack("4s2s2s", data[0:8])
    prodid, varid = struct.unpack("12s12s", data[8:32])
    ver = data[32:36]
    _unk = data[36:40]
    data_off = int.from_bytes(data[40:44], "big")
    data_size = int.from_bytes(data[44:48], "big")
    if data_off > len(data):
        raise ValueError(f"data_offset {data_off} past EOF")

    header = data[:data_off]
    pos = 48 + 0x104
    dynamic: dict[str, str] = {}
    while pos < data_off:
        tag = header[pos]
        pos += 1
        length = header[pos]
        pos += 1
        value = header[pos : pos + length]
        pos += length
        name = TLV_NAMES.get(tag, f"id_{tag:02x}")
        if tag in (0x02, 0x81):
            dynamic[name] = "0x" + value.hex()
        else:
            dynamic[name] = value.decode("latin-1", errors="replace")

    return {
        "magic": magic.decode("ascii", errors="replace"),
        "fim": fim.decode("ascii", errors="replace"),
        "fia": fia.decode("ascii", errors="replace"),
        "prodid": prodid.split(b"\x00", 1)[0].decode("ascii", errors="replace"),
        "varid": varid.split(b"\x00", 1)[0].decode("ascii", errors="replace"),
        "version": f"{ver[0]}.{ver[1]:x}.{ver[2]:x}.{ver[3]:x}",
        "data_offset": str(data_off),
        "data_size": str(data_size),
        **dynamic,
    }


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "-")
    data = path.read_bytes() if path != Path("-") else sys.stdin.buffer.read()
    info = parse_header(data)
    for key in (
        "magic",
        "fim",
        "fia",
        "prodid",
        "varid",
        "version",
        "data_offset",
        "data_size",
        "timestamp",
        "boardname",
        "prodname",
        "varname",
        "tagpparserversion",
        "flashaddress",
    ):
        if key in info:
            print(f"{key}: {info[key]}")
    extra = [k for k in info if k not in {
        "magic", "fim", "fia", "prodid", "varid", "version",
        "data_offset", "data_size", "timestamp", "boardname",
        "prodname", "varname", "tagpparserversion", "flashaddress",
    }]
    for key in sorted(extra):
        print(f"{key}: {info[key]}")
    off = int(info["data_offset"])
    if off < len(data):
        print(f"payload_first_byte: 0x{data[off]:02x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
