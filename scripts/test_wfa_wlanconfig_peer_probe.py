#!/usr/bin/env python3
import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wfa_wlanconfig_peer_probe as peer


class Tests(unittest.TestCase):
    def test_nonce_extraction_fixture(self):
        nonce = bytes(range(16))
        payload = peer.wps_tlv(0x104a, b"\x10") + peer.wps_tlv(0x1022, b"\x04") + peer.wps_tlv(0x101a, nonce)
        b64 = base64.b64encode(payload).decode()
        soap = (
            '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Body><u:GetDeviceInfoResponse xmlns:u="{peer.SERVICE}">'
            f"<NewDeviceInfo>{b64}</NewDeviceInfo></u:GetDeviceInfoResponse></s:Body></s:Envelope>"
        ).encode()
        self.assertEqual(peer.enrollee_nonce_from_get_device_info(soap), nonce)

    def test_wrong_state_m1_length(self):
        nonce = bytes(16)
        blob = peer.wrong_state_m1(nonce)
        self.assertEqual(len(blob), 5 + 5 + 20)


if __name__ == "__main__":
    unittest.main()
