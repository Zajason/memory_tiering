#!/usr/bin/env python3
"""Bounded real-input engineering pilot; never a fidelity result or deployment approval."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import time

import numpy as np

from validate_pin_scalability import bounded

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/analysis'))
from compare_reproduction import checked_histograms

BASELINE = 'a7276ee255ea5e74179fd22fff41ad4d7052520ea626339717b67032514a706a'
CANDIDATE = '6a24fae0dd3fbd7a61d9b0db1dc65e8bf8764bac65780aa85c46268d9eaf3941'
SOURCE = '085d5efd0ebf4556d0a10d133017246bf0db4f0875063e92e28bb35efaa16f5a'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selected_nodes(nodes, denominator):
    # Same integer mixer as prepare_twitter.cpp, applied to this CSR's vertex IDs.
    with np.errstate(over='ignore'):
        value = np.arange(nodes, dtype=np.uint64) + np.uint64(0x9e3779b97f4a7c15)
        value = (value ^ (value >> 30)) * np.uint64(0xbf58476d1ce4e5b9)
        value = (value ^ (value >> 27)) * np.uint64(0x94d049bb133111eb)
        value ^= value >> 31
    return np.flatnonzero(value % denominator == 0)


def induce(source, target, denominator=8):
    with source.open('rb') as stream:
        directed, edges, nodes = struct.unpack('<?qq', stream.read(17))
    if directed or nodes <= 0 or edges < 0:
        raise ValueError('Expected nonempty undirected unweighted CSR')
    if source.stat().st_size != 17 + (nodes+1)*8 + edges*4:
        raise ValueError('CSR size mismatch')
    offsets = np.memmap(source, dtype='<i8', mode='r', offset=17, shape=(nodes+1,))
    neighbors = np.memmap(source, dtype='<i4', mode='r', offset=17+(nodes+1)*8, shape=(edges,))
    if offsets[0] != 0 or offsets[-1] != edges or np.any(np.diff(offsets) < 0):
        raise ValueError('Invalid CSR offsets')
    chosen = selected_nodes(nodes, denominator)
    if not len(chosen):
        raise ValueError('Empty selection')
    mapping = np.full(nodes, -1, dtype=np.int32)
    mapping[chosen] = np.arange(len(chosen), dtype=np.int32)
    new_offsets = np.zeros(len(chosen)+1, dtype='<i8')
    with target.open('xb') as output:
        output.seek(17+(len(chosen)+1)*8)
        for index, vertex in enumerate(chosen):
            row = neighbors[offsets[vertex]:offsets[vertex+1]]
            if len(row) and (row.min() < 0 or row.max() >= nodes):
                raise ValueError('Invalid neighbor ID')
            remapped = mapping[row]
            retained = remapped[remapped >= 0]
            if np.any(np.diff(retained) <= 0) or np.any(retained == index):
                raise ValueError('Expected sorted unique loop-free source rows')
            output.write(retained.astype('<i4', copy=False).tobytes())
            new_offsets[index+1] = new_offsets[index] + len(retained)
        output.seek(0)
        output.write(struct.pack('<?qq', False, int(new_offsets[-1]), len(chosen)))
        output.write(new_offsets.tobytes())
    return dict(nodes=len(chosen), directed_entries=int(new_offsets[-1]),
                bytes=target.stat().st_size, sha256=sha(target),
                selection=f'SplitMix64(source CSR vertex ID)%{denominator} == 0; induced; ascending relabel',
                limitation='Nested subset of hash25, not original-ID selection or the full held input')


def triangles(log):
    matches = re.findall(r'^(\d+) triangles\s*$', log.read_text(), re.MULTILINE)
    if len(matches) != 1:
        raise ValueError('Missing unique completed triangle count')
    return int(matches[0])


def measured(command, log, timeout, env=None):
    started = time.monotonic()
    peak = 0
    with log.open('w') as output:
        child = subprocess.Popen(list(map(str, command)), stdout=output,
                                 stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            while child.poll() is None and time.monotonic()-started < timeout:
                rss = 0
                for entry in Path('/proc').iterdir():
                    if not entry.name.isdigit(): continue
                    try:
                        stat = (entry/'stat').read_text()
                        fields = stat[stat.rfind(')')+2:].split()
                        if int(fields[2]) == child.pid:
                            rss += int(fields[21])*os.sysconf('SC_PAGE_SIZE')
                    except (OSError, ValueError, IndexError):
                        continue
                peak = max(peak, rss)
                try: child.wait(timeout=min(1, max(0.01, timeout-(time.monotonic()-started))))
                except subprocess.TimeoutExpired: pass
            timed_out = child.poll() is None
            if timed_out:
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL); child.wait()
    return dict(status='timeout' if timed_out else 'complete' if child.returncode == 0 else 'failed',
                returncode=child.returncode, elapsed_s=time.monotonic()-started,
                sampled_peak_process_group_rss_bytes=peak,
                rss_method='sum of RSS for process group, sampled once/second; shared pages may double count')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    storage = Path('/mnt/research/memory-tiering')
    source = storage/'datasets/fidelity-v1/attempt-1/twitter-hash25.sg'
    tools = {name: storage/f'profiler-builds/{digest}/hotskew.so'
             for name, digest in [('baseline', BASELINE), ('local-bbl', CANDIDATE)]}
    report = dict(status='preparing', deployment_approved=False, timeout_s=600,
                  purpose=__doc__, source=str(source), source_sha256=sha(source),
                  script_sha256=sha(Path(__file__)), runner_sha256=sha(ROOT/'experiments/run_paired.py'),
                  executable_sha256=sha(ROOT/'workloads/gapbs/tc'),
                  tool_sha256={name: sha(path) for name, path in tools.items()}, runs=[])

    def save():
        path = args.out/'validation.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(report, indent=2)+'\n')
        temp.replace(path)

    def stop(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')

    signal.signal(signal.SIGTERM, stop)
    save()
    try:
        if report['source_sha256'] != SOURCE or report['tool_sha256'] != {'baseline':BASELINE, 'local-bbl':CANDIDATE}:
            raise ValueError('Frozen source/tool hash mismatch')
        prerequisite = ROOT/'results/pin-scalability-2026-10-31/attempt-6.json'
        gate = json.loads(prerequisite.read_text())
        if (gate['status'] != 'passed' or gate['candidate_sha256'] != CANDIDATE
                or gate['baseline_sha256'] != BASELINE or not gate['instruction_guard']
                or len(gate['fixture']) != 14 or not all(r.get('exact_match') for r in gate['fixture'])
                or len(gate['scaling']) != 50 or not all(r.get('audited') for r in gate['scaling'])):
            raise ValueError('Required completed correctness/scaling gate missing')
        report['prerequisite_report_sha256'] = sha(prerequisite); save()
        graph = args.out/'twitter-nested-hash8.sg'
        report['graph'] = induce(source, graph)
        report['status'] = 'running'; save()
        expected = None
        for threads in (1, 20):
            log = args.out/f'native-{threads}.log'
            env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_DYNAMIC='FALSE')
            result = bounded([ROOT/'workloads/gapbs/tc', '-f', graph, '-n', '1', '-a'], log, 120, env)
            if result['status'] != 'complete':
                report[f'native_{threads}'] = result
                raise ValueError('Native pilot failed or timed out')
            count = triangles(log)
            if expected is not None and count != expected:
                raise ValueError('Native thread counts disagree')
            expected = count
            report[f'native_{threads}'] = dict(**result, triangles=count); save()
        for index, (threads, name) in enumerate([(1,'baseline'),(1,'local-bbl'),
                                               (20,'baseline'),(20,'local-bbl'),
                                               (20,'local-bbl'),(20,'baseline')]):
            directory = args.out/f'case-{index}-{threads}-{name}'
            log = args.out/f'case-{index}.log'
            command = [sys.executable, ROOT/'experiments/run_paired.py', 'tc',
                       '--graph-prefix', graph.with_suffix(''), '--graph-family',
                       'Engineering-only nested Twitter induced subset', '--threads', str(threads),
                       '--epoch-traffic', '1', '--application-stats', '--tool', tools[name], '--out', directory]
            if name == 'local-bbl': command += ['--local-bbl']
            row = dict(case=name, threads=threads, command=list(map(str, command)))
            report['runs'].append(row); save()
            row.update(measured(command, log, 600))
            manifest = directory/'gapbs-tc.manifest.json'
            if row['status'] == 'timeout' and manifest.exists():
                meta = json.loads(manifest.read_text())
                meta.update(status='interrupted', interruption_reason='Engineering pilot 600-second deadline')
                manifest.write_text(json.dumps(meta, indent=2)+'\n')
            if row['status'] == 'complete':
                checked_histograms(directory, 'tc')
                row['audited'] = True
                row['triangles'] = triangles(directory/'gapbs-tc.run.log')
                if row['triangles'] != expected:
                    raise ValueError('Instrumented application result differs from native')
            epochs = directory/'gapbs-tc.epochs.csv'
            if epochs.exists():
                with epochs.open() as stream:
                    rows = list(csv.DictReader(stream))
                row['full_event_windows'] = sum(int(r['accesses']) >= 1000000 for r in rows)
            save(); print(json.dumps(row), flush=True)
        left = args.out/'case-0-1-baseline/gapbs-tc'
        right = args.out/'case-1-1-local-bbl/gapbs-tc'
        if all(r.get('audited') for r in report['runs'][:2]):
            report['one_thread_exact_outputs'] = all(
                left.with_suffix(suffix).read_bytes() == right.with_suffix(suffix).read_bytes()
                for suffix in ('.epochs.csv', '.paired.csv'))
        report['status'] = ('passed bounded proxy' if all(r.get('audited') for r in report['runs'])
                            and report.get('one_thread_exact_outputs') else 'pilot not passed')
        report['limitation'] = 'Reduced real-input proxy, not the full held input. No M5 scores or automatic deployment approval.'
        save()
        return int(report['status'] != 'passed bounded proxy')
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error))
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
