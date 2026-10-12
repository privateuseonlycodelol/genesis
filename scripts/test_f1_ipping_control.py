#!/usr/bin/env python3
"""Offline regressions for the one-shot loopback ping control. No live HTTP."""
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path

import f1_ipping_control as probe


def log_row(stamp, message, process="transformer[12780]"):
    return (
        "<tr><td data-title=\"Date\">%s</td>"
        "<td data-title=\"Facility\">daemon.info</td>"
        "<td data-title=\"Process\">%s</td>"
        "<td data-title=\"Message\">%s</td></tr>"
    ) % (stamp, process, message)


def log_page(rows):
    return ('<table id="logviewer"><tbody>' + "".join(rows) + "</tbody></table>").encode()


HELPER = "async run: &#47;usr&#47;bin&#47;ipping_helper"
OLD = log_row("Oct 12 07:40:01", HELPER)
NEW = log_row("Oct 12 07:46:16", HELPER)


def ping_page():
    return (
        '<div id="send-config_PING"></div>'
        '<span id="Status:">Complete</span>'
        '<span id="Success Count:">1</span>'
        '<span id="Failure Count:">0</span>'
        '<span id="Min Resp Time:">0 ms</span>'
        '<span id="Max Resp Time:">0 ms</span>'
        '<span id="Avg Resp Time:">0 ms</span>'
        '<input type="text" name="ipAddress" value="127.0.0.1">'
        '<table id="pingtrace"><tbody><tr>'
        "<td>64</td><td>127.0.0.1</td><td>0</td><td>64</td><td>0.084</td>"
        "</tr></tbody></table>"
    ).encode()


class ParserTests(unittest.TestCase):
    def test_helper_entity_has_no_logged_arguments(self):
        events = probe.helper_events(probe.parse_log_rows(log_page([OLD])))
        self.assertEqual(events[0]["message"], probe.HELPER_EXACT)
        self.assertFalse(events[0]["arguments_logged"])
        self.assertEqual(events[0]["process"], "transformer[12780]")

    def test_argument_suffix_is_kept_when_printable(self):
        row = log_row("Oct 12 07:46:16", HELPER + " 127.0.0.1")
        event = probe.helper_events(probe.parse_log_rows(log_page([row])))[0]
        self.assertTrue(event["arguments_logged"])
        self.assertTrue(event["message"].endswith(" 127.0.0.1"))

    def test_unsafe_helper_text_is_not_copied(self):
        row = log_row("Oct 12 07:46:16", HELPER + " SUPERSECRET\x01tail")
        event = probe.helper_events(probe.parse_log_rows(log_page([row])))[0]
        self.assertIsNone(event["arguments_logged"])
        self.assertNotIn("SUPERSECRET", json.dumps(event))

    def test_rotation_is_not_a_new_launch(self):
        before = probe.helper_events(probe.parse_log_rows(log_page([NEW, OLD])))
        after = probe.helper_events(probe.parse_log_rows(log_page([NEW])))
        self.assertEqual(probe.new_events(before, after), [])

    def test_same_stamp_duplicate_counts(self):
        before = probe.helper_events(probe.parse_log_rows(log_page([NEW])))
        after = probe.helper_events(probe.parse_log_rows(log_page([NEW, NEW])))
        self.assertEqual(len(probe.new_events(before, after)), 1)

    def test_other_address_in_the_result_table_is_dropped(self):
        body = ping_page().replace(b"127.0.0.1", b"203.0.113.5")
        # The input echo and the trace cell both change; only the trace must drop.
        parsed = probe.parse_ping_result(body)
        self.assertEqual(parsed["trace"], [{"cells": 5, "kept": False}])
        self.assertTrue(parsed["ip_echo"].startswith("<redacted"))

    def test_loopback_result_is_kept(self):
        parsed = probe.parse_ping_result(ping_page())
        self.assertEqual(parsed["trace"][0]["ip"], "127.0.0.1")
        self.assertEqual(parsed["spans"]["Success Count:"], "1")


class SequencingTests(unittest.TestCase):
    def run_case(self, log_bodies, ping_body=None, login_ok=True):
        calls = []
        logs = list(log_bodies)

        class Fake:
            base = "http://192.168.2.1"
            csrf = ""

            def __init__(self, directory):
                self.directory = directory

            def login(self, username, password):
                self.login_user = username
                self.login_password = password
                return (200, "ok") if login_ok else (401, "no")

            def open(self, url, data=None, method="GET", timeout=30):
                calls.append({"url": url, "data": data, "method": method, "timeout": timeout})
                if url.endswith("/login.lp"):
                    return 200, b'<meta name="CSRFtoken" content="login-token">'
                if url.endswith("/gateway.lp"):
                    return 200, b'<meta name="CSRFtoken" content="session-token">23.1.b'
                if "getSessionStatus" in url:
                    return 200, b'{"current_role":"admin"}'
                if url.endswith(probe.PING_PATH) and method == "POST":
                    return 200, ping_body or ping_page()
                if probe.LOG_PATH in url:
                    return 200, logs.pop(0)
                raise AssertionError(url)

        with tempfile.TemporaryDirectory() as directory:
            try:
                outcome = probe.run(Fake(Path(directory)), "dummy-password")
            except probe.StopProbe:
                if login_ok:
                    raise
                return None, calls
        return outcome, calls

    def test_one_loopback_ping_after_a_quiet_pair(self):
        quiet = log_page([OLD])
        after = log_page([NEW, OLD])
        outcome, calls = self.run_case([quiet, quiet, after])
        posts = [call for call in calls if call["method"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["timeout"], 45)
        fields = urllib.parse.parse_qsl(posts[0]["data"].decode())
        self.assertEqual(
            fields,
            [
                ("action", "PING"),
                ("CSRFtoken", "session-token"),
                ("ProtocolVersion", "IPv4"),
                ("ipAddress", "127.0.0.1"),
                ("NumberOfRepetitions", "1"),
                ("DataBlockSize", "56"),
            ],
        )
        self.assertNotIn(b"1.1.1.1", posts[0]["data"])
        self.assertNotIn(b"TRACE", posts[0]["data"])
        self.assertTrue(outcome["ping_sent"])
        self.assertEqual(len(outcome["new_helper"]), 1)
        self.assertFalse(outcome["new_helper"][0]["arguments_logged"])
        self.assertIn("loopback result and a new ipping_helper", outcome["conclusion"])
        self.assertNotIn("session-token", json.dumps(outcome))

    def test_spontaneous_helper_skips_the_ping(self):
        outcome, calls = self.run_case([log_page([OLD]), log_page([NEW, OLD])])
        self.assertFalse(outcome["ping_sent"])
        self.assertFalse(any(call["method"] == "POST" for call in calls))
        self.assertIn("ping was not sent", outcome["conclusion"])

    def test_empty_filter_uses_the_full_log_when_it_already_has_the_helper(self):
        empty = log_page([])
        full = log_page([OLD, log_row("Oct 12 07:39:00", "other line", "nginx")])
        outcome, calls = self.run_case([empty, full, full, log_page([NEW, OLD])])
        self.assertEqual(outcome["log_query"], "")
        self.assertTrue(outcome["ping_sent"])
        log_urls = [call["url"] for call in calls if probe.LOG_PATH in call["url"]]
        self.assertTrue(all("process=" not in url for url in log_urls[1:]))

    def test_empty_filter_stays_when_the_full_log_has_no_helper(self):
        empty = log_page([])
        full = log_page([log_row("Oct 12 07:39:00", "port check", "kernel")])
        after = log_page([NEW])
        outcome, calls = self.run_case([empty, full, empty, empty, after])
        self.assertEqual(outcome["log_query"], "?process=transformer")
        self.assertTrue(outcome["ping_sent"])
        self.assertEqual(len(outcome["new_helper"]), 1)

    def test_login_failure_stops_before_the_log(self):
        outcome, calls = self.run_case([], login_ok=False)
        self.assertIsNone(outcome)
        self.assertFalse(any(probe.LOG_PATH in call["url"] or probe.PING_PATH in call["url"] for call in calls))

    def test_result_without_a_new_log_line_is_a_separate_conclusion(self):
        quiet = log_page([OLD])
        outcome, calls = self.run_case([quiet, quiet, quiet, quiet])
        self.assertTrue(outcome["ping_sent"])
        self.assertEqual(outcome["new_helper"], [])
        self.assertIn("helper log line did not change", outcome["conclusion"])
        self.assertEqual(sum(call["method"] == "POST" for call in calls), 1)


if __name__ == "__main__":
    unittest.main()
