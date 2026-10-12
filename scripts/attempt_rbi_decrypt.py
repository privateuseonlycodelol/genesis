#!/usr/bin/env python3
"""Try OSCK and derived key candidates against a sealed BLI2 RBI (offline)."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import struct
import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rbi_header import parse_header  # noqa: E402

OSCK_DIR = ROOT / "tools" / "hack-technicolor" / "osck"
DECRYPT_UTIL_BOARDS = ROOT / "tools" / "Decrypt_RBI_Firmware_Utility" / "src" / "main" / "board.java"
RIP_ID_OSCK = 0x0121

LOGVIEWER_16 = bytes.fromhex("4d17f88a54003ce68362bbf7b1c70d1d")


def _env_serial() -> str:
    return os.environ.get("GENESIS_SERIAL", "").strip()


def _env_mac_hex() -> str:
    return os.environ.get("GENESIS_MAC_HEX", "").strip().replace(":", "").lower()


def process_payload(buf: memoryview, osck: bytes, depth: int = 0) -> tuple[bytes | None, str]:
    if depth > 8:
        return None, "depth"
    i = 0
    while i < len(buf):
        t = buf[i]
        i += 1
        if t == 0xB0:
            i += 4 + 1
            return bytes(buf[i:]), "plain_b0"
        if t == 0xB4:
            i += 4 + 1 + 4
            d = zlib.decompressobj()
            out = d.decompress(bytes(buf[i:]))
            return out + d.flush(), "inflate"
        if t == 0xB8:
            i += 4 + 1 + 4 + 32
            continue
        if t == 0xB7:
            i += 4 + 1 + 4
            iv1 = bytes(buf[i : i + 16])
            i += 16
            enc = bytes(buf[i : i + 48])
            i += 48
            try:
                key2 = unpad(AES.new(osck, AES.MODE_CBC, iv1).decrypt(enc), 16)
            except ValueError:
                return None, "bad_osck"
            if len(key2) != 32:
                return None, f"bad_inner_key_len_{len(key2)}"
            iv2 = bytes(buf[i : i + 16])
            i += 16
            cipher2 = AES.new(key2, AES.MODE_CBC, iv2)
            rest = bytes(buf[i:])
            encbody = rest[: len(rest) // 16 * 16]
            plain = cipher2.decrypt(encbody)
            try:
                plain = unpad(plain, 16)
            except ValueError:
                pass
            return process_payload(memoryview(plain), osck, depth + 1)
        return None, f"bad_magic_{t:02x}"
    return None, "eof"


def b7_first_layer_oracle(stream: memoryview) -> tuple[bytes, bytes, bytes]:
    """Return (iv1, wrapped_48, iv2) from first B7 chunk."""
    if stream[0] != 0xB7:
        raise ValueError("stream does not start with B7")
    i = 1 + 4 + 1 + 4
    iv1 = bytes(stream[i : i + 16])
    i += 16
    enc = bytes(stream[i : i + 48])
    i += 48
    iv2 = bytes(stream[i : i + 16])
    return iv1, enc, iv2


def classify_b7_unwrap(osck: bytes, iv1: bytes, enc: bytes) -> str:
    plain = AES.new(osck, AES.MODE_CBC, iv1).decrypt(enc)
    pad = plain[-1]
    if pad < 1 or pad > 16:
        return f"bad_pad_{pad:02x}"
    if plain[-pad:] != bytes([pad]) * pad:
        return f"bad_pkcs_{pad:02x}"
    try:
        unpad(plain, 16)
    except ValueError:
        return f"unpad_fail_{pad:02x}"
    return "unwrap_ok"


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def _parse_board_java_osck_hex() -> list[tuple[str, bytes]]:
    import re

    out: list[tuple[str, bytes]] = []
    if not DECRYPT_UTIL_BOARDS.is_file():
        return out
    text = DECRYPT_UTIL_BOARDS.read_text(encoding="utf-8", errors="replace")
    board = "unknown"
    for line in text.splitlines():
        m_board = re.search(r'new board\("([^"]+)"\)', line)
        if m_board:
            board = m_board.group(1)
        m_key = re.search(r'addOsKeys\("([0-9A-Fa-f]{64})"', line)
        if m_key:
            out.append((f"board.java:{board}", bytes.fromhex(m_key.group(1))))
    seen: set[bytes] = set()
    unique: list[tuple[str, bytes]] = []
    for name, key in out:
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, key))
    return unique


def derived_key_candidates(
    serial: str | None = None,
    mac_hex: str | None = None,
    header: dict[str, str] | None = None,
) -> list[tuple[str, bytes]]:
    if serial is None:
        serial = _env_serial()
    if mac_hex is None:
        mac_hex = _env_mac_hex()

    keys: list[tuple[str, bytes]] = []
    if serial:
        serials = [
            serial,
            serial.upper(),
            serial.lower(),
            serial.strip(),
            serial.replace("CP", ""),
            serial[2:] if serial.startswith("CP") else serial,
        ]
        seen_s: set[str] = set()
        for s in serials:
            if not s or s in seen_s:
                continue
            seen_s.add(s)
            raw = s.encode("ascii")
            keys.append((f"serial_pad32:{s}", raw.ljust(32, b"\0")[:32]))
            keys.append((f"sha256_serial:{s}", _sha256(raw)))

    if mac_hex and len(mac_hex) == 12:
        mac = bytes.fromhex(mac_hex)
        mac_colon = ":".join(mac_hex[i : i + 2] for i in range(0, 12, 2)).upper()
        for label, material in [
            ("mac6_raw", mac),
            ("mac6_colon_upper", mac_colon.encode()),
            ("mac6_nocolon_upper", mac_hex.upper().encode()),
        ]:
            keys.append((label, material.ljust(32, b"\0")[:32]))
            keys.append((f"sha256_{label}", _sha256(material)))

    keys.append(("logviewer16_pad32", LOGVIEWER_16.ljust(32, b"\0")))
    keys.append(("logviewer16_x2", LOGVIEWER_16 * 2))
    keys.append(("sha256_logviewer16", _sha256(LOGVIEWER_16)))

    static_strings: list[tuple[str, str]] = [
        ("GCNT-X", "GCNT-X"),
        ("EWA1330", "EWA1330"),
        ("EWA1331", "EWA1331"),
        ("BLI223KN", "BLI223KN"),
        ("TCH", "TCH"),
        ("TL", "TL"),
        ("Technicolor", "Technicolor"),
    ]
    if serial:
        static_strings.append(("serial+board", f"{serial}:GCNT-X"))
    if mac_hex:
        static_strings.append(("mac+board", f"{mac_hex}:GCNT-X"))
    for label, text in static_strings:
        keys.append((f"sha256_{label}", _sha256(text.encode())))

    rip_salt = struct.pack(">H", RIP_ID_OSCK)
    rip_msgs: list[tuple[str, bytes]] = [
        ("rip0121_board", b"GCNT-X"),
        ("rip0121_varid_TL", b"TL"),
    ]
    if serial:
        rip_msgs.append(("rip0121_serial", serial.encode()))
    if mac_hex:
        rip_msgs.append(("rip0121_mac", mac_hex.encode()))
    for label, msg in rip_msgs:
        keys.append((f"hmac_sha256_{label}", _hmac_sha256(rip_salt, msg)))
        if serial:
            keys.append(
                (f"hmac_sha256_serial_{label}", _hmac_sha256(serial.encode(), rip_salt + msg))
            )

    if header and (serial or mac_hex):
        keys.extend(_header_derived_candidates(header, serial, mac_hex))

    keys.extend(_parse_board_java_osck_hex())
    return keys


def _header_derived_candidates(
    header: dict[str, str], serial: str, mac_hex: str
) -> list[tuple[str, bytes]]:
    keys: list[tuple[str, bytes]] = []
    prodid = header.get("prodid", "")
    varid = header.get("varid", "")
    board = header.get("boardname", "GCNT-X")
    varname = header.get("varname", "")
    fim_fia = (header.get("fim", "") + header.get("fia", "")).encode()

    for label, blob in [
        ("header_prodid_pad32", prodid.encode().ljust(32, b"\0")[:32]),
        ("header_varid_pad32", varid.encode().ljust(32, b"\0")[:32]),
        ("header_fim_fia_pad32", fim_fia.ljust(32, b"\0")[:32]),
        ("sha256_prodid_varid", _sha256(f"{prodid}:{varid}".encode())),
        ("sha256_board_varname", _sha256(f"{board}:{varname}".encode())),
        ("sha256_fim_fia", _sha256(fim_fia)),
    ]:
        keys.append((label, blob if len(blob) == 32 else blob))

    ts_hex = header.get("timestamp", "")
    if ts_hex.startswith("0x"):
        ts = int(ts_hex, 16)
        keys.append(("sha256_timestamp", _sha256(struct.pack(">I", ts))))
        keys.append(("timestamp_pad32_be", struct.pack(">I", ts).ljust(32, b"\0")))

    flash = header.get("flashaddress", "")
    if flash.startswith("0x"):
        fa = int(flash, 16)
        keys.append(("sha256_flashaddr", _sha256(struct.pack(">I", fa))))

    combo = f"{serial}|{mac_hex}|{board}|{varid}|{prodid}".encode()
    keys.append(("sha256_device_header_combo", _sha256(combo)))
    keys.append(("hmac_TL_combo", _hmac_sha256(b"TL", combo)))

    # Manufacturer / operator ids seen in BLI static header (varid TL).
    for mfg in (b"TL", b"TCH", b"Telia", b"Technicolor"):
        keys.append((f"hmac_mfg_{mfg.decode()}_serial", _hmac_sha256(mfg, serial.encode())))
        keys.append((f"hmac_mfg_{mfg.decode()}_board", _hmac_sha256(mfg, board.encode())))

    return keys


def community_osck_files() -> list[tuple[str, bytes]]:
    keys: list[tuple[str, bytes]] = []
    if OSCK_DIR.is_dir():
        for f in sorted(OSCK_DIR.glob("*.osck")):
            keys.append((f"osck/{f.name}", f.read_bytes()))
    return keys


def structural_scan(data: bytes, info: dict[str, str]) -> list[str]:
    lines: list[str] = []
    data_off = int(info["data_offset"])
    data_size = int(info["data_size"])
    file_len = len(data)
    lines.append(f"file_len: {file_len}")
    lines.append(f"data_off + data_size: {data_off + data_size}")
    trailing = file_len - (data_off + data_size)
    lines.append(f"trailing_after_payload: {trailing}")

    extra_bli = []
    for off in range(1, min(file_len, 1024 * 1024)):
        if data[off : off + 4] == b"BLI2":
            extra_bli.append(off)
    lines.append(f"BLI2_magic_offsets_first_1MiB: {extra_bli[:20]}")

    hdr = data[:data_off]
    for sig, name in [(b"PK\x03\x04", "zip_local"), (b"\x1f\x8b", "gzip"), (b"BLI2", "bli2_in_hdr")]:
        idx = hdr.find(sig)
        lines.append(f"{name}_in_header_region: offset {idx if idx >= 0 else 'none'}")

    payload = data[data_off : data_off + min(256, data_size)]
    lines.append(f"payload_prefix_hex: {payload[:64].hex()}")

    # Cleartext ASCII runs in signed header gap (0x30..0x104 per Java parser skip).
    gap = data[48 : 48 + 0x104]
    if b"BEGIN" in gap or b"ssh" in gap.lower():
        lines.append("warning: cleartext-like material in header gap")
    else:
        lines.append("header_gap_0x104: no obvious cleartext PEM/ssh")

    return lines


def compare_rbi_headers(path_a: Path, path_b: Path) -> list[str]:
    a = parse_header(path_a.read_bytes())
    b = parse_header(path_b.read_bytes())
    lines = [f"ref: {path_a.name}", f"sibling: {path_b.name}"]
    all_keys = sorted(set(a) | set(b))
    for k in all_keys:
        va, vb = a.get(k, "—"), b.get(k, "—")
        mark = "==" if va == vb else "!="
        lines.append(f"  {k}: {mark}  {va} | {vb}")
    da = path_a.read_bytes()
    db = path_b.read_bytes()
    off_a, off_b = int(a["data_offset"]), int(b["data_offset"])
    pa = da[off_a : off_a + 80]
    pb = db[off_b : off_b + 80]
    lines.append(f"  seal_prefix_80B: {'==' if pa == pb else '!='}")
    if pa != pb:
        lines.append(f"    ref:    {pa.hex()}")
        lines.append(f"    sib:    {pb.hex()}")
    return lines


def run_trials(
    rbi: Path,
    log_path: Path,
    include_attempt2: bool = True,
) -> tuple[bool, list[str]]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    data = rbi.read_bytes()
    info = parse_header(data)
    data_off = int(info["data_offset"])
    stream = memoryview(data)[data_off:]

    keys: list[tuple[str, bytes]] = []
    keys.extend(community_osck_files())
    keys.extend(derived_key_candidates(header=info if include_attempt2 else None))

    by_bytes: dict[bytes, str] = {}
    for name, key in keys:
        if len(key) != 32:
            continue
        by_bytes.setdefault(key, name)

    iv1, enc, iv2 = b7_first_layer_oracle(stream)
    oracle_hist: dict[str, int] = {}
    oracle_samples: dict[str, str] = {}
    for key, name in by_bytes.items():
        tag = classify_b7_unwrap(key, iv1, enc)
        oracle_hist[tag] = oracle_hist.get(tag, 0) + 1
        if tag not in oracle_samples:
            plain = AES.new(key, AES.MODE_CBC, iv1).decrypt(enc)
            oracle_samples[tag] = plain[:8].hex()

    ok: list[str] = []
    statuses: dict[str, int] = {}
    for key, name in sorted(by_bytes.items(), key=lambda x: x[1]):
        _, status = process_payload(stream, key)
        statuses[status] = statuses.get(status, 0) + 1
        if status in ("plain_b0", "inflate"):
            ok.append(name)

    struct_lines = structural_scan(data, info) if include_attempt2 else []

    lines = [
        f"RBI: {rbi}",
        f"header: board={info.get('boardname')} varid={info.get('varid')} "
        f"timestamp={info.get('timestamp')} flash={info.get('flashaddress')}",
        f"payload_offset: {data_off} first_byte: 0x{stream[0]:02x}",
        f"keys_tried: {len(by_bytes)}",
        f"  community_osck_files: {len(community_osck_files())}",
        f"  derived_candidates: {len(derived_key_candidates(header=info if include_attempt2 else None))}",
        f"status_histogram: {statuses}",
        f"b7_unwrap_oracle: {oracle_hist}",
        f"b7_oracle_plain_prefix_by_class: {oracle_samples}",
        f"decrypt_success: {bool(ok)}",
    ]
    if struct_lines:
        lines.append("structural_scan:")
        lines.extend(f"  {s}" for s in struct_lines)
    if ok:
        lines.append("working_keys: " + ", ".join(ok))
    else:
        lines.append(
            "note: no trial passed B7 OSCK unwrap (bad_osck); GCNT-X.osck not published"
        )

    out = "\n".join(lines) + "\n"
    print(out, end="")
    log_path.write_text(out, encoding="utf-8")
    return bool(ok), lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline GCNT-X RBI OSCK trials")
    parser.add_argument("rbi", nargs="?", help="Path to .rbi (default: reference)")
    parser.add_argument(
        "--log",
        help="Log output path (default: decrypt-attempt-19x.txt or -attempt2.txt)",
    )
    parser.add_argument(
        "--compare-sibling",
        metavar="RBI",
        help="Diff BLI2 header vs this RBI (e.g. sibling 19.5 unified)",
    )
    parser.add_argument(
        "--attempt1-only",
        action="store_true",
        help="Skip attempt-2 header/HMAC derivations",
    )
    args = parser.parse_args()

    rbi = Path(
        args.rbi
        if args.rbi
        else ROOT / "artifacts/firmware/REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi"
    )
    include_attempt2 = not args.attempt1_only
    log_path = Path(
        args.log
        if args.log
        else (
            ROOT / "artifacts/logs/decrypt-attempt2.txt"
            if include_attempt2
            else ROOT / "artifacts/logs/decrypt-attempt-19x.txt"
        )
    )

    if args.compare_sibling:
        sib = Path(args.compare_sibling)
        if sib.is_file():
            for line in compare_rbi_headers(rbi, sib):
                print(line)
        else:
            print(f"sibling missing: {sib}", file=sys.stderr)

    ok, _ = run_trials(rbi, log_path, include_attempt2=include_attempt2)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
