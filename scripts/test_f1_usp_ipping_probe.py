#!/usr/bin/env python3
import unittest

import f1_usp_ipping_probe as probe


class TcpTests(unittest.TestCase):
    def test_cwmp_skips_soap_when_port_closed(self):
        original = probe.tcp_state

        def closed(_port, timeout=2.0):
            return "closed"

        probe.tcp_state = closed
        try:
            out = probe.cwmp_probe()
        finally:
            probe.tcp_state = original
        self.assertEqual(out["soap"], "skipped")


if __name__ == "__main__":
    unittest.main()
