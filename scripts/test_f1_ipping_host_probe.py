#!/usr/bin/env python3
"""Offline sequencing for the two fixed host checks. No live HTTP."""
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path

import f1_ipping_host_probe as probe


def log_page(messages):
    rows = []
    for message in messages:
        rows.append(
            "<tr><td data-title=\"Date\">Oct 12 08:30:00</td>"
            "<td data-title=\"Facility\">user.notice</td>"
            "<td data-title=\"Process\">logger</td>"
            "<td data-title=\"Message\">%s</td></tr>" % message
        )
    return ('<table id="logviewer">' + "".join(rows) + "</table>").encode()


def helper_page():
    return log_page(["async run: &#47;usr&#47;bin&#47;ipping_helper"]).replace(
        b"logger", b"transformer[12780]"
    )


def reject_page():
    return (
        b'<input name="ipAddress" value="x">'
        b'<span id="Status:">Please enter valid ipv4/domain address</span>'
        b"Please enter valid ipv4/domain address"
    )


def ongoing_page():
    return (
        b'<div id = "stop-config_PING"></div><span id="Status:">Ongoing</span>'
        b'<input name="ipAddress" value="127.0.0.1">'
        b'<table id="pingtrace"><tbody></tbody></table>'
    )


class ProbeTests(unittest.TestCase):
    def run_case(self, posts):
        calls = []
        posted = list(posts)

        class Fake:
            base = "http://192.168.2.1"
            csrf = ""

            def __init__(self, directory):
                self.directory = directory

            def login(self, username, password):
                return 200, "ok"

            def open(self, url, data=None, method="GET", timeout=30):
                calls.append({"url": url, "data": data, "method": method})
                if url.endswith("/login.lp"):
                    return 200, b'<meta name="CSRFtoken" content="login-token">'
                if url.endswith("/gateway.lp"):
                    return 200, b'<meta name="CSRFtoken" content="session-token">'
                if "getSessionStatus" in url:
                    return 200, b'{"current_role":"admin"}'
                if method == "POST":
                    fields = dict(urllib.parse.parse_qsl(data.decode()))
                    return posted.pop(0)(fields)
                if "process=transformer" in url:
                    return 200, log_page([])
                return 200, log_page([])

        with tempfile.TemporaryDirectory() as directory:
            outcome = probe.run_probe(Fake(Path(directory)), "dummy-password")
        return outcome, calls

    def test_rejected_newline_continues_to_the_backtick_label(self):
        def respond(fields):
            self.assertEqual(fields["NumberOfRepetitions"], "1")
            self.assertEqual(fields["DataBlockSize"], "56")
            self.assertNotIn("1.1.1.1", fields["ipAddress"])
            return 200, reject_page()

        outcome, calls = self.run_case([respond, respond])
        hosts = [
            urllib.parse.parse_qs(call["data"].decode())["ipAddress"][0]
            for call in calls
            if call["method"] == "POST"
        ]
        self.assertEqual(hosts, [probe.NEWLINE_HOST, probe.BACKTICK_HOST])
        self.assertIn("both rejected", outcome["conclusion"])
        self.assertNotIn("session-token", json.dumps(outcome))

    def test_marker_stops_after_one_id_read(self):
        def newline(_fields):
            return 200, ongoing_page()

        def identify(_fields):
            return 200, ongoing_page()

        seen = {"n": 0}

        class Sequenced:
            def __init__(self):
                self.posts = [newline, identify]

            def __call__(self, fields):
                return self.posts.pop(0)(fields)

        # The full-log GETs are every log read without the transformer query.
        # First is the baseline (no marker). After the newline POST the script
        # reads the transformer log, then the full log. Supply the marker there
        # by patching run-level behavior through a custom open in run_case.
        outcome, calls = self.run_case_with_marker()
        hosts = [
            urllib.parse.parse_qs(call["data"].decode())["ipAddress"][0]
            for call in calls
            if call["method"] == "POST"
        ]
        self.assertEqual(hosts[0], probe.NEWLINE_HOST)
        self.assertEqual(hosts[1], probe.ID_HOST)
        self.assertNotIn(probe.BACKTICK_HOST, hosts)
        self.assertIn("logger marker appeared", outcome["conclusion"])
        self.assertTrue(any("uid=" in hit["message"] for hit in outcome["tests"][-1]["markers"]))

    def run_case_with_marker(self):
        calls = []
        full_reads = {"n": 0}

        class Fake:
            base = "http://192.168.2.1"
            csrf = ""

            def __init__(self, directory):
                self.directory = directory

            def login(self, username, password):
                return 200, "ok"

            def open(self, url, data=None, method="GET", timeout=30):
                calls.append({"url": url, "data": data, "method": method})
                if url.endswith("/login.lp"):
                    return 200, b'<meta name="CSRFtoken" content="login-token">'
                if url.endswith("/gateway.lp"):
                    return 200, b'<meta name="CSRFtoken" content="session-token">'
                if "getSessionStatus" in url:
                    return 200, b'{"current_role":"admin"}'
                if method == "POST":
                    return 200, ongoing_page()
                if "process=transformer" in url:
                    return 200, log_page(["async run: /usr/bin/ipping_helper"])
                full_reads["n"] += 1
                if full_reads["n"] == 1:
                    return 200, log_page(["ordinary"])
                if full_reads["n"] == 2:
                    return 200, log_page([probe.MARKER])
                return 200, log_page([probe.MARKER + " uid=0(root)"])

        with tempfile.TemporaryDirectory() as directory:
            outcome = probe.run_probe(Fake(Path(directory)), "dummy-password")
        return outcome, calls


class FieldTests(unittest.TestCase):
    def test_duplicate_hosts_keep_order(self):
        fields = probe.ping_fields("token", ["127.0.0.1", probe.NEWLINE_HOST])
        hosts = [value for name, value in fields if name == "ipAddress"]
        self.assertEqual(hosts, ["127.0.0.1", probe.NEWLINE_HOST])
        encoded = urllib.parse.urlencode(fields)
        self.assertEqual(encoded.count("ipAddress="), 2)
        self.assertNotIn("1.1.1.1", encoded)


if __name__ == "__main__":
    unittest.main()
