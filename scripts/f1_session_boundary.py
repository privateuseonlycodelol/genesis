#!/usr/bin/env python3
"""One normal SRP login and paced cookie/CSRF read-export boundary controls.

Password is terminal-only. No settings, reboot, upload or firmware operations.
Exports can create temporary backend files; all raw evidence stays private.
"""
import copy
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from f1_srp_login import SRPClient
from management_boundary_probe import classify

ROOT = Path(__file__).resolve().parents[1]
STATUS = '/gateway.lp?auto_update=true&getSessionStatus=true'
EXPORT = '/modals/system-config-modal.lp'


class StopExperiment(RuntimeError):
    pass


def token(body):
    match = re.search(rb'CSRFtoken["\']\s+content\s*=\s*["\']([^"\']+)', body, re.I)
    if not match:
        raise StopExperiment('No CSRF meta token in control page')
    return match.group(1).decode()


def export_envelope(body):
    boundary = body.find(b'\n\n', 0, 4096)
    lines = body[:boundary].splitlines() if boundary >= 0 else []
    return (len(lines) >= 2 and all(b'=' in line for line in lines)
            and boundary >= 0 and len(body) - boundary - 2 >= 52
            and (len(body) - boundary - 2 - 36) % 16 == 0)


def load_imported_jar(client, path):
    client.jar.load(str(path), ignore_discard=True, ignore_expires=True)
    # Netscape jars written by curl use 0 for session cookies. Python loads
    # this as epoch expiry and otherwise drops the cookie before sending.
    for cookie in client.jar:
        if cookie.expires == 0:
            cookie.expires = None
            cookie.discard = True


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Evidence:
    def __init__(self, directory):
        self.directory = directory
        self.rows = []
        self.facts = {}

    def save(self):
        (self.directory / 'summary.json').write_text(json.dumps(
            {'requests': self.rows, 'comparisons': self.facts}, indent=2) + '\n')


class Session(SRPClient):
    def __init__(self, evidence, label):
        super().__init__(str(evidence.directory / (label + '.cookies.txt')), 'http://192.168.2.1')
        self.evidence = evidence
        self.label = label
        self.case = label

    def _open(self, url, data=None, method='GET'):
        if self.evidence.rows:
            time.sleep(3)
        request = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                             urllib.request.HTTPCookieProcessor(self.jar))
        try:
            response = opener.open(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            code = response.code
            body = response.read(1048577)
            headers = response.headers.as_bytes()
        self.save_jar()
        index = len(self.evidence.rows) + 1
        prefix = self.evidence.directory / f'response-{index:02d}'
        Path(str(prefix) + '.body.private').write_bytes(body)
        Path(str(prefix) + '.headers.private').write_bytes(headers)
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        fields = urllib.parse.parse_qs(data.decode()) if data else {}
        row = {'request': index, 'session': self.label, 'case': self.case, 'method': method,
               'path': parsed.path, 'action': fields.get('action', query.get('action', [None]))[0],
               'status': code, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
               **classify(body), 'export_envelope': export_envelope(body)}
        self.evidence.rows.append(row)
        self.evidence.save()
        print(json.dumps(row), flush=True)
        if code == 503 or len(body) > 1048576:
            raise StopExperiment('503 or response-size limit; stopped immediately')
        return code, body


def require_admin(client, case):
    client.case = case
    code, body = client._open(client.base + STATUS)
    if code != 200 or classify(body).get('current_role') != 'admin':
        raise StopExperiment('Authenticated admin-role control failed')


def post_export(client, csrf, case, expect_export=False):
    client.case = case
    fields = {'action': 'export_config'}
    if csrf is not None:
        fields['CSRFtoken'] = csrf
    code, body = client._open(client.base + EXPORT, urllib.parse.urlencode(fields).encode(), 'POST')
    is_export = code == 200 and export_envelope(body) and not classify(body)['login_marker']
    if expect_export and not is_export:
        raise StopExperiment('Correct-token export positive control failed')
    if not expect_export and is_export:
        raise StopExperiment('Unexpected export in negative control; preserved for investigation')
    return {'status': code, 'login_marker': classify(body)['login_marker'], 'export_envelope': is_export}


def experiment(evidence, password, anonymous_cookie=None, other_anonymous_cookie=None):
    admin = Session(evidence, 'login-session')
    if anonymous_cookie:
        load_imported_jar(admin, anonymous_cookie)
    admin.case = 'pre-login-page'
    code, body = admin._open(admin.base + '/login.lp')
    if code != 200 or not classify(body)['login_marker']:
        raise StopExperiment('Pre-login page control failed')
    pre_token = token(body)
    admin.csrf = pre_token
    admin.case = 'pre-login-role-negative-control'
    code, role_body = admin._open(admin.base + STATUS)
    if code != 200 or not classify(role_body)['login_marker']:
        raise StopExperiment('Pre-login session was not verified anonymous')
    old = Session(evidence, 'pre-login-cookie-copy')
    # CookieJar contains an uncopyable thread lock. Copy individual cookies,
    # preserving an independent jar and its original filename/policy.
    for cookie in admin.jar:
        old.jar.set_cookie(copy.copy(cookie))
    old.save_jar()
    pre_ids = [(c.name, c.value) for c in admin.jar]
    admin.case = 'normal-srp-login'
    code, result = admin.login('User', password)
    if code != 200 or result != 'ok':
        raise StopExperiment('SRP server proof not verified; no retry')
    post_ids = [(c.name, c.value) for c in admin.jar]
    evidence.facts['srp_server_proof_verified'] = True
    evidence.facts['cookie_values_changed_after_login'] = pre_ids != post_ids
    admin.case = 'authenticated-page'
    code, body = admin._open(admin.base + '/gateway.lp')
    if code != 200 or classify(body)['login_marker']:
        raise StopExperiment('Authenticated page control failed')
    current_token = token(body)
    evidence.facts['csrf_changed_after_login'] = pre_token != current_token
    require_admin(admin, 'admin-positive-before-boundary-tests')
    old.case = 'pre-login-cookie-after-successful-login'
    code, body = old._open(old.base + STATUS)
    evidence.facts['old_cookie_role_control'] = {'status': code, **classify(body)}
    require_admin(admin, 'admin-positive-after-old-cookie-test')
    anonymous = Session(evidence, 'independent-anonymous')
    if other_anonymous_cookie:
        load_imported_jar(anonymous, other_anonymous_cookie)
    anonymous.case = 'independent-anonymous-page'
    code, body = anonymous._open(anonymous.base + '/login.lp')
    if code != 200 or not classify(body)['login_marker']:
        raise StopExperiment('Independent anonymous page control failed')
    other_token = token(body)
    evidence.facts['independent_anonymous_token_differs'] = other_token != current_token
    if other_token == current_token:
        raise StopExperiment('Tokens unexpectedly equal; cross-session test not discriminating')
    evidence.facts['admin_with_other_session_token'] = post_export(admin, other_token, 'admin-export-other-session-token')
    evidence.facts['admin_without_token'] = post_export(admin, None, 'admin-export-no-token')
    if pre_token != current_token:
        evidence.facts['admin_with_prelogin_token'] = post_export(admin, pre_token, 'admin-export-pre-login-token')
    evidence.facts['anonymous_with_admin_token'] = post_export(anonymous, current_token, 'anonymous-export-admin-token')
    require_admin(admin, 'admin-positive-before-correct-export')
    evidence.facts['admin_with_correct_token'] = post_export(admin, current_token, 'admin-export-correct-token', True)
    require_admin(admin, 'admin-positive-after-correct-export')
    evidence.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anonymous-cookie', type=Path, help='reuse a previously issued anonymous jar; original stays unchanged')
    parser.add_argument('--other-anonymous-cookie', type=Path, help='second independently issued anonymous jar for cross-session control')
    args = parser.parse_args()
    os.umask(0o077)
    directory = ROOT / 'artifacts/management' / ('session-boundary-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    evidence = Evidence(directory)
    password = getpass.getpass('F1 web-admin password (not echoed): ')
    try:
        experiment(evidence, password, args.anonymous_cookie, args.other_anonymous_cookie)
        print('Completed paired session/CSRF controls. Private evidence: ' + str(directory))
        return 0
    except (StopExperiment, urllib.error.URLError, TimeoutError) as error:
        evidence.save()
        print('Stopped: ' + (str(error) if isinstance(error, StopExperiment) else type(error).__name__))
        print('Private evidence: ' + str(directory))
        return 1
    finally:
        del password


if __name__ == '__main__':
    raise SystemExit(main())
