#!/usr/bin/env python3
"""Resolve snprintf format strings for every system() site in wps_pbcd (v2).

For each system@plt call, scan the preceding window for every pc-relative
literal load+add pair, resolve each to a string, and report the ones that
look like command formats.
"""
import re
import struct
import sys

ASM = sys.argv[1] if len(sys.argv) > 1 else "wps_pbcd.asm"
BIN = sys.argv[2] if len(sys.argv) > 2 else "/Users/nils/genesis/artifacts/firmware/rom-2026-11-06/rom/sbin/wps_pbcd"
BASE = 0x10000

data = open(BIN, "rb").read()
lines = open(ASM, errors="replace").read().splitlines()

ins = []
for ln in lines:
    m = re.match(r"^\s*([0-9a-f]{5,8}):\s+([0-9a-f]{8})\s+(.*)$", ln)
    if m:
        ins.append((int(m.group(1), 16), m.group(3).strip()))


def resolve_all():
    sites = [i for i, (a, t) in enumerate(ins) if "system@plt" in t and t.startswith("bl")]
    for si in sites:
        addr = ins[si][0]
        found = []
        for j in range(max(si - 45, 0), si):
            a, t = ins[j]
            m = re.match(r"ldr\s+(\w+), \[pc, #-?\w+\]\s+@ (0x[0-9a-f]+)", t)
            if not m:
                continue
            reg, pool = m.group(1), int(m.group(2), 16)
            for k in range(j + 1, si):
                a2, t2 = ins[k]
                if re.match(rf"add\s+{reg}, pc, {reg}$", t2):
                    word = struct.unpack_from("<I", data, pool - BASE)[0]
                    off = (a2 + 8 + word) - BASE
                    if 0 <= off < len(data):
                        end = data.find(b"\x00", off)
                        s = data[off:end].decode("latin1")
                        if s and s not in [x[1] for x in found]:
                            found.append((a, s))
                    break
        cmd = [s for _, s in found if "%" in s or s.startswith(("hostapd", "wpa", "ifconfig", "iw", "ubus", "/"))]
        print(f"system@{addr:#x}:")
        for a, s in found[-6:]:
            print(f"   [{a:#x}] {s!r}")


resolve_all()
