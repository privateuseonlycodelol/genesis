#!/usr/bin/env python3
"""Offline, LF-indexed UART evidence inventory; matches are not security verdicts.

Output removes CR/ANSI for presentation and conservatively masks long hex,
MACs, UUIDs, IPv4-shaped strings, and labeled serials. This is a review aid,
not a general secret detector. Review output before publishing other logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
PART = re.compile(r'^0x([0-9a-fA-F]+)-0x([0-9a-fA-F]+)\s*:\s*"([^"\r\n]+)"$')
MARKER = re.compile(
    r"BTRM|U-Boot|DDR test|JTAG|FLD secure|digest sha256|Volume Boot Order|"
    r"SELECTED Image|Retry boot|Launch image|Fit checksum|emsa_pss|Authentication|"
    r"INFO:.*(?:key|Key|SDR|Security Node|anti.rollback|sec_exports|SEC_ITEM|TEE|Scrubbing)|"
    r"No export|copying em|eRIP|erip|BOOT-P|Booting\s*:|Bank duplication|"
    r"Chip ID|Broadcom B53|^RDP:|^DRAM:|Strap Register|WDT:|^In:|^Out:|^Err:|"
    r"Board Mnemonic|Secure Mode|Market ID|Read .*volume|^## |Description:|"
    r"Compression:|Data Start:|Data Size:|Architecture:|Load Address:|Entry Point:|"
    r"Hash algo:|Hash value:|Verifying Hash|RSVD:|Starting kernel|Linux version|"
    r"Machine model|earlycon:|bootconsole|console \[|Kernel command line|Memory:|"
    r"CPU features:|CPU: All|smp:|SMP:|psci:|^nand:|bcm63xx_nand|bad block|"
    r"Bad block|MTD partitions|cmdlinepart|^0x.* : |^ubi0:|ubiblock|device-mapper|"
    r"VFS:|W\+X|/sbin/init|^init:|^UBIFS|^mount_root:|HOMEWARE_CONFIG|ON_ACTIVE_BANK|"
    r"^procd:|activate this console|OSCK|keymanager|^ncr|^cryptodev|module license|"
    r"^platform regulatory|regulatory.db|ERROR|warning|failed|Failed|error:|"
    r"Empty key|sae_password|^BP3 status|BP3 Driver|HW acceleration|"
    r"Final FW path|Found section|FWID|GET_REVINFO|Host Driver|PCIe IPC.*Completed|"
    r"Register interface|^Compiled in|WAN.*type|Wan type|RTL8226|^WLSSK|"
    r"^OCSD|^apiosd|lxc.mount|^open:",
)


def display_line(raw: bytes) -> str:
    text = ANSI.sub("", raw.decode("utf-8", errors="replace")).replace("\r", "")
    # Preserve the ERROR label when lowercase hex and ERROR were concatenated.
    text = re.sub(r"[0-9a-f]{32,}(?=ERROR:)", "[REDACTED_HEX]", text)
    text = re.sub(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}", "[REDACTED_LONG_HEX]", text)
    text = re.sub(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b", "[REDACTED_UUID]", text)
    text = re.sub(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b", "[REDACTED_MAC]", text)
    if re.fullmatch(r"\s*(?:[0-9a-fA-F]{2}\s+){5}[0-9a-fA-F]{2}\s*", text):
        text = "[REDACTED_SPACED_MAC]"
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IPV4_SHAPE]", text)
    text = re.sub(r"(?i)(\b(?:serial(?: number|_num)?|s/n)\s*[:=]\s*)\S+", r"\1[REDACTED_SERIAL]", text)
    return "".join(c if c == "\t" or ord(c) >= 32 else "[CTRL]" for c in text)


def index_log(data: bytes) -> dict:
    raw_lines = data.split(b"\n")
    if data.endswith(b"\n"):
        raw_lines.pop()
    if not data:
        raw_lines = []
    selected = []
    partitions = []
    invalid_utf8 = []
    for number, raw in enumerate(raw_lines, 1):
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            invalid_utf8.append(number)
        text = display_line(raw)
        if MARKER.search(text):
            selected.append({"line": number, "text": text})
        match = PART.fullmatch(text)
        if match:
            start, end = int(match[1], 16), int(match[2], 16)
            if end <= start:
                raise ValueError(f"reversed/empty partition range at LF line {number}")
            partitions.append({"line": number, "name": match[3], "start": start,
                               "end_exclusive": end, "size": end - start})
    return {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
        "lf_count": data.count(b"\n"), "lf_lines": len(raw_lines),
        "cr_count": data.count(b"\r"), "esc_count": data.count(b"\x1b"),
        "final_lf": data.endswith(b"\n"), "invalid_utf8_lines": invalid_utf8,
        "line_convention": "1-based raw LF records, CR removed only for display",
        "warning": "Selected messages only; no access, key, or exploit classification. Review redactions before publication.",
        "partitions": partitions, "selected_lines": selected,
        "tail": [{"line": n, "text": display_line(raw_lines[n - 1])}
                 for n in range(max(1, len(raw_lines) - 34), len(raw_lines) + 1)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    print(json.dumps(index_log(args.log.read_bytes()), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
