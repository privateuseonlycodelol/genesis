#!/usr/bin/env python3
"""Offline RBI parser/decryptor correctness probes.

Real-firmware checks use the ignored GCNT-X 19.x reference RBI. Synthetic
payloads use public, deterministic dummy keys and establish implementation
behavior only; they are not evidence of successful firmware decryption.
"""
from __future__ import annotations

import hashlib
import struct
import sys
import zlib
from pathlib import Path

import Crypto
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import cryptography
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from attempt_rbi_decrypt import b7_first_layer_oracle, process_payload  # noqa: E402
from rbi_header import parse_header  # noqa: E402

REFERENCE = ROOT / "artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi"
REFERENCE_SHA256 = "2d46e728b73fda7fd2f5af2d5a4b06f8a5d5dfb1409bdaebe1f6447b6b1453de"
FIXED_HEADER_SIZE = 0x134


def independent_header(data: bytes) -> tuple[dict[str, object], dict[int, bytes]]:
    """Minimal independent struct/TLV reader for the fields used here."""
    fields: dict[str, object] = {
        "magic": data[0:4],
        "fim": data[4:6],
        "fia": data[6:8],
        "prodid": data[8:20].split(b"\0", 1)[0],
        "varid": data[20:32].split(b"\0", 1)[0],
        "version": data[32:36],
        "data_offset": struct.unpack_from(">I", data, 40)[0],
        "data_size": struct.unpack_from(">I", data, 44)[0],
    }
    end = int(fields["data_offset"])
    pos = FIXED_HEADER_SIZE
    tlvs: dict[int, bytes] = {}
    while pos < end:
        tag = data[pos]
        size = data[pos + 1]
        pos += 2
        value = data[pos : pos + size]
        if len(value) != size:
            raise ValueError("truncated TLV in independent reader")
        tlvs[tag] = value
        pos += size
    if pos != end:
        raise ValueError("TLV region did not end exactly at data_offset")
    return fields, tlvs


def make_header(data_offset: int, data_size: int, magic: bytes = b"BLI2") -> bytes:
    header = bytearray(FIXED_HEADER_SIZE)
    header[0:4] = magic
    header[4:6] = b"23"
    header[6:8] = b"KN"
    header[8:20] = b"0".ljust(12, b"\0")
    header[20:32] = b"TL".ljust(12, b"\0")
    header[40:44] = struct.pack(">I", data_offset)
    header[44:48] = struct.pack(">I", data_size)
    return bytes(header)


def strict_unpad(data: bytes) -> bytes:
    count = data[-1]
    if not 1 <= count <= 16 or data[-count:] != bytes([count]) * count:
        raise AssertionError("independent AES control had invalid PKCS#7 padding")
    return data[:-count]


def expect_value_error(call, message_fragment: str) -> None:
    try:
        call()
    except ValueError as exc:
        if message_fragment not in str(exc):
            raise AssertionError(f"unexpected ValueError: {exc}") from exc
    else:
        raise AssertionError(f"expected ValueError containing {message_fragment!r}")


def encrypt_synthetic_b7(
    osck: bytes,
    inner_key: bytes,
    inner_stream: bytes,
    declared_size: int | None = None,
    trailing: bytes = b"",
) -> bytes:
    iv1 = bytes(range(16))
    iv2 = bytes(range(16, 32))
    wrapped = AES.new(osck, AES.MODE_CBC, iv1).encrypt(pad(inner_key, 16))
    encrypted = AES.new(inner_key, AES.MODE_CBC, iv2).encrypt(pad(inner_stream, 16))
    ciphertext = encrypted + trailing
    size = len(iv1 + wrapped + iv2 + ciphertext) if declared_size is None else declared_size
    return b"\xB7MUTE\n" + struct.pack(">I", size) + iv1 + wrapped + iv2 + ciphertext


def main() -> int:
    if not REFERENCE.is_file():
        raise SystemExit(f"missing ignored reference RBI: {REFERENCE}")

    raw = REFERENCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == REFERENCE_SHA256, f"reference hash changed: {digest}"
    parsed = parse_header(raw)
    fields, tlvs = independent_header(raw)
    assert fields["magic"] == b"BLI2"
    assert fields["fim"] == b"23" and fields["fia"] == b"KN"
    assert fields["prodid"] == b"0" and fields["varid"] == b"TL"
    assert fields["data_offset"] == 363 and fields["data_size"] == len(raw) - 363
    assert parsed["data_offset"] == "363" and parsed["data_size"] == str(len(raw) - 363)
    assert tlvs[0x08] == b"GCNT-X"
    assert tlvs[0x09] == b"Technicolor EWA1330"
    assert tlvs[0x0A] == b"EWA1330"
    assert tlvs[0x02] == bytes.fromhex("27987416")
    assert tlvs[0x81] == bytes.fromhex("117c0000")
    stream = raw[int(fields["data_offset"]) :]
    assert stream[:6] == b"\xB7MUTE\n"
    advertised_b7_size = struct.unpack_from(">I", stream, 6)[0]
    assert advertised_b7_size == len(stream) - 10
    legacy_blidec_offset = struct.unpack_from(">H", raw, 0x2A)[0]
    assert legacy_blidec_offset == fields["data_offset"]
    iv1, wrapped, iv2 = b7_first_layer_oracle(memoryview(stream))
    assert (len(iv1), len(wrapped), len(iv2)) == (16, 48, 16)
    print(
        "VERIFIED real fixture header: "
        f"sha256={digest}; board={parsed['boardname']}; "
        f"offset={parsed['data_offset']}; size={parsed['data_size']}; "
        f"B7_size={advertised_b7_size}; exact payload boundary"
    )
    print(
        "VERIFIED offset cross-check: blidec_enhanced.py's >H@0x2a reads "
        f"{legacy_blidec_offset}, equal to this fixture's >I@0x28 offset"
    )

    # Malformed synthetic headers must fail consistently without weakening the
    # verified real-fixture path above.
    expect_value_error(
        lambda: parse_header(make_header(48, 0)), "before end of fixed header"
    )
    expect_value_error(
        lambda: parse_header(make_header(FIXED_HEADER_SIZE, 0, magic=b"NOPE")),
        "invalid BLI magic",
    )
    expect_value_error(
        lambda: parse_header(make_header(FIXED_HEADER_SIZE + 1, 0)), "past EOF"
    )
    expect_value_error(
        lambda: parse_header(make_header(FIXED_HEADER_SIZE, 999)), "extends past EOF"
    )
    expect_value_error(
        lambda: parse_header(make_header(FIXED_HEADER_SIZE + 1, 0) + b"\x08"),
        "incomplete TLV tag/length",
    )
    expect_value_error(
        lambda: parse_header(
            make_header(FIXED_HEADER_SIZE + 5, 0) + b"\x08\x08abc"
        ),
        "exceeds header",
    )
    print(
        "VERIFIED malformed-header rejection: wrong magic, offset below "
        "0x134, offset past EOF, size past EOF, incomplete TLV header, and "
        "incomplete TLV value all raise ValueError"
    )

    # Synthetic positive control. PyCryptodome creates the ciphertext; the
    # independent cryptography backend decrypts both AES-CBC layers and checks
    # the explicitly known plaintext before the project helper is exercised.
    osck = bytes(range(32))
    inner_key = bytes(range(32, 64))
    expected_body = b"SYNTHETIC-ONLY\x00known plaintext control"
    inner_stream = b"\xB0MUTE\n" + expected_body
    synthetic = encrypt_synthetic_b7(osck, inner_key, inner_stream)
    s_iv1, s_wrapped, s_iv2 = b7_first_layer_oracle(memoryview(synthetic))
    dec1 = Cipher(algorithms.AES(osck), modes.CBC(s_iv1)).decryptor()
    assert strict_unpad(dec1.update(s_wrapped) + dec1.finalize()) == inner_key
    s_ciphertext = synthetic[90:]
    dec2 = Cipher(algorithms.AES(inner_key), modes.CBC(s_iv2)).decryptor()
    assert strict_unpad(dec2.update(s_ciphertext) + dec2.finalize()) == inner_stream
    decoded, status = process_payload(memoryview(synthetic), osck)
    assert status == "plain_b0" and decoded == expected_body
    print(
        f"VERIFIED synthetic control only: PyCryptodome {Crypto.__version__}; "
        "independent "
        f"cryptography {cryptography.__version__} "
        "AES-CBC unwrap/body checks and project helper agree on known plaintext"
    )

    wrong_key = bytes([0xFF]) * 32
    wrong_decoded, wrong_status = process_payload(memoryview(synthetic), wrong_key)
    assert wrong_decoded is None and wrong_status == "bad_osck"
    truncated = synthetic[: 10 + 16 + 16]
    truncated_decoded, truncated_status = process_payload(memoryview(truncated), osck)
    assert truncated_decoded is None and truncated_status == "bad_osck"
    print(
        "OBSERVED synthetic B7 negatives: wrong dummy key and truncated "
        "wrapped-key ciphertext both report bad_osck; status does not distinguish them"
    )

    # The implementation currently accepts an inconsistent size and silently
    # ignores a trailing non-block byte after a valid second-layer ciphertext.
    malformed = encrypt_synthetic_b7(
        osck, inner_key, inner_stream, declared_size=1, trailing=b"X"
    )
    decoded_bad, status_bad = process_payload(memoryview(malformed), osck)
    assert status_bad == "plain_b0" and decoded_bad == expected_body
    print(
        "OBSERVED B7 framing gap: helper accepts declared_size=1 and ignores "
        "one trailing non-block byte after valid ciphertext"
    )
    print("LIMIT: synthetic controls test code paths, not GCNT-X OSCK or real firmware decryption")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
