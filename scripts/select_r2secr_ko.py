#!/usr/bin/env python3
"""Pick a tools/secr r2secr*.ko from `uname -a` or a boot-log kernel line."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECR = ROOT / "tools" / "secr"

# vermagic substring -> module basename (newest / best match first within arch).
_AARCH64 = [
    ("4.1.52", "r2secr.arm64.4.1.52.ko"),
    ("4.1.45", "r2secr.arm64.4.1.45.ko"),
]
_ARM32 = [
    ("4.1.52", "r2secr.arm.4.1.38.ko"),  # lime.arm.4.1.52 is 32-bit but no r2secr 4.1.52 in tree
    ("4.1.38", "r2secr.arm.4.1.38.ko"),
    ("3.4.11-rt19", "r2secr.arm.3.4.11-rt19.ko"),
]
_MIPS = [
    ("3.4.11-rt19", "r2secr.mips.3.4.11-rt19.ko"),
    ("2.6", "r2secr.mips.2.6.ko"),
]


def _detect_arch(text: str) -> str:
    if re.search(r"\baarch64\b", text) or "ARM64" in text or "AArch64" in text:
        return "aarch64"
    if re.search(r"\barmv7\b", text) or "ARMv7" in text or "p2v8" in text:
        return "arm32"
    if "mips" in text.lower():
        return "mips"
    if re.search(r"\barm\b", text, re.I) and "aarch64" not in text.lower():
        return "arm32"
    return "unknown"


def pick_ko(uname_or_banner: str) -> tuple[Path | None, str]:
    arch = _detect_arch(uname_or_banner)
    table = {"aarch64": _AARCH64, "arm32": _ARM32, "mips": _MIPS}.get(arch, [])
    for ver, name in table:
        if ver in uname_or_banner:
            path = SECR / name
            if path.is_file():
                note = f"arch={arch} matched={ver} module={name}"
                return path, note
    return None, f"arch={arch} no_module_match"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "text",
        nargs="?",
        help="uname -a or kernel banner line (default: stdin)",
    )
    args = parser.parse_args()
    text = args.text if args.text else sys.stdin.read()
    path, note = pick_ko(text)
    print(note)
    if path:
        print(path)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
