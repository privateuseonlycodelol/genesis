#!/usr/bin/env python3
"""Read-only pcapng preflight for a designated IPv4/TCP mirror control.

A positive result requires a caller-supplied flow and WAN MAC, the outbound SYN
from that MAC, the matching reverse SYN/ACK to that MAC, the final ACK from it,
an outbound data segment, and a matching reverse data segment. This is a bounded
simple-flow check, not TCP stream reassembly. Aggregate traffic is never enough.
This utility does not configure or inspect a physical switch/mirror session.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class CaptureError(Exception):
    """The input cannot be parsed as a structurally valid pcapng file."""


@dataclass(frozen=True)
class Interface:
    section: int
    index: int
    linktype: int
    snaplen: int


@dataclass(frozen=True)
class Packet:
    section: int
    interface: int
    number: int
    captured_len: int
    original_len: int
    data: bytes


@dataclass(frozen=True)
class TcpSegment:
    section: int
    interface: int
    number: int
    src_mac: bytes
    dst_mac: bytes
    src_ip: bytes
    dst_ip: bytes
    src_port: int
    dst_port: int
    seq: int
    ack: int
    flags: int
    payload_len: int


@dataclass(frozen=True)
class Flow:
    client_ip: bytes
    client_port: int
    server_ip: bytes
    server_port: int


def parse_pcapng(path: Path) -> tuple[list[Interface], list[Packet]]:
    raw = path.read_bytes()
    interfaces: list[Interface] = []
    packets: list[Packet] = []
    offset = 0
    section = -1
    endian: str | None = None
    section_interfaces: list[Interface] = []

    while offset < len(raw):
        if offset + 12 > len(raw):
            raise CaptureError("trailing or truncated pcapng block")
        if raw[offset : offset + 4] == b"\x0a\x0d\x0d\x0a":
            byte_order_magic = raw[offset + 8 : offset + 12]
            if byte_order_magic == b"\x4d\x3c\x2b\x1a":
                endian = "<"
            elif byte_order_magic == b"\x1a\x2b\x3c\x4d":
                endian = ">"
            else:
                raise CaptureError("invalid pcapng byte-order magic")
            block_len = struct.unpack_from(endian + "I", raw, offset + 4)[0]
            section += 1
            section_interfaces = []
            if block_len < 28 or block_len % 4 or offset + block_len > len(raw):
                raise CaptureError("invalid pcapng section-header length")
            trailer = struct.unpack_from(endian + "I", raw, offset + block_len - 4)[0]
            if trailer != block_len:
                raise CaptureError("section-header length trailer mismatch")
            major, minor = struct.unpack_from(endian + "HH", raw, offset + 12)
            if major != 1:
                raise CaptureError("unsupported pcapng major version")
            offset += block_len
            continue

        if endian is None:
            raise CaptureError("missing pcapng section header")
        block_type, block_len = struct.unpack_from(endian + "II", raw, offset)
        if block_len < 12 or block_len % 4 or offset + block_len > len(raw):
            raise CaptureError("invalid pcapng block length")
        trailer = struct.unpack_from(endian + "I", raw, offset + block_len - 4)[0]
        if trailer != block_len:
            raise CaptureError("pcapng block length trailer mismatch")

        if block_type == 1:  # Interface Description Block
            if block_len < 20:
                raise CaptureError("short Interface Description Block")
            body = offset + 8
            linktype = struct.unpack_from(endian + "H", raw, body)[0]
            snaplen = struct.unpack_from(endian + "I", raw, body + 4)[0]
            entry = Interface(section, len(section_interfaces), linktype, snaplen)
            section_interfaces.append(entry)
            interfaces.append(entry)
        elif block_type == 6:  # Enhanced Packet Block
            if block_len < 32:
                raise CaptureError("short Enhanced Packet Block")
            body = offset + 8
            iface, _ts_hi, _ts_lo, caplen, origlen = struct.unpack_from(
                endian + "IIIII", raw, body
            )
            if iface >= len(section_interfaces):
                raise CaptureError("packet references a missing interface")
            packet_start = body + 20
            packet_end = packet_start + caplen
            if packet_end > offset + block_len - 4:
                raise CaptureError("packet bytes exceed Enhanced Packet Block")
            if caplen > origlen:
                raise CaptureError("captured length exceeds original packet length")
            packets.append(
                Packet(
                    section,
                    iface,
                    len(packets) + 1,
                    caplen,
                    origlen,
                    raw[packet_start:packet_end],
                )
            )
        # Statistics, name-resolution, and other valid block types do not carry
        # packets relevant to this preflight and are safely skipped.
        offset += block_len

    if not interfaces:
        raise CaptureError("pcapng contains no interface descriptions")
    return interfaces, packets


def checksum_valid(header: bytes) -> bool:
    if len(header) % 2:
        header += b"\x00"
    total = sum(struct.unpack(">" + str(len(header) // 2) + "H", header))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return total == 0xFFFF


def raw_ip_signature(packet: bytes) -> str | None:
    """Recognize complete raw IP accidentally stored under an Ethernet IDB."""
    if len(packet) >= 20 and packet[0] >> 4 == 4:
        ihl = (packet[0] & 0x0F) * 4
        if (
            20 <= ihl <= len(packet)
            and struct.unpack_from(">H", packet, 2)[0] == len(packet)
            and checksum_valid(packet[:ihl])
        ):
            return "IPv4"
    if len(packet) >= 40 and packet[0] >> 4 == 6:
        if 40 + struct.unpack_from(">H", packet, 4)[0] == len(packet):
            return "IPv6"
    return None


def ethernet_ethertype(packet: bytes) -> int | None:
    if len(packet) < 14:
        return None
    etype = struct.unpack_from(">H", packet, 12)[0]
    cursor = 14
    while etype in (0x8100, 0x88A8, 0x9100):
        if len(packet) < cursor + 4:
            return None
        etype = struct.unpack_from(">H", packet, cursor + 2)[0]
        cursor += 4
    return etype


def parse_tcp(packet: Packet) -> TcpSegment | None:
    data = packet.data
    if len(data) < 14:
        return None
    dst_mac, src_mac = data[:6], data[6:12]
    cursor = 14
    etype = struct.unpack_from(">H", data, 12)[0]
    while etype in (0x8100, 0x88A8, 0x9100):
        if len(data) < cursor + 4:
            return None
        etype = struct.unpack_from(">H", data, cursor + 2)[0]
        cursor += 4
    if etype != 0x0800 or len(data) < cursor + 20:
        return None
    ip = data[cursor:]
    if ip[0] >> 4 != 4:
        return None
    ihl = (ip[0] & 0x0F) * 4
    total_len = struct.unpack_from(">H", ip, 2)[0]
    if ihl < 20 or total_len < ihl + 20 or total_len > len(ip):
        return None
    flags_fragment = struct.unpack_from(">H", ip, 6)[0]
    if flags_fragment & 0x3FFF:  # MF or nonzero fragment offset
        return None
    if ip[9] != 6:
        return None
    tcp = ip[ihl:total_len]
    tcp_hlen = (tcp[12] >> 4) * 4
    if tcp_hlen < 20 or tcp_hlen > len(tcp):
        return None
    src_port, dst_port, seq, ack = struct.unpack_from(">HHII", tcp, 0)
    flags = tcp[13]
    return TcpSegment(
        packet.section,
        packet.interface,
        packet.number,
        src_mac,
        dst_mac,
        ip[12:16],
        ip[16:20],
        src_port,
        dst_port,
        seq,
        ack,
        flags,
        len(tcp) - tcp_hlen,
    )


def parse_mac(value: str) -> bytes:
    compact = value.replace(":", "").replace("-", "")
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", compact):
        raise ValueError("WAN MAC must contain exactly six hexadecimal bytes")
    return bytes.fromhex(compact)


def parse_flow(args: argparse.Namespace) -> Flow | None:
    values = (args.client_ip, args.client_port, args.server_ip, args.server_port)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("supply all client/server IP and port fields")
    client_ip = ipaddress.ip_address(args.client_ip)
    server_ip = ipaddress.ip_address(args.server_ip)
    if client_ip.version != 4 or server_ip.version != 4:
        raise ValueError("this preflight currently supports IPv4/TCP flows")
    for port in (args.client_port, args.server_port):
        if not 1 <= port <= 65535:
            raise ValueError("TCP ports must be in 1..65535")
    return Flow(client_ip.packed, args.client_port, server_ip.packed, args.server_port)


def flow_direction(segment: TcpSegment, flow: Flow) -> str | None:
    if (
        segment.src_ip == flow.client_ip
        and segment.dst_ip == flow.server_ip
        and segment.src_port == flow.client_port
        and segment.dst_port == flow.server_port
    ):
        return "out"
    if (
        segment.src_ip == flow.server_ip
        and segment.dst_ip == flow.client_ip
        and segment.src_port == flow.server_port
        and segment.dst_port == flow.client_port
    ):
        return "in"
    return None


def summarize_capture(path: Path, wan_mac: bytes | None, flow: Flow | None) -> dict[str, object]:
    interfaces, packets = parse_pcapng(path)
    linktypes = {(item.section, item.index): item.linktype for item in interfaces}
    ethernet_interfaces = [item for item in interfaces if item.linktype == 1]
    raw_v4 = raw_v6 = ethernet_frames = truncated = 0
    for packet in packets:
        linktype = linktypes[(packet.section, packet.interface)]
        if packet.captured_len < packet.original_len:
            truncated += 1
        if linktype == 1:
            signature = raw_ip_signature(packet.data)
            if signature == "IPv4":
                raw_v4 += 1
            elif signature == "IPv6":
                raw_v6 += 1
            if ethernet_ethertype(packet.data) in (0x0800, 0x0806, 0x86DD, 0x8100, 0x88A8, 0x9100, 0x8899):
                ethernet_frames += 1
    raw_ip = raw_v4 + raw_v6
    mixed = raw_ip >= 2 and (raw_ip / max(1, len(packets)) >= 0.01 or ethernet_frames >= 2)

    summary: dict[str, object] = {
        "interfaces": interfaces,
        "packet_count": len(packets),
        "truncated_packets": truncated,
        "raw_v4": raw_v4,
        "raw_v6": raw_v6,
        "ethernet_frames": ethernet_frames,
        "mixed_encapsulation": mixed,
        "status": "UNVALIDATED",
        "reason": "a designated known TCP flow and target WAN MAC are required",
        "flow_frames": 0,
        "stages": {
            "syn": False,
            "syn_ack": False,
            "final_ack": False,
            "client_data": False,
            "return_payload": False,
        },
    }

    if len(ethernet_interfaces) != 1:
        summary["reason"] = "capture does not identify exactly one Ethernet interface"
        return summary
    selected = ethernet_interfaces[0]
    if mixed:
        summary["reason"] = "raw-IP records conflict with Ethernet link-type metadata"
        return summary
    if wan_mac is None or flow is None:
        return summary

    segments: list[tuple[TcpSegment, str]] = []
    for packet in packets:
        if packet.section != selected.section or packet.interface != selected.index:
            continue
        segment = parse_tcp(packet)
        if segment is None:
            continue
        direction = flow_direction(segment, flow)
        if direction:
            segments.append((segment, direction))
    summary["flow_frames"] = len(segments)

    # This matcher handles a simple visible handshake and in-order client data;
    # it does not perform general TCP stream reassembly.
    syns = [
        seg for seg, direction in segments
        if direction == "out" and seg.src_mac == wan_mac
        and (seg.flags & 0x12) == 0x02 and not (seg.flags & 0x05)
        and seg.payload_len == 0
    ]
    saw_synack = saw_final_ack = saw_client_data = False
    for syn in syns:
        synacks = [
            seg for seg, direction in segments
            if direction == "in" and seg.dst_mac == wan_mac
            and (seg.flags & 0x12) == 0x12
            and not (seg.flags & 0x05) and seg.payload_len == 0
            and seg.ack == ((syn.seq + 1) & 0xFFFFFFFF)
            and seg.number > syn.number
            and (seg.section, seg.interface) == (syn.section, syn.interface)
        ]
        for synack in synacks:
            saw_synack = True
            final_acks = [
                seg for seg, direction in segments
                if direction == "out" and seg.src_mac == wan_mac
                and (seg.flags & 0x10) and not (seg.flags & 0x07)
                and seg.payload_len == 0
                and seg.seq == ((syn.seq + 1) & 0xFFFFFFFF)
                and seg.ack == ((synack.seq + 1) & 0xFFFFFFFF)
                and seg.number > synack.number
                and (seg.section, seg.interface) == (syn.section, syn.interface)
            ]
            for final_ack in final_acks:
                saw_final_ack = True
                client_data = sorted(
                    (
                        seg for seg, direction in segments
                        if direction == "out" and seg.src_mac == wan_mac
                        and (seg.flags & 0x10) and not (seg.flags & 0x07)
                        and seg.payload_len > 0 and seg.number > final_ack.number
                        and (seg.section, seg.interface) == (syn.section, syn.interface)
                    ),
                    key=lambda seg: seg.number,
                )
                # Extend only a contiguous, in-order client data run. TCP
                # sequence arithmetic wraps at 2^32.
                next_client_seq = (syn.seq + 1) & 0xFFFFFFFF
                client_data_ends: dict[int, int] = {}
                for data in client_data:
                    if data.seq == next_client_seq:
                        next_client_seq = (data.seq + data.payload_len) & 0xFFFFFFFF
                        client_data_ends[next_client_seq] = data.number
                saw_client_data |= bool(client_data_ends)

                return_payloads = [
                    seg for seg, direction in segments
                    if direction == "in" and seg.dst_mac == wan_mac
                    and (seg.flags & 0x10) and not (seg.flags & 0x07)
                    and seg.seq == ((synack.seq + 1) & 0xFFFFFFFF)
                    and seg.ack in client_data_ends and seg.payload_len > 0
                    and seg.number > final_ack.number
                    and client_data_ends[seg.ack] < seg.number
                    and (seg.section, seg.interface) == (syn.section, syn.interface)
                ]
                if return_payloads:
                    summary["status"] = "VALIDATED"
                    summary["reason"] = "designated TCP request and matching reverse payload matched target WAN MAC"
                    summary["stages"] = {
                        "syn": True,
                        "syn_ack": True,
                        "final_ack": True,
                        "client_data": True,
                        "return_payload": True,
                    }
                    return summary

    summary["stages"] = {
        "syn": bool(syns),
        "syn_ack": saw_synack,
        "final_ack": saw_final_ack,
        "client_data": saw_client_data,
        "return_payload": False,
    }
    if syns:
        summary["reason"] = "capture lacks a fully correlated handshake, outbound data, and matching reverse payload"
    else:
        summary["reason"] = "designated flow has no outbound SYN from the supplied WAN MAC"
    return summary


def print_result(result: dict[str, object], label: str | None = None) -> None:
    prefix = f"{label}: " if label else ""
    print(f"{prefix}STATUS: {result['status']}")
    interfaces = result["interfaces"]
    rendered = ", ".join(
        f"section {i.section}/interface {i.index} linktype {i.linktype} snaplen {i.snaplen}"
        for i in interfaces  # type: ignore[union-attr]
    )
    print(f"  Interfaces: {rendered}")
    print(f"  Packets: {result['packet_count']}; truncated records: {result['truncated_packets']}")
    print(f"  Raw-IP signatures under Ethernet metadata: IPv4={result['raw_v4']}, IPv6={result['raw_v6']}")
    print(f"  Designated-flow packets: {result['flow_frames']}")
    stages = result["stages"]
    print(
        "  Correlation: "
        + ", ".join(f"{name}={'yes' if ok else 'no'}" for name, ok in stages.items())  # type: ignore[union-attr]
    )
    print(f"  Reason: {result['reason']}")


# The fixtures below use documentation-only IPv4 addresses and locally
# administered MACs. They are generated in a temporary directory and never
# sent on a network.
SYNTH_MAC = bytes.fromhex("020000000001")
PEER_MAC = bytes.fromhex("0200000000fe")
SYNTH_FLOW = Flow(
    ipaddress.IPv4Address("198.51.100.10").packed,
    40000,
    ipaddress.IPv4Address("203.0.113.80").packed,
    80,
)


def internet_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(">" + str(len(data) // 2) + "H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def make_tcp_frame(
    src_mac: bytes,
    dst_mac: bytes,
    src_ip: bytes,
    dst_ip: bytes,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: int,
    payload: bytes = b"",
) -> bytes:
    tcp0 = struct.pack(">HHIIHHHH", src_port, dst_port, seq, ack, 5 << 12 | flags, 65535, 0, 0)
    pseudo = src_ip + dst_ip + b"\x00\x06" + struct.pack(">H", len(tcp0) + len(payload))
    tcp_sum = internet_checksum(pseudo + tcp0 + payload)
    tcp = struct.pack(">HHIIHHHH", src_port, dst_port, seq, ack, 5 << 12 | flags, 65535, tcp_sum, 0) + payload
    total_len = 20 + len(tcp)
    ip0 = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total_len, 1, 0, 64, 6, 0, src_ip, dst_ip)
    ip_sum = internet_checksum(ip0)
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total_len, 1, 0, 64, 6, ip_sum, src_ip, dst_ip)
    frame = dst_mac + src_mac + b"\x08\x00" + ip + tcp
    return frame + bytes(max(0, 60 - len(frame)))


def synthetic_flow(
    one_way: bool = False,
    unrelated_mac: bool = False,
    bad_response_ack: bool = False,
    bad_response_seq: bool = False,
    rst_final_ack: bool = False,
) -> list[bytes]:
    router_mac = bytes.fromhex("020000000002") if unrelated_mac else SYNTH_MAC
    c, s = SYNTH_FLOW.client_ip, SYNTH_FLOW.server_ip
    cp, sp = SYNTH_FLOW.client_port, SYNTH_FLOW.server_port
    client_isn, server_isn = 0xFFFFFFFE, 0xFFFFFFFF
    client_next, server_next = (client_isn + 1) & 0xFFFFFFFF, (server_isn + 1) & 0xFFFFFFFF
    request = b"GET /capture-control HTTP/1.1\r\nHost: control.example\r\nConnection: close\r\n\r\n"
    response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"
    request_end = (client_next + len(request)) & 0xFFFFFFFF
    syn = make_tcp_frame(router_mac, PEER_MAC, c, s, cp, sp, client_isn, 0, 0x02)
    if one_way:
        return [syn]
    response_seq = (server_next + 1) & 0xFFFFFFFF if bad_response_seq else server_next
    response_ack = (request_end + 1) & 0xFFFFFFFF if bad_response_ack else request_end
    return [
        syn,
        make_tcp_frame(PEER_MAC, router_mac, s, c, sp, cp, server_isn, client_next, 0x12),
        make_tcp_frame(router_mac, PEER_MAC, c, s, cp, sp, client_next, server_next, 0x14 if rst_final_ack else 0x10),
        make_tcp_frame(router_mac, PEER_MAC, c, s, cp, sp, client_next, server_next, 0x18, request),
        make_tcp_frame(PEER_MAC, router_mac, s, c, sp, cp, response_seq, response_ack, 0x18, response),
    ]


def synthetic_unrelated_tuple_flow() -> list[bytes]:
    """A valid control flow that is not the tuple supplied to the matcher."""
    c = ipaddress.IPv4Address("198.51.100.11").packed
    s = ipaddress.IPv4Address("203.0.113.81").packed
    cp, sp = 40001, 443
    return [
        make_tcp_frame(SYNTH_MAC, PEER_MAC, c, s, cp, sp, 200, 0, 0x02),
        make_tcp_frame(PEER_MAC, SYNTH_MAC, s, c, sp, cp, 600, 201, 0x12),
        make_tcp_frame(SYNTH_MAC, PEER_MAC, c, s, cp, sp, 201, 601, 0x10),
        make_tcp_frame(PEER_MAC, SYNTH_MAC, s, c, sp, cp, 601, 201, 0x18, b"unrelated-response"),
    ]


def pcapng_bytes(frames: Iterable[bytes], linktype: int = 1) -> bytes:
    packets = list(frames)
    shb = (
        b"\x0a\x0d\x0d\x0a"
        + struct.pack("<IIHHq", 28, 0x1A2B3C4D, 1, 0, -1)
        + struct.pack("<I", 28)
    )
    idb = struct.pack("<IIHHII", 1, 20, linktype, 0, 0, 20)
    blocks = [shb, idb]
    for i, frame in enumerate(packets):
        padded_len = (len(frame) + 3) & ~3
        total = 32 + padded_len
        epb = (
            struct.pack("<II", 6, total)
            + struct.pack("<IIIII", 0, 0, i + 1, len(frame), len(frame))
            + frame
            + bytes(padded_len - len(frame))
            + struct.pack("<I", total)
        )
        blocks.append(epb)
    return b"".join(blocks)


def result_for_fixture(directory: Path, name: str, frames: list[bytes], mac: bytes = SYNTH_MAC) -> dict[str, object]:
    path = directory / f"{name}.pcapng"
    path.write_bytes(pcapng_bytes(frames))
    return summarize_capture(path, mac, SYNTH_FLOW)


def self_test(repo_root: Path) -> bool:
    checks: list[tuple[str, str, dict[str, object]]] = []
    with tempfile.TemporaryDirectory(prefix="capture-preflight-") as temp:
        directory = Path(temp)
        positive = result_for_fixture(directory, "positive", synthetic_flow())
        checks.append(("SYNTHETIC HTTP request/response with sequence wrap", "VALIDATED", positive))
        one_way = result_for_fixture(directory, "one-way", synthetic_flow(one_way=True))
        checks.append(("SYNTHETIC one-way SYN", "UNVALIDATED", one_way))
        unrelated = result_for_fixture(directory, "unrelated", synthetic_flow(unrelated_mac=True))
        checks.append(("SYNTHETIC complete flow with unrelated L2 MAC", "UNVALIDATED", unrelated))
        unrelated_tuple = result_for_fixture(directory, "unrelated-tuple", synthetic_unrelated_tuple_flow())
        checks.append(("SYNTHETIC complete unrelated TCP tuple", "UNVALIDATED", unrelated_tuple))
        bad_ack = result_for_fixture(directory, "bad-response-ack", synthetic_flow(bad_response_ack=True))
        checks.append(("SYNTHETIC response with unrelated ACK", "UNVALIDATED", bad_ack))
        bad_seq = result_for_fixture(directory, "bad-response-seq", synthetic_flow(bad_response_seq=True))
        checks.append(("SYNTHETIC response with unrelated sequence", "UNVALIDATED", bad_seq))
        rst = result_for_fixture(directory, "rst-final-ack", synthetic_flow(rst_final_ack=True))
        checks.append(("SYNTHETIC RST|ACK substituted for final handshake ACK", "UNVALIDATED", rst))

        # Independent packet-decoder cross-check for the positive fixture.
        tshark = shutil.which("tshark")
        tshark_ok: bool | None = None
        if tshark:
            p = directory / "positive.pcapng"
            proc = subprocess.run(
                [tshark, "-r", str(p), "-T", "fields", "-e", "frame.number", "-e", "tcp.flags.syn", "-e", "tcp.flags.ack", "-e", "tcp.len", "-e", "http.request.method", "-e", "http.response.code"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            rows = [line.split("\t") for line in proc.stdout.splitlines() if line.strip()]
            is_true = lambda value: value.lower() in ("1", "true")
            tshark_ok = (
                proc.returncode == 0
                and len(rows) == 5
                and sum(is_true(row[1]) and not is_true(row[2]) for row in rows) == 1
                and sum(is_true(row[1]) and is_true(row[2]) for row in rows) == 1
                and sum(row[3].isdigit() and int(row[3]) > 0 for row in rows) == 2
                and sum(row[4] == "GET" for row in rows) == 1
                and sum(row[5] == "200" for row in rows) == 1
            )

        # Existing ignored captures are optional in a standalone checkout.
        want = repo_root / "artifacts/captures/want.pcapng"
        if want.is_file():
            result = summarize_capture(want, SYNTH_MAC, SYNTH_FLOW)
            checks.append(("EXISTING want.pcapng against synthetic designated flow", "UNVALIDATED", result))
        mixed = repo_root / "artifacts/captures/wan2-real.pcapng"
        if mixed.is_file():
            result = summarize_capture(mixed, SYNTH_MAC, SYNTH_FLOW)
            checks.append(("EXISTING wan2-real.pcapng mixed framing", "UNVALIDATED", result))

        ok = True
        for label, expected, actual in checks:
            passed = actual["status"] == expected
            if "wan2-real" in label:
                passed = passed and actual["mixed_encapsulation"] is True and int(actual["raw_v4"]) + int(actual["raw_v6"]) >= 2
            print_result(actual, label)
            print(f"  Expected status: {expected}; assertion: {'PASS' if passed else 'FAIL'}")
            ok &= passed
        if tshark is None:
            print("INDEPENDENT DECODER: tshark unavailable; positive-fixture cross-check skipped")
        else:
            print(f"INDEPENDENT DECODER: tshark positive-fixture check {'PASS' if tshark_ok else 'FAIL'}")
            ok &= bool(tshark_ok)
        print("SYNTHETIC positive result is a parser control only; it is not evidence about a physical mirror.")
        print(f"SELF-TEST: {'PASS' if ok else 'FAIL'}")
        return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", nargs="?", type=Path, help="pcapng capture to inspect (read-only)")
    parser.add_argument("--wan-mac", help="expected router WAN-side Ethernet MAC (hex, colons optional)")
    parser.add_argument("--client-ip", help="client-side IPv4 address as observed in the capture")
    parser.add_argument("--client-port", type=int, help="client-side TCP port")
    parser.add_argument("--server-ip", help="server IPv4 address of the known test flow")
    parser.add_argument("--server-port", type=int, help="server-side TCP port")
    parser.add_argument("--self-test", action="store_true", help="run temporary synthetic controls and available capture negatives")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent

    if args.self_test:
        return 0 if self_test(root) else 2
    if args.capture is None:
        parser.error("capture is required unless --self-test is used")
    try:
        wan_mac = parse_mac(args.wan_mac) if args.wan_mac else None
        flow = parse_flow(args)
        result = summarize_capture(args.capture, wan_mac, flow)
    except (CaptureError, OSError, ValueError) as exc:
        print("STATUS: INVALID")
        print(f"  Reason: {exc}")
        return 2
    print_result(result)
    if result["status"] == "VALIDATED":
        print("  Scope: validates only the supplied flow and MAC in this file; establish their identity and the physical mirror setup separately.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
