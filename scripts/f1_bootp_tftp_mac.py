#!/usr/bin/env python3
"""All-in-one macOS BOOTP + TFTP recovery responder and UART watcher for Telia F1 / GCNT-X.

Replaces the multi-window Windows PowerShell scripts with a single Python process
running natively on macOS. Eliminates Tailscale/virtual interface route hijacking,
Parsec remote desktop disconnects, and Windows firewall UDP drops.

What it does:
  1. (Optional) Configures the specified macOS Ethernet interface to a static IP (default
     192.168.1.100/24). The prior service config is restored on exit unless --keep-ip is set.
  2. (Optional) Watches UART (/dev/cu.usbserial-0001) and presses 'b' at the BOOT-P prompt.
  3. Listens on UDP/67 for the router's BOOTREQUEST (file='GCNT-X') and sends RFC 951 BOOTREPLY.
  4. Listens on UDP/69 for the router's TFTP RRQ and serves block 1 of a test payload.
  5. Records all network exchanges and UART output to a single timestamped log.

Usage (requires sudo to bind privileged UDP ports 67 and 69):
  sudo python3 scripts/f1_bootp_tftp_mac.py --iface en4 --uart /dev/cu.usbserial-0001
  sudo python3 scripts/f1_bootp_tftp_mac.py --help
"""
from __future__ import annotations

import argparse
import atexit
import os
import select
import shutil
import socket
import struct
import subprocess
import sys
import termios
import threading
import time
from pathlib import Path

DEFAULT_SERVER_IP = "192.168.1.100"
DEFAULT_CLIENT_IP = "192.168.1.2"
DEFAULT_BOOT_FILE = "GCNT-X"
DEFAULT_TEST_PAYLOAD = b"NOT-FIRMWARE-TEST\n"
BOOT_PROMPT = "Press b to enter BOOT-P"
BOOT_START = "U-Boot SPL"
DHCP_MAGIC = b"\x63\x82\x53\x63"
IP_BOUND_IF = 25  # Darwin IPPROTO_IP IP_BOUND_IF


def mac_to_bytes(mac_str: str) -> bytes:
    clean = mac_str.replace(":", "").replace("-", "")
    if len(clean) != 12:
        raise ValueError(f"Invalid MAC address: {mac_str}")
    return bytes.fromhex(clean)


def build_bootp_reply(
    xid: bytes,
    client_mac: bytes,
    server_ip: str = DEFAULT_SERVER_IP,
    offer_ip: str = DEFAULT_CLIENT_IP,
    boot_file: str = DEFAULT_BOOT_FILE,
) -> bytes:
    """Build an RFC 951 / BOOTP reply packet with Technicolor options."""
    if len(xid) != 4:
        raise ValueError("xid must be 4 bytes")
    if len(client_mac) != 6:
        raise ValueError("client_mac must be 6 bytes")

    # BOOTP fixed header is 236 bytes:
    # op(1)=2, htype(1)=1, hlen(1)=6, hops(1)=0, xid(4), secs(2)=0, flags(2)=0x8000
    # ciaddr(4)=0, yiaddr(4)=offer_ip, siaddr(4)=server_ip, giaddr(4)=0
    # chaddr(16)=client_mac + 10 nulls, sname(64)=0, file(128)=boot_file + nulls
    yiaddr = socket.inet_aton(offer_ip)
    siaddr = socket.inet_aton(server_ip)
    chaddr = client_mac.ljust(16, b"\x00")
    file_bytes = boot_file.encode("ascii").ljust(128, b"\x00")[:128]

    hdr = struct.pack(
        "!BBBBIHH4s4s4s4s16s64s128s",
        2,                     # op = BOOTREPLY
        1,                     # htype = Ethernet
        6,                     # hlen = 6
        0,                     # hops = 0
        struct.unpack("!I", xid)[0],
        0,                     # secs = 0
        0x8000,                # flags = broadcast
        b"\x00" * 4,           # ciaddr
        yiaddr,                # yiaddr
        siaddr,                # siaddr
        b"\x00" * 4,           # giaddr
        chaddr,                # chaddr (16B)
        b"\x00" * 64,          # sname (64B)
        file_bytes,            # file (128B)
    )

    # Options (RFC 2132): Magic cookie + Subnet + Router + Server ID + End
    options = bytearray()
    options.extend(DHCP_MAGIC)
    options.extend(b"\x35\x01\x02")                          # Opt 53 (Message Type): 2 (DHCPOFFER / REPLY)
    options.extend(b"\x01\x04\xff\xff\xff\x00")              # Opt 1 (Subnet Mask): 255.255.255.0
    options.extend(b"\x03\x04" + siaddr)                     # Opt 3 (Router): server_ip
    options.extend(b"\x36\x04" + siaddr)                     # Opt 54 (Server Identifier): server_ip
    options.extend(b"\xff")                                  # Opt 255 (End)

    return bytes(hdr + options)


def parse_bootp_request(data: bytes, match_mac: bytes | None = None) -> tuple[bytes, bytes, str] | None:
    """Parse incoming BOOTREQUEST. Return (xid, chaddr, boot_file) or None."""
    if len(data) < 236:
        return None
    op, htype, hlen, _ = struct.unpack("!BBBB", data[:4])
    if op != 1 or htype != 1 or hlen != 6:
        return None
    xid = data[4:8]
    chaddr = data[28:34]
    if match_mac and chaddr != match_mac:
        return None
    raw_file = data[108:236]
    nul = raw_file.find(b"\x00")
    file_name = raw_file[:nul].decode("ascii", "replace") if nul != -1 else ""
    return xid, chaddr, file_name


def parse_tftp_packet(data: bytes) -> tuple[int, dict]:
    """Parse a TFTP packet. Return (opcode, details)."""
    if len(data) < 2:
        return 0, {}
    opcode = struct.unpack("!H", data[:2])[0]
    if opcode == 1:  # RRQ
        parts = data[2:].split(b"\x00")
        filename = parts[0].decode("ascii", "replace") if len(parts) > 0 else ""
        mode = parts[1].decode("ascii", "replace") if len(parts) > 1 else ""
        return opcode, {"filename": filename, "mode": mode}
    elif opcode == 4:  # ACK
        if len(data) >= 4:
            block = struct.unpack("!H", data[2:4])[0]
            return opcode, {"block": block}
        return opcode, {}
    elif opcode == 5:  # ERROR
        errcode = struct.unpack("!H", data[2:4])[0] if len(data) >= 4 else -1
        msg = data[4:].rstrip(b"\x00").decode("ascii", "replace")
        return opcode, {"error_code": errcode, "message": msg}
    return opcode, {"raw": data}


def build_tftp_data(block: int, payload: bytes) -> bytes:
    """Build a TFTP DATA packet (opcode 3)."""
    return struct.pack("!HH", 3, block) + payload


def chunk_tftp_payload(payload: bytes, block_size: int = 512) -> list[bytes]:
    """Splits payload into RFC 1350 blocks. Appends empty block if exact multiple."""
    if not payload:
        return [b""]
    blocks = [payload[i : i + block_size] for i in range(0, len(payload), block_size)]
    if len(blocks[-1]) == block_size:
        blocks.append(b"")
    return blocks


def get_service_name_for_iface(iface: str) -> str | None:
    """Finds macOS network service name corresponding to a BSD interface name."""
    try:
        out = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
        cur_port = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Hardware Port:"):
                cur_port = line.split(":", 1)[1].strip()
            elif line.startswith("Device:") and cur_port:
                dev = line.split(":", 1)[1].strip()
                if dev == iface:
                    return cur_port
    except Exception:
        pass
    return None


def parse_getinfo(output: str) -> dict:
    """Parses `networksetup -getinfo` output into mode, ip, mask, and router."""
    info: dict = {}
    for raw in output.splitlines():
        line = raw.strip()
        if line.endswith("Configuration"):
            info["mode"] = line.split()[0]
        elif ":" in line:
            key, value = (part.strip() for part in line.split(":", 1))
            if key == "IP address":
                info["ip"] = value
            elif key == "Subnet mask":
                info["mask"] = value
            elif key == "Router":
                info["router"] = value
    return info


def snapshot_service(svc: str) -> dict | None:
    """Returns the service's current IP configuration, or None if it cannot be read."""
    try:
        return parse_getinfo(subprocess.check_output(["networksetup", "-getinfo", svc], text=True))
    except Exception:
        return None


def restore_commands(svc: str | None, prior: dict | None, client_ip: str) -> list[list[str]]:
    """Commands that return the service and ARP table to their state before this run."""
    cmds: list[list[str]] = []
    if svc and prior:
        mode = prior.get("mode")
        if mode == "DHCP":
            cmds.append(["networksetup", "-setdhcp", svc])
        elif mode == "Manual" and {"ip", "mask", "router"} <= prior.keys():
            cmds.append(["networksetup", "-setmanual", svc, prior["ip"], prior["mask"], prior["router"]])
    cmds.append(["arp", "-d", client_ip])
    return cmds


def restore_interface(svc: str | None, prior: dict | None, client_ip: str) -> None:
    """Runs the restore commands. Failures are printed and never raised."""
    if svc and not prior:
        print(f"[-] Could not read prior config for '{svc}'; it stays on the static IP.", file=sys.stderr)
    for cmd in restore_commands(svc, prior, client_ip):
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"[*] Restored: {' '.join(cmd)}")
        except Exception as exc:
            print(f"[-] Restore failed for {' '.join(cmd)}: {exc}", file=sys.stderr)


def send_tftp_packet_with_retry(
    sock: socket.socket,
    pkt: bytes,
    addr: tuple[str, int],
    iface: str | None = None,
    mac_str: str | None = None,
    retries: int = 5,
) -> int:
    """Sends a TFTP packet with retry and automatic ARP priming for macOS Darwin."""
    ip, _ = addr
    for i in range(retries):
        try:
            return sock.sendto(pkt, addr)
        except OSError as e:
            if e.errno == 65 and i < retries - 1:  # [Errno 65] No route to host
                # Darwin ARP table or interface route dropped during link bounce
                if mac_str:
                    os.system(f"arp -d {ip} >/dev/null 2>&1")
                    os.system(f"arp -s {ip} {mac_str} >/dev/null 2>&1")
                time.sleep(0.05)
                continue
            raise


class UartPromptTrigger:
    """Detects bootloader prompt in raw streaming UART chunks without requiring newlines."""

    def __init__(self, prompt: str = BOOT_PROMPT, reset_marker: str = BOOT_START):
        self.prompt = prompt
        self.reset_marker = reset_marker
        self.buffer = ""
        self.answered = False
        self.sent_count = 0

    def feed(self, chunk: str) -> bool:
        """Feed incoming text chunk. Returns True immediately if prompt triggered."""
        self.buffer += chunk
        if self.reset_marker in self.buffer:
            self.answered = False
            idx = self.buffer.rfind(self.reset_marker)
            self.buffer = self.buffer[idx:]

        if self.prompt in self.buffer and not self.answered:
            self.answered = True
            self.sent_count += 1
            return True

        if len(self.buffer) > 4096:
            self.buffer = self.buffer[-2048:]
        return False


class UartWatcher(threading.Thread):
    """Watches serial console in a background thread, logging and auto-pressing 'b'."""

    def __init__(self, device: str, log_path: Path):
        super().__init__(daemon=True)
        self.device = device
        self.log_path = log_path
        self.running = True
        self.trigger = UartPromptTrigger()

    @property
    def b_sent_count(self) -> int:
        return self.trigger.sent_count

    def run(self) -> None:
        if not os.path.exists(self.device):
            print(f"[UART] Warning: serial device not found: {self.device}", flush=True)
            return

        try:
            fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY)
            speed = termios.B115200
            attrs = termios.tcgetattr(fd)
            attrs[0] = 0
            attrs[1] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] = 0
            attrs[4] = speed
            attrs[5] = speed
            attrs[6][termios.VMIN] = 1
            attrs[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except Exception as e:
            print(f"[UART] Error opening {self.device}: {e}", flush=True)
            return

        print(f"[UART] Watching {self.device} (auto-b armed)", flush=True)
        with open(self.log_path, "ab") as log:
            while self.running:
                ready, _, _ = select.select([fd], [], [], 0.5)
                if not ready:
                    continue
                try:
                    data = os.read(fd, 4096)
                    if not data:
                        break
                except OSError:
                    break

                log.write(data)
                log.flush()

                chunk = data.decode("utf-8", "replace").replace("\r", "")
                sys.stdout.write(chunk)
                sys.stdout.flush()
                if self.trigger.feed(chunk):
                    # Send 'b' immediately without waiting for a newline!
                    os.write(fd, b"b")
                    stamp = time.strftime("%H:%M:%S")
                    msg = f"\n[{stamp}] [UART] *** DETECTED PROMPT -> SENT 'b' (#{self.b_sent_count}) ***\n"
                    log.write(msg.encode())
                    log.flush()
                    print(msg.strip(), flush=True)

        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--iface", help="macOS Ethernet interface to check/bind (e.g. en4, en5, en10)")
    parser.add_argument("--no-set-ip", action="store_true", help="Do not configure static IP automatically on iface")
    parser.add_argument("--keep-ip", action="store_true", help="Leave the static IP and ARP entry in place after exit")
    parser.add_argument("--uart", default="/dev/cu.usbserial-0001", help="Serial device to watch and auto-press 'b'")
    parser.add_argument("--no-uart", action="store_true", help="Disable UART watching")
    parser.add_argument("--client-mac", default=None, help="Target router MAC address (optional, default: accept any)")
    parser.add_argument("--server-ip", default=DEFAULT_SERVER_IP, help="Mac IP (BOOTP server & TFTP server)")
    parser.add_argument("--client-ip", default=DEFAULT_CLIENT_IP, help="Offered IP for router")
    parser.add_argument("--boot-file", default=DEFAULT_BOOT_FILE, help="Boot file name in BOOTREPLY")
    parser.add_argument("--payload", default="NOT-FIRMWARE-TEST\n", help="Content to serve over TFTP")
    parser.add_argument("--file", help="Path to custom file to serve instead of text payload")
    parser.add_argument("--timeout", type=int, default=180, help="Listen timeout in seconds")
    parser.add_argument("--log-dir", default="artifacts/bootp/live-mac", help="Directory for logs")
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("ERROR: This script must be run with sudo to bind UDP ports 67 (BOOTP) and 69 (TFTP).", file=sys.stderr)
        print("Example: sudo python3 scripts/f1_bootp_tftp_mac.py --iface en4", file=sys.stderr)
        return 1

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    session_log = log_dir / f"session-{ts}.log"
    pcap_path = log_dir / f"session-{ts}.pcap"

    target_mac = mac_to_bytes(args.client_mac) if args.client_mac else None
    last_client_mac = args.client_mac or "00:1e:e3:76:83:61"
    test_payload = Path(args.file).read_bytes() if args.file else args.payload.encode("utf-8")
    tftp_blocks = chunk_tftp_payload(test_payload, block_size=512)
    total_blocks = len(tftp_blocks)

    # Automatic interface IP and routing setup. The prior service config is saved and
    # restored at exit, unless --keep-ip is given.
    if args.iface and not args.no_set_ip:
        svc = get_service_name_for_iface(args.iface)
        prior = snapshot_service(svc) if svc else None
        if svc:
            print(f"[*] Locking macOS manual IP {args.server_ip} on '{svc}' ({args.iface})...")
            os.system(f"networksetup -setmanual '{svc}' {args.server_ip} 255.255.255.0 {args.server_ip} >/dev/null 2>&1")
        print(f"[*] Ensuring static IP {args.server_ip} on {args.iface}...")
        os.system(f"ifconfig {args.iface} {args.server_ip} netmask 255.255.255.0 up >/dev/null 2>&1")
        os.system(f"arp -d {args.client_ip} >/dev/null 2>&1")
        os.system(f"arp -s {args.client_ip} {last_client_mac} >/dev/null 2>&1")
        if not args.keep_ip:
            atexit.register(restore_interface, svc, prior, args.client_ip)

    print(f"=== Telia F1 / GCNT-X macOS BOOTP & TFTP Responder ===")
    print(f"Interface:    {args.iface or 'all'}")
    print(f"Server IP:    {args.server_ip}")
    print(f"Offered IP:   {args.client_ip}")
    print(f"Target MAC:   {args.client_mac or 'any'}")
    print(f"Boot File:    {args.boot_file}")
    print(f"Payload Size: {len(test_payload)} bytes ({total_blocks} TFTP blocks)")
    print(f"Session Log:  {session_log}")

    # Optional background packet capture
    tcpdump_proc = None
    if args.iface and shutil.which("tcpdump"):
        try:
            tcpdump_cmd = [
                "tcpdump", "-i", args.iface, "-nn", "-U", "-w", str(pcap_path),
                "udp port 67 or udp port 68 or udp port 69 or icmp",
            ]
            tcpdump_proc = subprocess.Popen(tcpdump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[*] Live capture: {pcap_path}")
        except Exception as e:
            print(f"[-] Warning: Failed to start tcpdump: {e}")

    # Start UART watcher thread
    uart_thread = None
    if not args.no_uart and os.path.exists(args.uart):
        uart_thread = UartWatcher(args.uart, session_log)
        uart_thread.start()
    else:
        print("[*] UART auto-b disabled or device not found; ensure 'b' is pressed manually.")

    # Setup BOOTP socket (UDP/67)
    bootp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bootp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        bootp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    bootp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Setup TFTP socket (UDP/69)
    tftp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tftp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        tftp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    # Scoping sockets to specific physical interface index on Darwin
    if args.iface:
        try:
            if_idx = socket.if_nametoindex(args.iface)
            bootp_sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, struct.pack("I", if_idx))
            tftp_sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, struct.pack("I", if_idx))
            print(f"[*] Scoped sockets to physical interface {args.iface} (index {if_idx}) via IP_BOUND_IF")
        except Exception as e:
            print(f"[-] Warning: IP_BOUND_IF failed for {args.iface}: {e}", file=sys.stderr)

    try:
        bootp_sock.bind(("0.0.0.0", 67))
        print("[*] Bound UDP/67 for BOOTP")
    except Exception as e:
        print(f"[-] Failed to bind UDP/67: {e}", file=sys.stderr)
        if tcpdump_proc:
            tcpdump_proc.terminate()
        return 1

    # Setup TFTP socket (UDP/69)
    try:
        tftp_sock.bind((args.server_ip, 69))
        print(f"[*] Bound UDP/69 on {args.server_ip} for TFTP")
    except Exception as e:
        # Fallback to 0.0.0.0 if specific IP binding fails
        tftp_sock.bind(("0.0.0.0", 69))
        print(f"[*] Bound UDP/69 on 0.0.0.0 for TFTP")

    deadline = time.time() + args.timeout
    bootp_replies = 0
    tftp_rrq_count = 0
    tftp_ack_received = False

    print(f"[*] Ready. Waiting for router boot (timeout in {args.timeout}s)...")
    print(">>> Power on the router now! <<<")

    with open(session_log, "a") as log:
        log.write(f"=== Session started at {time.ctime()} ===\n")
        try:
            while time.time() < deadline:
                rlist, _, _ = select.select([bootp_sock, tftp_sock], [], [], 1.0)
                for sock in rlist:
                    if sock is bootp_sock:
                        data, addr = bootp_sock.recvfrom(4096)
                        parsed = parse_bootp_request(data, match_mac=target_mac)
                        if parsed:
                            xid, chaddr, file_name = parsed
                            bootp_replies += 1
                            last_client_mac = chaddr.hex(":")
                            xid_hex = xid.hex()
                            msg = f"[{time.strftime('%H:%M:%S')}] BOOTREQUEST from {last_client_mac} xid={xid_hex} (file='{file_name}') -> Replying (#{bootp_replies})\n"
                            print(msg.strip(), flush=True)
                            log.write(msg)
                            log.flush()

                            # Set static ARP for router MAC upon receiving BOOTREQUEST
                            os.system(f"arp -d {args.client_ip} >/dev/null 2>&1")
                            os.system(f"arp -s {args.client_ip} {last_client_mac} >/dev/null 2>&1")

                            reply = build_bootp_reply(
                                xid=xid,
                                client_mac=chaddr,
                                server_ip=args.server_ip,
                                offer_ip=args.client_ip,
                                boot_file=args.boot_file,
                            )
                            for bcast in ("255.255.255.255", "192.168.1.255"):
                                try:
                                    bootp_sock.sendto(reply, (bcast, 68))
                                except Exception as e:
                                    pass
                        else:
                            got_mac = data[28:34].hex(':') if len(data) >= 34 else "unknown"
                            msg = f"[{time.strftime('%H:%M:%S')}] [UDP/67] Received {len(data)}B from {addr} (MAC={got_mac})\n"
                            print(msg.strip(), flush=True)
                            log.write(msg)
                            log.flush()

                    elif sock is tftp_sock:
                        data, client_addr = tftp_sock.recvfrom(4096)
                        opcode, details = parse_tftp_packet(data)
                        if opcode == 1:  # RRQ
                            tftp_rrq_count += 1
                            filename = details.get("filename", "")
                            msg = f"[{time.strftime('%H:%M:%S')}] TFTP RRQ #{tftp_rrq_count} from {client_addr} for '{filename}'\n"
                            print(msg.strip(), flush=True)
                            log.write(msg)
                            log.flush()

                            # Send DATA block 1
                            try:
                                data_pkt = build_tftp_data(block=1, payload=tftp_blocks[0])
                                bytes_sent = send_tftp_packet_with_retry(
                                    tftp_sock,
                                    data_pkt,
                                    client_addr,
                                    iface=args.iface,
                                    mac_str=last_client_mac,
                                )
                                msg2 = f"[{time.strftime('%H:%M:%S')}]   -> Sent DATA block 1/{total_blocks} ({len(tftp_blocks[0])}B, wire {bytes_sent}B) to {client_addr}\n"
                                print(msg2.strip(), flush=True)
                                log.write(msg2)
                                log.flush()
                            except Exception as e:
                                err_msg = f"[{time.strftime('%H:%M:%S')}] [!] Error sending DATA block 1: {e}\n"
                                print(err_msg.strip(), file=sys.stderr, flush=True)
                                log.write(err_msg)
                                log.flush()

                        elif opcode == 4:  # ACK
                            block = details.get("block", 0)
                            msg = f"[{time.strftime('%H:%M:%S')}] TFTP ACK block={block}/{total_blocks} from {client_addr}\n"
                            print(msg.strip(), flush=True)
                            log.write(msg)
                            log.flush()

                            if block < total_blocks:
                                # Send next block
                                next_block = block + 1
                                chunk_data = tftp_blocks[block]
                                try:
                                    data_pkt = build_tftp_data(block=next_block, payload=chunk_data)
                                    bytes_sent = send_tftp_packet_with_retry(
                                        tftp_sock,
                                        data_pkt,
                                        client_addr,
                                        iface=args.iface,
                                        mac_str=last_client_mac,
                                    )
                                    msg2 = f"[{time.strftime('%H:%M:%S')}]   -> Sent DATA block {next_block}/{total_blocks} ({len(chunk_data)}B, wire {bytes_sent}B) to {client_addr}\n"
                                    print(msg2.strip(), flush=True)
                                    log.write(msg2)
                                    log.flush()
                                except Exception as e:
                                    err_msg = f"[{time.strftime('%H:%M:%S')}] [!] Error sending DATA block {next_block}: {e}\n"
                                    print(err_msg.strip(), file=sys.stderr, flush=True)
                                    log.write(err_msg)
                                    log.flush()
                                    log.write(err_msg)
                                    log.flush()
                            elif block == total_blocks:
                                tftp_ack_received = True
                                msg = f"[{time.strftime('%H:%M:%S')}] *** TFTP TRANSFER COMPLETE! All {total_blocks} blocks ACKed! ***\n"
                                print(msg.strip(), flush=True)
                                log.write(msg)
                                log.flush()

                        elif opcode == 5:  # ERROR
                            err = details.get("message", "")
                            code = details.get("error_code", 0)
                            msg = f"[{time.strftime('%H:%M:%S')}] TFTP ERROR {code}: {err}\n"
                            print(msg.strip(), flush=True)
                            log.write(msg)
                            log.flush()

                # If ACK received, wait 15s for the bootloader's action 3 execution logs before closing
                if tftp_ack_received:
                    print("[*] TFTP transfer complete! Waiting 15s to capture bootloader parser output...")
                    time.sleep(15)
                    break

        except KeyboardInterrupt:
            print("\n[*] Stopped by user.")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"\n[!] Unhandled exception in server loop:\n{tb}", file=sys.stderr, flush=True)
            try:
                log.write(f"\n[!] UNHANDLED EXCEPTION:\n{tb}\n")
                log.flush()
            except Exception:
                pass
        finally:
            bootp_sock.close()
            tftp_sock.close()
            if tcpdump_proc:
                try:
                    tcpdump_proc.terminate()
                    tcpdump_proc.wait(timeout=2)
                except Exception:
                    pass
            if uart_thread:
                uart_thread.running = False

    print("\n=== Session Summary ===")
    print(f"BOOTP replies sent:   {bootp_replies}")
    print(f"TFTP RRQs served:     {tftp_rrq_count}")
    print(f"TFTP ACK received:    {tftp_ack_received}")
    print(f"Log written to:       {session_log}")
    return 0 if (bootp_replies > 0 and tftp_rrq_count > 0) else 2


if __name__ == "__main__":
    sys.exit(main())
