#!/usr/bin/env python3
"""Literal fixtures exercise archive deltas independently of router behavior."""
from pathlib import Path
import tempfile
import unittest
import zipfile
from compare_f1_grabs import compare


def fixture(path, index, misses='', bodies=None):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('INDEX.md', index)
        z.writestr('MISSES.md', misses)
        for name, body in (bodies or {}).items():
            z.writestr(name, body)
    return path


class ComparisonTests(unittest.TestCase):
    def test_content_change_not_status_change(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            index = '| /a.js | 3 | seed | | js | |'
            old = fixture(p/'old.zip', index, bodies={'files/a.js': 'abc'})
            new = fixture(p/'new.zip', index, bodies={'files/a.js': 'def'})
            r = compare(old, new)
            self.assertEqual(r['record_transitions'], [])
            self.assertEqual([x['member'] for x in r['changed_members']], ['files/a.js'])
            self.assertEqual(r['changed_members'][0]['old_sha256'],
                             'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_missing_body_pending_not_404(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            old = fixture(p/'old.zip', '| /a.lp | 3 | seed | | html | |',
                          bodies={'files/a.lp.html': 'abc'})
            new = fixture(p/'new.zip', '- `/a.lp` — seed from seed\n')
            r = compare(old, new)
            self.assertEqual(r['removed_members'], ['files/a.lp.html'])
            self.assertEqual(r['record_transitions'],
                             [{'route': '/a.lp', 'old_status': '200',
                               'new_status': None, 'queued_in_new': True}])

    def test_miss_to_hit_and_new_route(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            old = fixture(p/'old.zip', '', '| /a.js | 404 | guess | | | 1 | error | |')
            new = fixture(p/'new.zip', '| /a.js | 3 | seed | | js | |\n'
                          '| /b.js | 3 | seed | | js | |', bodies={
                              'files/a.js': 'abc', 'files/b.js': 'def'})
            r = compare(old, new)
            self.assertEqual(r['new_completed_routes'], ['/b.js'])
            self.assertEqual(r['record_transitions'][0]['old_status'], '404')
            self.assertEqual(r['record_transitions'][0]['new_status'], '200')

    def test_unchanged_error_is_not_new_success(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            miss = '| /qr.lp | http://router/qr.lp | 500 | seed | | | 1 | error | |'
            old, new = fixture(p/'old.zip', '', miss), fixture(p/'new.zip', '', miss)
            r = compare(old, new)
            self.assertEqual(r['record_transitions'], [])
            self.assertEqual(r['summary']['new']['miss_statuses'], {'500': 1})


if __name__ == '__main__':
    unittest.main()
