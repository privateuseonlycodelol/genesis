"""Decode the F1 GCNT-X BOOTREQUEST's boot-file field and anomalous DHCP options.

Finding (2026-10-27, offline, see findings/f1-bootp-lan-2026-10-13.md addendum):
the device's BOOTREQUEST packets carry a 128-byte "file" field containing TWO
null-terminated strings back to back ("GCNT-X\\0" + a second variant string),
and populate DHCP options 1 (Subnet Mask), 3 (Router) with non-zero,
non-address-shaped values that decode as ASCII fragments. This looks like an
uninitialized/reused buffer leaking adjacent memory into option fields a
BOOTREQUEST client would not normally need to set, rather than intentional
protocol content. This module only decodes already-captured bytes; it sends
nothing and does not re-interpret pcaps on its own.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BootFileDecode:
    raw: bytes
    strings: list[str]  # null-terminated ASCII runs found before the first all-zero tail


def decode_boot_file_field(field: bytes) -> BootFileDecode:
    """Split a 128-byte BOOTP 'file' field into its null-terminated ASCII runs.

    A spec-conformant client sets one string and zero-pads the rest. This
    finding is that GCNT-X's field instead holds *two* such runs back to back.
    """
    strings: list[str] = []
    current = bytearray()
    for b in field:
        if b == 0:
            if current:
                strings.append(current.decode("ascii", errors="replace"))
                current = bytearray()
            # else: just padding, keep scanning in case more text follows
        else:
            current.append(b)
    if current:
        strings.append(current.decode("ascii", errors="replace"))
    return BootFileDecode(raw=field, strings=strings)


def decode_suspect_option(value: bytes) -> str:
    """Render an option's raw value as hex and best-effort ASCII, no interpretation."""
    ascii_repr = "".join(chr(c) if 32 <= c < 127 else "." for c in value)
    return f"hex={value.hex()} ascii={ascii_repr!r}"


def walk_vendor_specific(blob: bytes, skip_prefix: int = 0) -> list[tuple[int, bytes]]:
    """Best-effort tag/len/value walk of a DHCP option-43 payload.

    Returns (offset, raw_value) pairs. This is diagnostic only: the GCNT-X
    blob analyzed on 2026-10-27 does NOT parse as clean TLV end-to-end (some
    claimed lengths overrun the buffer), which itself supports the
    leaked-memory hypothesis over an intentional, well-formed vendor schema.
    Returns whatever it can walk before a length would overrun the buffer.
    """
    out: list[tuple[int, bytes]] = []
    i = skip_prefix
    n = len(blob)
    while i < n:
        tag = blob[i]
        if tag == 0xFF:
            break
        if tag == 0x00:
            i += 1
            continue
        if i + 1 >= n:
            break
        length = blob[i + 1]
        if i + 2 + length > n:
            break
        out.append((i, blob[i + 2 : i + 2 + length]))
        i += 2 + length
    return out
