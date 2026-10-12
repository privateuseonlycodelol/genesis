#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wfa_wlanconfig_probe as probe


class Tests(unittest.TestCase):
    def test_classify_fault_and_response(self):
        fault = (
            b'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            b"<s:Body><s:Fault><detail><UPnPError>"
            b"<errorCode>501</errorCode></UPnPError></detail></s:Fault></s:Body></s:Envelope>"
        )
        self.assertEqual(
            probe.classify_soap(fault),
            {"soap_fault": True, "upnp_error_code": 501, "response_action": None},
        )
        ok = (
            b'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            b'<s:Body><u:PutMessageResponse xmlns:u="' + probe.SERVICE.encode() + b'"/>'
            b"</s:Body></s:Envelope>"
        )
        parsed = probe.classify_soap(ok)
        self.assertFalse(parsed["soap_fault"])
        self.assertEqual(parsed["response_action"], "PutMessageResponse")

    def test_scpd_fixture(self):
        body = b"""<?xml version="1.0"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
<actionList>
<action><name>GetDeviceInfo</name></action>
<action><name>PutMessage</name></action>
<action><name>PutWLANResponse</name></action>
<action><name>SetSelectedRegistrar</name></action>
</actionList>
</scpd>"""
        self.assertTrue(probe._scpd_valid(body))
        self.assertFalse(probe._scpd_valid(b"<html></html>"))


if __name__ == "__main__":
    unittest.main()
