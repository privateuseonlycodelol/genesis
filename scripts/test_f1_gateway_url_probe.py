#!/usr/bin/env python3
import unittest

from f1_gateway_url_probe import classify_body, login_page


class GatewayUrlClassify(unittest.TestCase):
    def test_login_marker(self):
        body = b'<html><input id="sign-me-in"></html>'
        out = classify_body(body)
        self.assertTrue(out["login_page"])
        self.assertIn("login_form", out["markers"])

    def test_cups_marker(self):
        body = b"prefix No destinations added suffix"
        self.assertIn("cups_empty", classify_body(body)["markers"])


if __name__ == "__main__":
    unittest.main()
