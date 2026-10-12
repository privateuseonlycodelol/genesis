#!/usr/bin/env python3
import unittest
from pathlib import Path

import cups_ipp_readonly_matrix as matrix


class CupsIppEncoderTests(unittest.TestCase):
    def test_get_printers_matches_prior_fixture(self):
        fixture = Path(__file__).resolve().parents[1] / "artifacts/management/protocol-control/get-printers.request.private"
        encoded = matrix.build_ipp_request(0x4002, (("requested-attributes", "printer-state", matrix.IPP_TAG_KEYWORD),))
        self.assertEqual(encoded, fixture.read_bytes())

    def test_decode_known_response_status(self):
        body = b"\x01\x01\x04\x06" + b"\x00" * 20 + b"No destinations added."
        code, name = matrix.decode_ipp_status(body)
        self.assertEqual(code, 0x0406)
        self.assertEqual(name, "client-error-not-found-cups")


if __name__ == "__main__":
    unittest.main()
