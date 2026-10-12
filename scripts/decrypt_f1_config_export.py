#!/usr/bin/env python3
"""Decrypt or verify Technicolor-style F1 configuration exports offline.

Format (cross-version analogue, verified on GCNT-X 23.1.b exports):
  ASCII header lines, blank line, 16-byte IV, AES-256-CBC ciphertext, 20-byte HMAC-SHA1.

The header fields CIPHERKEY and SIGNATUREKEY are key-slot labels (observed value ``GW``),
not embedded AES/HMAC material. Decryption requires ``RIP_ID_RANDOM_KEY_B`` (64 bytes),
typically from ``/proc/rip/0108`` or ``eripv2.py`` on an MTD dump — same model as
``tools/secr/cfg_dec.py`` and the public technicolor-config-decrypt PoC.

This tool never prints key bytes, header field values, or decrypted content.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
from dataclasses import dataclass
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

KNOWN_HEADER_FIELDS = (
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


@dataclass(frozen=True)
class ConfigEnvelope:
    raw: bytes
    field_names: tuple[str, ...]
    cipher_key_label: str
    signature_key_label: str
    header_with_sep: bytes
    iv: bytes
    ciphertext: bytes
    signature: bytes

    @property
    def signed_prefix(self) -> bytes:
        return self.raw[: -len(self.signature)]


def _parse_header_lines(header_bytes: bytes) -> tuple[tuple[str, ...], dict[str, str]]:
    names: list[str] = []
    fields: dict[str, str] = {}
    for line in header_bytes.split(b"\n"):
        if not line:
            continue
        split_at = -1
        for sep in (b"=", b":"):
            position = line.find(sep)
            if position >= 0:
                split_at = position
                break
        if split_at < 0:
            continue
        name = line[:split_at].decode("ascii")
        value = line[split_at + 1 :].decode("utf-8", errors="replace")
        upper = name.upper()
        names.append(upper)
        fields[upper] = value
    return tuple(names), fields


def parse_envelope(data: bytes) -> ConfigEnvelope:
    delimiter = data.find(b"\n\n")
    if delimiter < 0:
        raise ValueError("header separator not found")
    header_bytes = data[:delimiter]
    body_start = delimiter + 2
    if len(data) < body_start + 16 + 20:
        raise ValueError("envelope too short")
    field_names, fields = _parse_header_lines(header_bytes)
    iv = data[body_start : body_start + 16]
    signature = data[-20:]
    ciphertext = data[body_start + 16 : -20]
    if len(ciphertext) % 16 != 0:
        raise ValueError("ciphertext length is not block-aligned")
    return ConfigEnvelope(
        raw=data,
        field_names=field_names,
        cipher_key_label=fields.get("CIPHERKEY", ""),
        signature_key_label=fields.get("SIGNATUREKEY", ""),
        header_with_sep=data[:body_start],
        iv=iv,
        ciphertext=ciphertext,
        signature=signature,
    )


def load_randb(path: Path) -> bytes:
    material = path.read_bytes()
    if len(material) < 64:
        raise ValueError("randb material shorter than 64 bytes")
    return material[:64]


def verify_hmac(randb: bytes, envelope: ConfigEnvelope) -> bool:
    digest = hmac.new(randb[:64], envelope.signed_prefix, hashlib.sha1).digest()
    return digest == envelope.signature


def decrypt(randb: bytes, envelope: ConfigEnvelope) -> bytes:
    cipher = AES.new(randb[:32], AES.MODE_CBC, envelope.iv)
    padded = cipher.decrypt(envelope.ciphertext)
    return unpad(padded, 16)


def plaintext_hints(plaintext: bytes) -> dict[str, object]:
    sample = plaintext[:4096]
    return {
        "length": len(plaintext),
        "sha256_prefix": hashlib.sha256(plaintext).hexdigest()[:16],
        "starts_with_angle": plaintext.startswith(b"<"),
        "contains_config_tag": b"<config" in sample or b"<?xml" in sample,
        "printable_ratio_head": round(
            sum(32 <= byte < 127 or byte in (9, 10, 13) for byte in sample) / max(len(sample), 1),
            3,
        ),
    }


def build_envelope(
    header_lines: list[str],
    randb: bytes,
    plaintext: bytes,
    iv: bytes,
) -> bytes:
    from Crypto.Util.Padding import pad

    header = "\n".join(header_lines).encode("ascii") + b"\n\n"
    if len(iv) != 16:
        raise ValueError("iv must be 16 bytes")
    ciphertext = AES.new(randb[:32], AES.MODE_CBC, iv).encrypt(pad(plaintext, 16))
    signed = header + iv + ciphertext
    signature = hmac.new(randb[:64], signed, hashlib.sha1).digest()
    return signed + signature


def _inspect(envelope: ConfigEnvelope) -> None:
    print("field_names=" + "|".join(envelope.field_names))
    print(f"cipher_key_label_len={len(envelope.cipher_key_label)}")
    print(f"signature_key_label_len={len(envelope.signature_key_label)}")
    print(f"header_end_offset={len(envelope.header_with_sep) - 2}")
    print(f"body_start_offset={len(envelope.header_with_sep)}")
    print(f"ciphertext_length={len(envelope.ciphertext)}")
    print(f"signature_length={len(envelope.signature)}")
    print(
        "known_field_order="
        + str(envelope.field_names == tuple(KNOWN_HEADER_FIELDS)).lower()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="saved config.bin export")
    parser.add_argument(
        "--randb",
        type=Path,
        help="64-byte RIP_ID_RANDOM_KEY_B material (not printed)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write decrypted plaintext here (never printed)",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="print allowlisted structural metadata only",
    )
    args = parser.parse_args()

    try:
        envelope = parse_envelope(args.config.read_bytes())
    except (OSError, ValueError):
        print("parse_failed=true")
        return 2

    if args.inspect_only:
        _inspect(envelope)
        return 0

    if args.randb is None:
        print("error=randb_required")
        return 2

    try:
        randb = load_randb(args.randb)
    except (OSError, ValueError):
        print("randb_load_failed=true")
        return 2

    hmac_ok = verify_hmac(randb, envelope)
    print(f"hmac_ok={str(hmac_ok).lower()}")
    if not hmac_ok:
        return 1

    try:
        plaintext = decrypt(randb, envelope)
    except ValueError:
        print("decrypt_failed=true")
        return 1

    hints = plaintext_hints(plaintext)
    for key, value in hints.items():
        print(f"{key}={value}")

    if args.output is not None:
        try:
            args.output.write_bytes(plaintext)
        except OSError:
            print("write_failed=true")
            return 2
        print("wrote_plaintext=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
