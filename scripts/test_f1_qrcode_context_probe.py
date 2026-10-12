#!/usr/bin/env python3
import unittest

from f1_qrcode_context_probe import classify_body, extract_qr_targets, normalize_remote


class QrcodeContextProbeTests(unittest.TestCase):
    def test_normalize_remote(self):
        self.assertEqual(
            normalize_remote("modals/wireless-qrcode-modal.lp?iface=cred0"),
            "/modals/wireless-qrcode-modal.lp?iface=cred0",
        )

    def test_extract_from_fixture_snippet(self):
        html = (
            '<div data-remote="modals/wireless-qrcode-modal.lp?iface=cred0&band6gOnly=1" />'
            '<div data-remote="modals/wireless-qrcode-modal.lp?iface=cred1&band6gOnly=1" />'
        )
        urls = extract_qr_targets(html)
        self.assertEqual(len(urls), 2)
        self.assertTrue(all("iface=cred" in u for u in urls))

    def test_classify_generic_500(self):
        body = b"<html><title>500 Internal Server Error</title></html>"
        c = classify_body(500, body)
        self.assertTrue(c["generic_nginx_500"])
        self.assertFalse(c["qrcode_page_hint"])


if __name__ == "__main__":
    unittest.main()
