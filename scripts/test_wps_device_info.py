#!/usr/bin/env python3
"""Literal WPS wire fixtures; structural checks are not crypto verification."""
import base64
import unittest
import wps_device_info as wps


class Tests(unittest.TestCase):
    def test_literal_version_and_m1_type(self):
        result = wps.parse_tlvs(bytes.fromhex('104a0001101022000104'))
        self.assertEqual(result['version_byte'], 16)
        self.assertEqual(result['message_type_byte'], 4)
        self.assertEqual(result['attributes'], [{'type':'0x104a','length':1}, {'type':'0x1022','length':1}])
        self.assertFalse(result['m1_core_structure'])

    def test_truncation_and_duplicate_critical(self):
        for data in (b'\x10', bytes.fromhex('104a000210'), bytes.fromhex('104a000110104a000110')):
            with self.assertRaises(ValueError):
                wps.parse_tlvs(data)

    def test_structural_fixture_not_cryptographic_m1(self):
        # Literal wire tags and lengths, with deliberately dummy nonce/key.
        data = bytes.fromhex('104a0001101022000104101a0010') + bytes(16) + bytes.fromhex('103200c0') + bytes(192)
        self.assertTrue(wps.parse_tlvs(data)['m1_core_structure'])
        self.assertFalse(wps.parse_tlvs(data.replace(bytes.fromhex('1022000104'), bytes.fromhex('1022000105')))['m1_core_structure'])

    def test_soap_response_and_fault(self):
        payload = base64.b64encode(bytes.fromhex('104a0001101022000104')).decode()
        envelope = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>{}</s:Body></s:Envelope>'
        reply = '<u:GetDeviceInfoResponse xmlns:u="' + wps.SERVICE + '"><NewDeviceInfo>' + payload + '</NewDeviceInfo></u:GetDeviceInfoResponse>'
        self.assertEqual(wps.parse_soap(envelope.format(reply).encode())['message_type_byte'], 4)
        fault = '<s:Fault><detail><UPnPError><errorCode>501</errorCode></UPnPError></detail></s:Fault>'
        self.assertEqual(wps.parse_soap(envelope.format(fault).encode()), {'soap_fault':True,'upnp_error_code':501})
        for bad in (b'<html>login</html>', envelope.format('<NewDeviceInfo>bad*</NewDeviceInfo>').encode()):
            with self.assertRaises(ValueError):
                wps.parse_soap(bad)


if __name__ == '__main__':
    unittest.main()
