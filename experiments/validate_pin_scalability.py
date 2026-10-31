#!/usr/bin/env python3
"""Bounded performance checks, kept separate from the scientific campaign."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/analysis'))
from compare_reproduction import checked_histograms


def bounded(command, log, timeout, env=None):
    started = time.monotonic()
    with log.open('w') as output:
        child = subprocess.Popen(list(map(str, command)), stdout=output,
                                 stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            return dict(status='timeout', elapsed_s=time.monotonic()-started)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
    return dict(status='complete' if code == 0 else 'failed', returncode=code,
                elapsed_s=time.monotonic()-started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-tool', type=Path, required=True)
    parser.add_argument('--candidate-tool', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--scale', type=int, default=12)
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--threads', type=int, nargs='+', default=[1,2,4,8,20])
    args = parser.parse_args()
    if args.timeout <= 0: parser.error('timeout must be positive')
    if args.scale < 8 or args.scale > 16: parser.error('engineering graph scale must be 8 through 16')
    if args.repeats < 1 or any(t < 1 or t > 20 for t in args.threads):
        parser.error('positive repetitions and 1 through 20 threads required')
    args.out.mkdir(parents=True, exist_ok=False)
    pin = Path.home()/'dev/advarch/pin/pin'
    report = dict(status='running', scope='engineering validation, not M5 fidelity results',
                  baseline_sha256=hashlib.sha256(args.baseline_tool.read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256(args.candidate_tool.read_bytes()).hexdigest(),
                  scale=args.scale, repeats=args.repeats, threads=args.threads, timeout_s=args.timeout,
                  fixture=[], scaling=[], instruction_guard=False)

    def save():
        path = args.out/'validation.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(report, indent=2)+'\n')
        temp.replace(path)

    save()
    fixture = args.out/'ordered-fixture'
    subprocess.run(['gcc','-O1','-fno-tree-vectorize','-no-pie',
                    str(ROOT/'src/profiler/validate/ordered_fixture.c'),'-o',str(fixture)],check=True)
    configurations = [('baseline', args.baseline_tool, []),
                      ('candidate-legacy', args.candidate_tool, []),
                      ('local-bbl', args.candidate_tool, ['-local_bbl','1']),
                      ('mutex', args.candidate_tool, ['-sync_mode','mutex']),
                      ('mutex-local', args.candidate_tool, ['-sync_mode','mutex','-local_bbl','1']),
                      ('private-local', args.candidate_tool, ['-local_bbl','1','-private_parallel','1']),
                      ('mutex-private-local', args.candidate_tool, ['-sync_mode','mutex','-local_bbl','1','-private_parallel','1'])]
    for clock in ['traffic', 'references']:
        expected = None
        for name, tool, opts in configurations:
            prefix = args.out/f'{clock}-{name}'
            command = ['setarch',os.uname().machine,'-R',pin,'-t',tool,'-paired','1',
                       '-epoch','1' if clock=='traffic' else '0',
                       '-epoch_refs','1' if clock=='references' else '0',
                       '-dump_pages','0','-l1_kb','4','-l1_assoc','2',
                       '-l2_kb','16','-l2_assoc','4','-l3_kb','256','-l3_assoc','4',
                       '-roi_begin','hotskew_roi_begin','-roi_end','hotskew_roi_end',
                       '-o',prefix,*opts,'--',fixture]
            row = dict(case=name, clock=clock, command=list(map(str,command)))
            row.update(bounded(command, prefix.with_suffix('.run.log'), args.timeout))
            if row['status'] == 'complete':
                outputs = [prefix.with_suffix(s).read_bytes() for s in ['.epochs.csv','.paired.csv']]
                if expected is None: expected = outputs
                row['exact_match'] = outputs == expected
                row['output_sha256'] = [hashlib.sha256(x).hexdigest() for x in outputs]
            report['fixture'].append(row); save()
            if row['status'] != 'complete' or not row['exact_match']:
                report['status']='failed fixture equivalence'; save(); return 1
    guard = [pin,'-t',args.candidate_tool,'-local_bbl','1','-epoch_ins','1','--','/bin/true']
    guard_run = bounded(guard,args.out/'guard.run.log',args.timeout)
    report['instruction_guard_run'] = guard_run
    # This Pin version reports tool-main early returns as success; use the explicit
    # rejection diagnostic, emitted before PIN_StartProgram(), rather than its code.
    report['instruction_guard'] = (guard_run['status'] != 'timeout' and
        'local_bbl requires' in (args.out/'guard.run.log').read_text())
    save()
    if not report['instruction_guard']:
        report['status']='failed instruction guard'; save(); return 1
    graph = args.out/'tiny.sg'
    subprocess.run([ROOT/'workloads/gapbs/converter','-g',str(args.scale),'-s','-b',graph],
                   check=True,stdout=subprocess.DEVNULL)
    # Include two repetitions and preserve timeouts; no speedup threshold selects a CDF.
    for repeat in range(args.repeats):
        for threads in args.threads:
            for name,tool,opts in [configurations[i] for i in (0,2,4,5,6)]:
                directory=args.out/f'tc-{repeat}-{threads}-{name}'
                command=[sys.executable,ROOT/'experiments/run_paired.py','tc',
                         '--graph-prefix',graph.with_suffix(''),'--graph-family','scaling smoke test',
                         '--threads',str(threads),'--epoch-traffic','1','--out',directory,'--tool',tool]
                if opts:
                    command+=['--local-bbl']
                    if name.startswith('mutex-'):command+=['--sync-mode','mutex']
                    if 'private' in name:command+=['--private-parallel']
                row=dict(case=name,threads=threads,repeat=repeat)
                row.update(bounded(command,args.out/f'tc-{repeat}-{threads}-{name}.run.log',args.timeout))
                if row['status']=='complete':
                    try:
                        checked_histograms(directory,'tc')
                        row['audited']=True
                    except (ValueError,AssertionError,KeyError) as error:
                        row.update(status='audit failed',error=str(error))
                report['scaling'].append(row);save()
                print(json.dumps(row),flush=True)
    report['status']='passed' if all(r['status']=='complete' and r.get('audited') for r in report['scaling']) else 'scaling incomplete'
    report['deployment_approved']=False
    report['limitation']='Small-input scaling only; concurrent schedules are not identical traces. No large multithreaded control is authorized by this report alone.'
    save()
    return int(report['status']!='passed')


if __name__=='__main__':raise SystemExit(main())
