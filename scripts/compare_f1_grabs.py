#!/usr/bin/env python3
"""Compare two F1 grab archives offline; output metadata, never body excerpts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from audit_f1_grab import audit, table_rows


def records(path):
    with zipfile.ZipFile(path) as z:
        hits = table_rows(z.read('INDEX.md').decode('utf-8'))
        misses = table_rows(z.read('MISSES.md').decode('utf-8'))
        result = {row[0]: '200' for row in hits}
        for row in misses:
            column = 2 if row[1].startswith('http') else 1
            if row[0] in result:
                raise ValueError('route appears in both hits and misses')
            result[row[0]] = row[column]
        queue = set(re.findall(r'^- `([^`]+)` — ',
                               z.read('INDEX.md').decode('utf-8'), re.M))
        return result, queue


def compare(old_path, new_path):
    # Reuse size/path/CRC validation before reading members for comparison.
    old_audit, new_audit = audit(old_path), audit(new_path)
    old_records, old_queue = records(old_path)
    new_records, new_queue = records(new_path)
    with zipfile.ZipFile(old_path) as old, zipfile.ZipFile(new_path) as new:
        old_names, new_names = set(old.namelist()), set(new.namelist())
        changes = []
        unchanged = []
        for name in sorted(old_names & new_names):
            before, after = old.read(name), new.read(name)
            if before == after:
                unchanged.append(name)
            else:
                changes.append({'member': name, 'old_bytes': len(before),
                                'new_bytes': len(after),
                                'old_sha256': hashlib.sha256(before).hexdigest(),
                                'new_sha256': hashlib.sha256(after).hexdigest()})
        transitions = []
        for route in sorted(old_records.keys() | new_records.keys()):
            before, after = old_records.get(route), new_records.get(route)
            if before != after:
                transitions.append({'route': route, 'old_status': before,
                                    'new_status': after,
                                    'queued_in_new': route in new_queue})
        summaries = {}
        for label, data in [('old', old_audit), ('new', new_audit)]:
            summaries[label] = {key: data[key] for key in
                                ['archive_sha256', 'zip_members', 'body_members',
                                 'hit_rows', 'miss_rows', 'miss_statuses',
                                 'queue_entries', 'queue_unique', 'blank_hit_hashes']}
            summaries[label]['queue_already_finished_count'] = len(data['queue_already_finished'])
        return {'summary': summaries, 'added_members': sorted(new_names - old_names),
                'removed_members': sorted(old_names - new_names),
                'changed_members': changes, 'unchanged_members': unchanged,
                'record_transitions': transitions,
                'new_completed_routes': sorted(new_records.keys() - old_records.keys()),
                'old_queue_count': len(old_queue), 'new_queue_count': len(new_queue)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old_archive', type=Path)
    parser.add_argument('new_archive', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.old_archive, args.new_archive), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
