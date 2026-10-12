#!/usr/bin/env python3
"""Synthetic privacy regression checks for inspect_ui_har.py."""

import json
import unittest

from inspect_ui_har import safe_path, summarize_entry


class HarInspectorPrivacyTests(unittest.TestCase):
    def serialized(self, entry):
        return json.dumps(summarize_entry(entry), sort_keys=True)

    def test_allowlisted_post_reports_only_safe_metadata(self):
        entry = {
            "request": {
                "method": "POST",
                "url": "https://router.invalid/modals/system-config-modal.lp?owner=secret-id",
                "headers": [
                    {"name": "Cookie", "value": "cookie-secret"},
                    {"name": "X-CSRFToken", "value": "header-token-secret"},
                ],
                "postData": {
                    "mimeType": "application/x-www-form-urlencoded",
                    "params": [
                        {"name": "action", "value": "export_config"},
                        {"name": "CSRFtoken", "value": "body-token-secret"},
                    ],
                },
            },
            "response": {
                "status": 200,
                "headers": [{"name": "Set-Cookie", "value": "set-cookie-secret"}],
                "content": {
                    "mimeType": "application/json",
                    "text": '{"success":"private-value","unknown-short-key":"private-value"}',
                },
            },
        }
        result = summarize_entry(entry)
        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual(result["path"], "/modals/system-config-modal.lp")
        self.assertEqual(result["request_body_class"], "form")
        self.assertEqual(result["request_action"], "export_config")
        self.assertTrue(result["request_body_csrf_present"])
        self.assertTrue(result["request_csrf_header_present"])
        self.assertTrue(result["request_cookie_header_present"])
        self.assertTrue(result["response_set_cookie_header_present"])
        self.assertEqual(result["json_top_level_keys"], ["<redacted>", "success"])
        for secret in (
            "router.invalid",
            "secret-id",
            "cookie-secret",
            "header-token-secret",
            "body-token-secret",
            "set-cookie-secret",
            "private-value",
            "unknown-short-key",
        ):
            self.assertNotIn(secret, serialized)

    def test_unknown_short_path_action_and_json_key_are_redacted(self):
        entry = {
            "request": {
                "method": "POST",
                "url": "http://router.invalid/x?token=q9",
                "postData": {
                    "mimeType": "application/x-www-form-urlencoded",
                    "text": "action=q&CSRFtoken=csrf-secret",
                },
            },
            "response": {
                "status": 200,
                "content": {"mimeType": "application/json", "text": '{"x":"value-secret"}'},
            },
        }
        result = summarize_entry(entry)
        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual(result["path"], "<redacted>")
        self.assertEqual(result["request_action"], "<redacted>")
        self.assertEqual(result["json_top_level_keys"], ["<redacted>"])
        self.assertTrue(result["request_body_csrf_present"])
        for secret in ("router.invalid", "q9", "csrf-secret", "value-secret", '"x"'):
            self.assertNotIn(secret, serialized)

    def test_known_form_without_action_and_unknown_path(self):
        entry = {
            "request": {
                "method": "POST",
                "url": "http://router.invalid/modals/ethernet-modal.lp",
                "postData": {
                    "mimeType": "application/x-www-form-urlencoded",
                    "params": [{"name": "CSRFtoken", "value": "private-token"}],
                },
            },
            "response": {"status": 200, "content": {"mimeType": "text/html", "text": "<html></html>"}},
        }
        result = summarize_entry(entry)
        self.assertEqual(result["path"], "/modals/ethernet-modal.lp")
        self.assertEqual(result["request_action"], "")
        self.assertEqual(result["request_body_class"], "form")
        self.assertTrue(result["request_body_csrf_present"])
        self.assertNotIn("private-token", self.serialized(entry))
        self.assertEqual(safe_path("http://router.invalid/u?x=123"), "<redacted>")


if __name__ == "__main__":
    unittest.main()
