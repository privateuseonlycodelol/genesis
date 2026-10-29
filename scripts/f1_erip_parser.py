#!/usr/bin/env python3
"""Technicolor eRIPv2 partition parser and decryptor.

Decompiled and verified from ripdrv.arm.3.4.11-rt19.ko and surrealiz3's eripv2
tooling for Vantiva / Technicolor Gateways (such as Telia F1 / GCNT-X).

eRIPv2 Binary Layout:
  Data area starts at offset 0.
  Index records are 18 bytes each, placed at the end of the partition and
  growing backwards until ID 0xFFFF is reached:
    [item_id: uint16_be, addr: uint32_be ^ 0x20000, attr_lo: uint32_be,
     attr_hi: uint32_be, length: uint32_be]

Attributes (attr_hi, active low):
  ATTR_EIK_SIGN = 0x10000000 (signed with 2048-bit RSA EIK via RSA-PSS SHA-256)
  ATTR_ECK_ENCR = 0x08000000 (encrypted with 128-bit AES-CBC ECK)
  ATTR_MCV_SIGN = 0x04000000 (manufacturer certificate validation)
  ATTR_BEK_ENCR = 0x02000000 (base/board encryption key)
  ATTR_VALID    = 0x20000000
  ATTR_LOCKED   = 0x40000000
"""

from __future__ import annotations

import argparse
import binascii
import json
import os
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Crypto.Cipher import AES

# Known RIP Item Identifiers (verified from ripdrv and eripv2.py)
RIP_ITEM_NAMES: Dict[int, str] = {
    0x0000: "RIP_ID_LOWER_CHECKSUM",
    0x0002: "RIP_ID_UNPROT_FREE1",
    0x0004: "RIP_ID_PART_NBR_VARIANT",
    0x0010: "RIP_ID_ICS",
    0x0012: "RIP_ID_BOARD_SERIAL_NBR",
    0x0022: "RIP_ID_FACTORY_RELEASE_DATE",
    0x0028: "RIP_ID_FIA",
    0x002C: "RIP_ID_HANDOVER_DATE",
    0x0032: "RIP_ID_LAN_ADDR",
    0x0038: "RIP_ID_COMPANY_ID",
    0x003C: "RIP_ID_FACTORY_ID",
    0x0040: "RIP_ID_BOARD_NAME",
    0x0048: "RIP_ID_MEMORY_CONFIG",
    0x004C: "RIP_ID_USB_LAN_ADDR",
    0x0083: "RIP_ID_MODEM_ACCESS_CODE",
    0x0088: "RIP_ID_SECURE_REMOTE_MANG_PASWD",
    0x008D: "RIP_ID_WLAN_LAN_ADDR",
    0x0100: "RIP_ID_PUBLIC_DSA_SYST",
    0x0101: "RIP_ID_PUBLIC_DSA_RESC",
    0x0102: "RIP_ID_MODELNAME",
    0x0103: "RIP_ID_PRODUCT_CLASS",
    0x0104: "RIP_ID_LB_CLIENT_CERTIFICATE",
    0x0105: "RIP_ID_PRIVATE_KEY",
    0x0106: "RIP_ID_H235_KEY",
    0x0107: "RIP_ID_RANDOM_KEY_A",
    0x0108: "RIP_ID_RANDOM_KEY_B",
    0x0109: "RIP_ID_KEY_PWD",
    0x0112: "RIP_ID_RALINK_CALIBRATION_DATA",
    0x0115: "RIP_ID_CHIPID",
    0x0116: "RIP_ID_PUBLIC_RSA_KEY",
    0x0118: "RIP_ID_SERIAL_NBR_BYTES",
    0x011A: "RIP_ID_CLIENT_CERTIFICATE",
    0x011B: "RIP_ID_OPTICAL_FRONT_END",
    0x011C: "RIP_ID_DUID_LLT",
    0x011E: "RIP_ID_EIK",
    0x011F: "RIP_ID_ECK",
    0x0120: "RIP_ID_OSIK",
    0x0121: "RIP_ID_OSCK",
    0x0122: "RIP_ID_RESTRICTED_DOWNGR_TS",
    0x0123: "RIP_ID_RESTRICTED_DOWNGR_OPT",
    0x0124: "RIP_ID_GENERIC_ACCESS_KEY_LIST",
    0x0125: "RIP_ID_UNLOCK_TAG",
    0x0127: "RIP_ID_OLYMPUS_IK",
    0x0128: "RIP_ID_OLYMPUS_CK",
    0x4001: "RIP_ID_ID_DECT_CFG",
    0x8001: "RIP_ID_PRODUCT_ID",
    0x8003: "RIP_ID_VARIANT_ID",
}

# Attribute bitmasks (checked with ~attr_hi in ripdrv)
ATTR_EIK_SIGN = 0x10000000
ATTR_ECK_ENCR = 0x08000000
ATTR_MCV_SIGN = 0x04000000
ATTR_BEK_ENCR = 0x02000000
ATTR_VALID    = 0x20000000
ATTR_LOCKED   = 0x40000000
INDEX_RECORD_SIZE = 18


@dataclass
class RipItem:
    item_id: int
    name: str
    addr: int
    length: int
    attr_lo: int
    attr_hi: int
    is_encrypted: bool
    is_signed: bool
    is_locked: bool
    is_valid: bool
    raw_data: bytes
    decrypted_data: Optional[bytes] = None
    decrypted_ok: bool = False


def decrypt_item_eck(raw_payload: bytes, eck_key: bytes) -> Tuple[Optional[bytes], Optional[bytes]]:
    """Decrypt an AES-128-CBC eRIP item using the 16-byte ECK key.

    Returns (plain_data, signature_bytes).
    """
    if len(raw_payload) < 32:
        return None, None
    iv = raw_payload[:16]
    ciphertext = raw_payload[16:]
    if len(ciphertext) % 16 != 0:
        return None, None

    cipher = AES.new(eck_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    pad = decrypted[-1]
    if pad < 1 or pad > 16:
        # Invalid padding
        return None, None
    unpadded = decrypted[:-pad]

    # If payload is signed, the last 256 bytes are RSA-2048 signature
    if len(unpadded) >= 256:
        data = unpadded[:-256]
        sig = unpadded[-256:]
        return data, sig
    return unpadded, None


def parse_eripv2_image(image_bytes: bytes, eck_key: Optional[bytes] = None) -> List[RipItem]:
    """Parse an eRIPv2 partition image and return all detected items."""
    total_len = len(image_bytes)
    if total_len < INDEX_RECORD_SIZE + 4:
        raise ValueError(f"Image too small ({total_len} bytes) to contain eRIPv2 structure")

    # Exclude trailing 4 bytes (CRC32/footer)
    buffer = image_bytes[: total_len - 4]
    items: List[RipItem] = []
    seen_ids = set()

    step = 1
    while True:
        record_offset = len(buffer) - (INDEX_RECORD_SIZE * step)
        if record_offset < 0:
            break
        record_bytes = buffer[record_offset : record_offset + INDEX_RECORD_SIZE]
        step += 1

        item_id = struct.unpack(">H", record_bytes[0:2])[0]
        if item_id == 0xFFFF:
            # End of index table marker
            break

        addr_raw = struct.unpack(">L", record_bytes[2:6])[0]
        addr = addr_raw ^ 0x20000
        attr_lo = struct.unpack(">L", record_bytes[6:10])[0]
        attr_hi = struct.unpack(">L", record_bytes[10:14])[0]
        length = struct.unpack(">L", record_bytes[14:18])[0]

        if addr + length > len(buffer) or addr < 0:
            # Corrupt address or out of bounds
            continue

        raw_data = buffer[addr : addr + length]
        is_encrypted = bool(~attr_hi & ATTR_ECK_ENCR)
        is_signed = bool(~attr_hi & ATTR_EIK_SIGN)
        is_locked = bool(attr_hi & ATTR_LOCKED)
        is_valid = bool(~attr_hi & ATTR_VALID)

        name = RIP_ITEM_NAMES.get(item_id, f"RIP_ID_0x{item_id:04X}")

        item = RipItem(
            item_id=item_id,
            name=name,
            addr=addr,
            length=length,
            attr_lo=attr_lo,
            attr_hi=attr_hi,
            is_encrypted=is_encrypted,
            is_signed=is_signed,
            is_locked=is_locked,
            is_valid=is_valid,
            raw_data=raw_data,
        )

        if is_encrypted and eck_key is not None:
            plain, _ = decrypt_item_eck(raw_data, eck_key)
            if plain is not None:
                item.decrypted_data = plain
                item.decrypted_ok = True
        elif not is_encrypted:
            item.decrypted_data = raw_data
            item.decrypted_ok = True

        items.append(item)
        seen_ids.add(item_id)

    return items


def dump_items_to_directory(items: List[RipItem], output_dir: Path) -> None:
    """Dump parsed and decrypted items to an output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for item in items:
        fn_base = f"{item.item_id:04x}_{item.name}"
        data_to_save = item.decrypted_data if item.decrypted_data is not None else item.raw_data
        out_file = output_dir / f"{fn_base}.bin"
        out_file.write_bytes(data_to_save)

        manifest.append({
            "item_id": f"0x{item.item_id:04x}",
            "name": item.name,
            "length": item.length,
            "encrypted": item.is_encrypted,
            "signed": item.is_signed,
            "locked": item.is_locked,
            "decrypted": item.decrypted_ok,
            "file": out_file.name,
        })

    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to raw eRIP partition image (e.g., mtd5 / eripv2_bak)")
    parser.add_argument("--eck", type=str, help="16-byte ECK key in hex (e.g. from keystore slot 0x114)")
    parser.add_argument("--out-dir", type=Path, help="Directory to extract item binaries and manifest")
    parser.add_argument("--json", action="store_true", help="Print item summary in JSON format")

    args = parser.parse_args(argv)

    if not args.image.exists():
        print(f"Error: image file {args.image} does not exist", file=sys.stderr)
        return 1

    eck_bytes = None
    if args.eck:
        try:
            eck_bytes = bytes.fromhex(args.eck.replace(" ", "").strip())
            if len(eck_bytes) != 16:
                print("Error: ECK must be exactly 16 bytes (32 hex characters)", file=sys.stderr)
                return 1
        except ValueError as err:
            print(f"Error parsing hex ECK: {err}", file=sys.stderr)
            return 1

    image_data = args.image.read_bytes()
    try:
        items = parse_eripv2_image(image_data, eck_key=eck_bytes)
    except Exception as err:
        print(f"Error parsing eRIPv2 image: {err}", file=sys.stderr)
        return 1

    print(f"Parsed {len(items)} items from {args.image} ({len(image_data)} bytes)")
    for item in items:
        status = "PLAINTEXT"
        if item.is_encrypted:
            status = "DECRYPTED" if item.decrypted_ok else "ENCRYPTED [LOCKED]"
        print(f"  [0x{item.item_id:04x}] {item.name:<32} Offset: 0x{item.addr:06x}  Len: {item.length:<6} [{status}]")

    if args.out_dir:
        dump_items_to_directory(items, args.out_dir)
        print(f"Dumped {len(items)} items to {args.out_dir}")

    if args.json:
        summary = [{
            "id": f"0x{i.item_id:04x}",
            "name": i.name,
            "length": i.length,
            "encrypted": i.is_encrypted,
            "decrypted": i.decrypted_ok,
            "locked": i.is_locked,
        } for i in items]
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
