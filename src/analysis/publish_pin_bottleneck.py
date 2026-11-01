#!/usr/bin/env python3
"""Audit and publish finished CPU attribution, without rerunning target programs."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'experiments'))
from profile_pin_bottleneck import GRAPH_SHA, parse_report, sha
from validate_pin_real_input import BASELINE, CANDIDATE, checked_histograms, triangles


def derive(source):
    capture = source/'study.json'
    report = json.loads(capture.read_text())
    if (report['status'] != 'completed attribution study'
            or report['deployment_approved'] is not False
            or report.get('one_thread_exact_outputs') is not True
            or report['graph_sha256'] != GRAPH_SHA
            or report['tool_sha256'] != {'baseline':BASELINE, 'local-bbl':CANDIDATE}):
        raise ValueError('Not a completed frozen-input engineering study')
    expected = [(1,'baseline'), (1,'local-bbl'), (20,'baseline'),
                (20,'local-bbl'), (20,'local-bbl'), (20,'baseline')]
    if [(r['threads'],r['case']) for r in report['profiles']] != expected:
        raise ValueError('Case order/count differs from fixed protocol')
    for index, row in enumerate(report['profiles']):
        if row['status'] != 'profile complete':
            raise ValueError('Partial profile')
        directory = source/f"case-{index}-{row['threads']}-{row['case']}"
        if index < 2:
            if row['profile_cutoff'] or row['returncode'] != 0:
                raise ValueError('One-thread target did not finish')
            checked_histograms(directory, 'tc')
            if triangles(directory/'gapbs-tc.run.log') != 957682:
                raise ValueError('Native answer mismatch')
        else:
            manifest = json.loads((directory/'gapbs-tc.manifest.json').read_text())
            if not row['profile_cutoff'] or manifest['status'] != 'interrupted':
                raise ValueError('Bounded prefix must remain interrupted')
        symbols = source/f'case-{index}.symbols.csv'
        raw = symbols.read_text()
        lost = re.findall(r'^# Total Lost Samples: (\d+)\s*$', raw, re.MULTILINE)
        if len(lost) != 1:
            raise ValueError('Missing/unrecognized sample-loss metadata')
        row['reported_lost_samples'] = int(lost[0])
        row['symbols_sha256'] = sha(symbols)
        row['attribution'] = parse_report(raw)
        total = row['attribution']['total_period']
        row['lock_internal_percent'] = sum(
            r['period'] for r in row['attribution']['top_symbols']
            if r['symbol'] == '[.] LockInternal')*100/total
    for suffix in ('.paired.csv', '.epochs.csv'):
        first = source/'case-0-1-baseline'/f'gapbs-tc{suffix}'
        second = source/'case-1-1-local-bbl'/f'gapbs-tc{suffix}'
        if first.read_bytes() != second.read_bytes():
            raise ValueError('One-thread outputs differ')
    report['analysis'] = dict(
        capture_path=str(capture), capture_sha256=sha(capture),
        publisher_sha256=sha(Path(__file__)),
        classifier_sha256=sha(ROOT/'experiments/profile_pin_bottleneck.py'),
        classification_version=2,
        correction='Internal lock/unlock functions classified as synchronization after symbol/disassembly inspection. Original capture is unchanged; no target rerun.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path,
                        default=ROOT/'results/pin-bottleneck-2026-11-01/study.json')
    args = parser.parse_args()
    report = derive(args.source)
    report['analysis']['evidence_sha256'] = {
        path.name: sha(path) for path in args.out.parent.glob('*.txt')}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    for row in report['profiles']:
        groups = row['attribution']['category_percent']
        print(f"{row['threads']:2} {row['case']:9} LockInternal={row['lock_internal_percent']:.2f}% "
              f"sync={groups['synchronization symbols']:.2f}% "
              f"memory={groups['memory callback (includes inlined work)']:.2f}% "
              f"unknown={groups['unresolved/JIT']:.2f}%")


if __name__ == '__main__':
    main()
