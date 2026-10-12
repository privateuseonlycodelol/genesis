#!/usr/bin/env python3
"""Literal archive fixtures; these establish auditor behavior, not router behavior."""
import tempfile
from pathlib import Path
import unittest
import zipfile
from audit_f1_grab import audit


class AuditTests(unittest.TestCase):
    def make(self, root, index, bodies=None, misses=''):
        path = root / 'fixture.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('INDEX.md', index)
            z.writestr('MISSES.md', misses)
            for name, body in (bodies or {}).items():
                z.writestr(name, body)
        return path

    def test_literal_hash_utf16_and_queue(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.make(Path(d), '| /a.js | 3 | seed | | javascript | ba7816bf |\n'
                          '| /empty.lua | 0 | seed | | http-200 | |\n'
                          '| /unicode.lp | 2 | seed | | http-200 | |\n'
                          '- `/a.js` — seed from seed\n- `/b.js` — seed from seed\n',
                          {'files/a.js': b'abc', 'files/unicode.lp.html': '\U0001f600'})
            r = audit(p)
            self.assertEqual(r['files'][0]['sha256'],
                             'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(r['size_mismatches'], [])
            self.assertEqual(r['hit_hash_mismatches'], [])
            self.assertEqual(r['missing_bodies'], [{'route': '/empty.lua', 'declared_size': 0}])
            self.assertEqual(r['queue_already_finished'], ['/a.js'])
            self.assertEqual(r['queue_unfinished'], ['/b.js'])

    def test_mismatch_unexpected_and_miss_versions(self):
        for miss in ['| /bad.lp | 500 | chase | | now | 5 | error | |',
                     '| /bad.lp | http://router/bad.lp | 500 | chase | | now | 5 | error | |']:
            with tempfile.TemporaryDirectory() as d:
                r = audit(self.make(Path(d), '| /a.js | 7 | seed | | js | deadbeef |',
                                    {'files/a.js': b'abc', 'files/extra': b''}, miss))
                self.assertEqual(r['size_mismatches'], ['/a.js'])
                self.assertEqual(r['hit_hash_mismatches'], ['/a.js'])
                self.assertEqual(r['unexpected_bodies'], ['files/extra'])
                self.assertEqual(r['miss_statuses'], {'500': 1})

    def test_reject_unsafe_member(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.make(Path(d), '', {'../escape': b'abc'})
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                audit(p)

    def test_invalid_utf8_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.make(Path(d), '| /a.js | 1 | seed | | js | |', {'files/a.js': b'\xff'})
            with self.assertRaises(UnicodeDecodeError):
                audit(p)


if __name__ == '__main__':
    unittest.main()
