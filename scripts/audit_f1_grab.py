#!/usr/bin/env python3
"""Offline ZIP/index reconciliation; emit metadata only, never response bodies."""
import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def table_rows(text):
    return [[c.strip() for c in line.split('|')[1:-1]]
            for line in text.splitlines() if line.startswith('| /')]


def member_for(route):
    name = 'files/' + route.lstrip('/').replace('/', '__')
    return name + '.html' if route.endswith('.lp') else name


def audit(path, baseline=None):
    result = {'archive_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if len(names) != len(set(names)):
            raise ValueError('duplicate ZIP members')
        if sum(e.file_size for e in entries) > 32 * 1024 * 1024:
            raise ValueError('archive exceeds 32 MiB audit limit')
        for entry in entries:
            p = PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in entry.filename:
                raise ValueError('unsafe member path')
        bad_crc = archive.testzip()
        if bad_crc:
            raise ValueError('ZIP CRC check failed')
        index = archive.read('INDEX.md').decode('utf-8')
        misses = archive.read('MISSES.md').decode('utf-8')
        hits = table_rows(index)
        miss_rows = table_rows(misses)
        # v1.3.2 added a URL column to misses; support both shapes.
        status_col = 2 if miss_rows and miss_rows[0][1].startswith('http') else 1
        queue = re.findall(r'^- `([^`]+)` — ([^\n]+)', index, re.M)
        finished = {r[0] for r in hits + miss_rows}
        result.update(zip_members=len(entries), crc_check='passed',
                      body_members=sum(n.startswith('files/') for n in names),
                      hit_rows=len(hits), miss_rows=len(miss_rows),
                      miss_statuses=dict(collections.Counter(r[status_col] for r in miss_rows)),
                      miss_methods=dict(collections.Counter(r[status_col + 1] for r in miss_rows)),
                      queue_entries=len(queue), queue_unique=len({p for p, _ in queue}),
                      queue_already_finished=sorted({p for p, _ in queue if p in finished}),
                      queue_unfinished=sorted({p for p, _ in queue if p not in finished}),
                      files=[], missing_bodies=[], unexpected_bodies=[],
                      size_mismatches=[], blank_hit_hashes=0, hit_hash_mismatches=[])
        expected = set()
        for row in hits:
            route, declared_size = row[0], int(row[1])
            member = member_for(route)
            expected.add(member)
            if not row[-1]:
                result['blank_hit_hashes'] += 1
            if member not in names:
                result['missing_bodies'].append({'route': route, 'declared_size': declared_size})
                continue
            body = archive.read(member)
            text = body.decode('utf-8')
            js_units = len(text.encode('utf-16-le')) // 2
            digest = hashlib.sha256(body).hexdigest()
            item = {'route': route, 'member': member, 'bytes': len(body),
                    'utf16_units': js_units, 'sha256': digest,
                    'redacted_markers': text.count('REDACTED')}
            if baseline:
                old = Path(baseline) / ('f1-grab_' + route.lstrip('/').replace('/', '_')
                                          + ('.html' if route.endswith('.lp') else ''))
                item['baseline_present'] = old.is_file()
                if old.is_file():
                    previous = old.read_bytes()
                    item['baseline_equal'] = previous == body
                    item['baseline_sha256'] = hashlib.sha256(previous).hexdigest()
            result['files'].append(item)
            if declared_size != js_units:
                result['size_mismatches'].append(route)
            if row[-1] and not digest.startswith(row[-1]):
                result['hit_hash_mismatches'].append(route)
        result['unexpected_bodies'] = sorted(set(n for n in names if n.startswith('files/')) - expected)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--baseline-downloads', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive, args.baseline_downloads), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
