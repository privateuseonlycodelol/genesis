#!/usr/bin/env python3
"""Offline negative controls for the paired session-boundary experiment."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from http.cookiejar import Cookie, MozillaCookieJar

import f1_session_boundary as boundary


class Tests(unittest.TestCase):
    def test_curl_zero_expiry_session_cookie_is_sent(self):
        import urllib.request
        class Fake:
            jar = MozillaCookieJar()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'curl-jar.txt'
            path.write_text('# Netscape HTTP Cookie File\n192.168.2.1\tFALSE\t/\tFALSE\t0\tsessionID\tdummy-session\n')
            client = Fake()
            boundary.load_imported_jar(client, path)
            req = urllib.request.Request('http://192.168.2.1/login.lp')
            client.jar.add_cookie_header(req)
            self.assertEqual(req.get_header('Cookie'), 'sessionID=dummy-session')
            self.assertIsNone(next(iter(client.jar)).expires)

    def test_token_extraction(self):
        self.assertEqual(boundary.token(b'<meta name="CSRFtoken" content="literal-fixture">'), 'literal-fixture')
        with self.assertRaises(boundary.StopExperiment):
            boundary.token(b'<html>not a token</html>')

    def test_export_envelope_negative_controls(self):
        for body in (b'', b'<html>login</html>', b'{"success":true}', b'A=x\nB=y\n\nshort'):
            self.assertFalse(boundary.export_envelope(body))

    def test_http_200_html_is_not_an_export(self):
        class Fake:
            base = 'http://192.168.2.1'
            def _open(self, *args):
                return 200, b'<html><button id="sign-me-in">login</button></html>'
        self.assertFalse(boundary.post_export(Fake(), 'dummy', 'negative')['export_envelope'])
        with self.assertRaises(boundary.StopExperiment):
            boundary.post_export(Fake(), 'dummy', 'positive', True)

    def test_failed_srp_stops_before_any_export(self):
        calls = []
        class Fake:
            base = 'http://192.168.2.1'
            def __init__(self, evidence, label):
                self.jar = MozillaCookieJar()
            def save_jar(self):
                pass
            def _open(self, url, *args):
                calls.append(url)
                return 200, b'<html><meta name="CSRFtoken" content="fixture"><button id="sign-me-in"></button></html>'
            def login(self, *args):
                return 401, 'not-verified'
        with tempfile.TemporaryDirectory() as directory, patch.object(boundary, 'Session', Fake):
            with self.assertRaises(boundary.StopExperiment):
                boundary.experiment(boundary.Evidence(Path(directory)), 'test-only')
        self.assertEqual(calls, ['http://192.168.2.1/login.lp', 'http://192.168.2.1' + boundary.STATUS])

    def test_paired_controls_keep_old_cookie_independent(self):
        login = b'<html><meta name="CSRFtoken" content="pre-A"><button id="sign-me-in"></button></html>'
        calls = []
        import urllib.parse
        class Fake:
            base = 'http://192.168.2.1'
            def __init__(self, evidence, label):
                self.label = label
                self.jar = MozillaCookieJar()
            def save_jar(self):
                pass
            def put_cookie(self, value):
                self.jar.set_cookie(Cookie(0, 'sessionID', value, None, False,
                    '192.168.2.1', False, False, '/', True, False, None, True,
                    None, None, {}, False))
            def login(self, username, password):
                self.put_cookie('authenticated-A')
                return 200, 'ok'
            def _open(self, url, data=None, method='GET'):
                cookie = next(iter(self.jar), None)
                identity = cookie.value if cookie else None
                calls.append((self.label, identity, url, data))
                if url.endswith('/login.lp'):
                    if self.label == 'independent-anonymous':
                        self.put_cookie('anonymous-B')
                        return 200, login.replace(b'pre-A', b'anon-B')
                    self.put_cookie('anonymous-A')
                    return 200, login
                if 'getSessionStatus' in url:
                    return (200, b'{"current_role":"admin"}') if identity == 'authenticated-A' else (200, login)
                if url.endswith('/gateway.lp'):
                    return 200, b'<html><meta name="CSRFtoken" content="post-A"></html>'
                fields = urllib.parse.parse_qs(data.decode())
                if identity != 'authenticated-A':
                    return 200, login
                if fields.get('CSRFtoken') != ['post-A']:
                    return 403, b'<html>Forbidden</html>'
                return 200, b'A=x\nB=y\n\n' + bytes(52)
        with tempfile.TemporaryDirectory() as directory, patch.object(boundary, 'Session', Fake):
            evidence = boundary.Evidence(Path(directory))
            boundary.experiment(evidence, 'test-only')
        self.assertTrue(evidence.facts['cookie_values_changed_after_login'])
        self.assertTrue(evidence.facts['csrf_changed_after_login'])
        self.assertTrue(evidence.facts['old_cookie_role_control']['login_marker'])
        for name in ('admin_with_other_session_token', 'admin_without_token', 'admin_with_prelogin_token'):
            self.assertEqual(evidence.facts[name]['status'], 403)
        self.assertTrue(evidence.facts['anonymous_with_admin_token']['login_marker'])
        self.assertTrue(evidence.facts['admin_with_correct_token']['export_envelope'])
        old_calls = [c for c in calls if c[0] == 'pre-login-cookie-copy']
        self.assertEqual(old_calls[0][1], 'anonymous-A')


if __name__ == '__main__':
    unittest.main()
