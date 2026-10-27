#!/usr/bin/env python3
import socket
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from f1_bootp_tftp_mac import (
    DEFAULT_CLIENT_IP,
    DEFAULT_SERVER_IP,
    DHCP_MAGIC,
    UartPromptTrigger,
    build_bootp_reply,
    build_tftp_data,
    chunk_tftp_payload,
    mac_to_bytes,
    parse_bootp_request,
    parse_tftp_packet,
    send_tftp_packet_with_retry,
)


class TestF1BootpTftpMac(unittest.TestCase):
    def setUp(self):
        self.sample_mac = "00:1e:e3:76:83:61"
        self.sample_mac_bytes = bytes.fromhex("001ee3768361")
        self.sample_xid = bytes.fromhex("e376c3ae")

    def test_mac_to_bytes(self):
        self.assertEqual(mac_to_bytes(self.sample_mac), self.sample_mac_bytes)
        self.assertEqual(mac_to_bytes("00-1E-E3-76-83-61"), self.sample_mac_bytes)
        with self.assertRaises(ValueError):
            mac_to_bytes("invalid_mac")

    def test_build_bootp_reply_layout(self):
        reply = build_bootp_reply(
            xid=self.sample_xid,
            client_mac=self.sample_mac_bytes,
            server_ip=DEFAULT_SERVER_IP,
            offer_ip=DEFAULT_CLIENT_IP,
            boot_file="GCNT-X",
        )
        self.assertGreater(len(reply), 240)

        # RFC 951 / BOOTP offsets
        self.assertEqual(reply[0], 2)  # op = BOOTREPLY
        self.assertEqual(reply[1], 1)  # htype = Ethernet
        self.assertEqual(reply[2], 6)  # hlen = 6
        self.assertEqual(reply[4:8], self.sample_xid)  # xid
        self.assertEqual(reply[10:12], b"\x80\x00")  # broadcast flags
        self.assertEqual(reply[16:20], socket.inet_aton(DEFAULT_CLIENT_IP))  # yiaddr = 192.168.1.2
        self.assertEqual(reply[20:24], socket.inet_aton(DEFAULT_SERVER_IP))  # siaddr = 192.168.1.1
        self.assertEqual(reply[28:34], self.sample_mac_bytes)  # chaddr

        # Boot file name at offset 108
        self.assertTrue(reply[108:].startswith(b"GCNT-X\x00"))

        # Magic cookie at offset 236
        self.assertEqual(reply[236:240], DHCP_MAGIC)

    def test_parse_bootp_request(self):
        # Construct valid 236-byte BOOTREQUEST
        req = bytearray(300)
        req[0] = 1  # op = BOOTREQUEST
        req[1] = 1  # htype
        req[2] = 6  # hlen
        req[4:8] = self.sample_xid
        req[28:34] = self.sample_mac_bytes
        req[108:114] = b"GCNT-X"

        parsed = parse_bootp_request(bytes(req), match_mac=self.sample_mac_bytes)
        self.assertIsNotNone(parsed)
        xid, chaddr, file_name = parsed
        self.assertEqual(xid, self.sample_xid)
        self.assertEqual(chaddr, self.sample_mac_bytes)
        self.assertEqual(file_name, "GCNT-X")

        # Wrong MAC should return None
        other_mac = bytes.fromhex("112233445566")
        self.assertIsNone(parse_bootp_request(bytes(req), match_mac=other_mac))

    def test_build_and_parse_tftp(self):
        payload = b"NOT-FIRMWARE-TEST\n"
        data_pkt = build_tftp_data(block=1, payload=payload)
        self.assertEqual(len(data_pkt), 4 + len(payload))
        opcode, block = struct.unpack("!HH", data_pkt[:4])
        self.assertEqual(opcode, 3)
        self.assertEqual(block, 1)
        self.assertEqual(data_pkt[4:], payload)

        # RRQ packet parsing
        rrq_raw = b"\x00\x01GCNT-X\x00octet\x00"
        opcode, details = parse_tftp_packet(rrq_raw)
        self.assertEqual(opcode, 1)
        self.assertEqual(details["filename"], "GCNT-X")
        self.assertEqual(details["mode"], "octet")

        # ACK packet parsing
        ack_raw = b"\x00\x04\x00\x01"
        opcode, details = parse_tftp_packet(ack_raw)
        self.assertEqual(opcode, 4)
        self.assertEqual(details["block"], 1)

        # ERROR packet parsing
        err_raw = b"\x00\x05\x00\x01File not found\x00"
        opcode, details = parse_tftp_packet(err_raw)
        self.assertEqual(opcode, 5)
        self.assertEqual(details["error_code"], 1)
        self.assertEqual(details["message"], "File not found")

    def test_chunk_tftp_payload(self):
        # Empty payload
        self.assertEqual(chunk_tftp_payload(b""), [b""])

        # Payload under 512 bytes
        p1 = b"A" * 100
        self.assertEqual(chunk_tftp_payload(p1), [p1])

        # Exact 512 bytes requires trailing empty block to signal EOF
        p512 = b"B" * 512
        blocks512 = chunk_tftp_payload(p512)
        self.assertEqual(len(blocks512), 2)
        self.assertEqual(blocks512[0], p512)
        self.assertEqual(blocks512[1], b"")

        # 682 bytes (like test-fit-standard.itb)
        p682 = b"C" * 682
        blocks682 = chunk_tftp_payload(p682)
        self.assertEqual(len(blocks682), 2)
        self.assertEqual(len(blocks682[0]), 512)
        self.assertEqual(len(blocks682[1]), 170)

    def test_send_tftp_packet_with_retry_on_errno_65(self):
        class MockSock:
            def __init__(self):
                self.calls = 0

            def sendto(self, pkt, addr):
                self.calls += 1
                if self.calls == 1:
                    err = OSError("No route to host")
                    err.errno = 65
                    raise err
                return len(pkt)

        sock = MockSock()
        sent = send_tftp_packet_with_retry(sock, b"test", ("127.0.0.1", 1234), retries=3)
        self.assertEqual(sent, 4)
        self.assertEqual(sock.calls, 2)

    def test_uart_prompt_trigger_no_newline(self):
        trigger = UartPromptTrigger()
        # Non-prompt lines
        self.assertFalse(trigger.feed("Gateway initialization sequence started\n"))
        self.assertFalse(trigger.feed("Board Mnemonic      : GCNT-X\n"))
        # U-Boot prints prompt with trailing spaces and NO newline
        self.assertTrue(trigger.feed("*** Press b to enter BOOT-P ***                                                                          "))
        self.assertEqual(trigger.sent_count, 1)
        # Does not retrigger on subsequent output in same boot
        self.assertFalse(trigger.feed("XRDP Ethernet driver un-initialize\n"))
        self.assertEqual(trigger.sent_count, 1)

    def test_uart_prompt_trigger_split_chunk(self):
        trigger = UartPromptTrigger()
        # Prompt arrives split across read boundaries
        self.assertFalse(trigger.feed("Bank duplication not supported\n*** Press b to "))
        self.assertTrue(trigger.feed("enter BOOT-P ***   "))
        self.assertEqual(trigger.sent_count, 1)

    def test_uart_prompt_trigger_reboot_reset(self):
        trigger = UartPromptTrigger()
        self.assertTrue(trigger.feed("*** Press b to enter BOOT-P ***"))
        self.assertEqual(trigger.sent_count, 1)
        # Reboot marker resets trigger
        self.assertFalse(trigger.feed("\nU-Boot SPL 2019.07 (Jan 06 2025)\n"))
        # Next boot prompt triggers again
        self.assertTrue(trigger.feed("*** Press b to enter BOOT-P ***"))
        self.assertEqual(trigger.sent_count, 2)


if __name__ == "__main__":
    unittest.main()
