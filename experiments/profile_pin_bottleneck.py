#!/usr/bin/env python3
"""Fixed-input, bounded CPU attribution; not fidelity collection or a speedup test."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from validate_pin_real_input import BASELINE, CANDIDATE, checked_histograms, triangles

ROOT = Path(__file__).resolve().parents[1]
STORAGE = Path('/mnt/research/memory-tiering')
GRAPH_SHA = '76c74f519c81ca04c22bdc41ae30a9c5cad0d55b257f1cc60d395c9154151e41'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def category(dso, symbol):
    name = symbol.lower()
    if any(term in name for term in ('spindelay', 'spinlock', 'getlock', 'releaselock',
                                     'mutexlock', 'mutexunlock', 'sync_lock', 'sync_unlock')):
        return 'synchronization symbols'
    if 'analyzememref' in name:
        return 'memory callback (includes inlined work)'
    if 'countbbl' in name:
        return 'instruction callback'
    if 'finishepoch' in name or 'pairedobserver' in name or 'counters' in name:
        return 'observer/epoch symbols'
    if dso == '[unknown]' or symbol.startswith('[.] 0x') or symbol.startswith('0x'):
        return 'unresolved/JIT'
    if 'hotskew.so' in dso:
        return 'other tool-linked code'
    return 'other runtime/application code'


def parse_report(text):
    rows = []
    for fields in csv.reader(io.StringIO(text), delimiter=';'):
        if len(fields) != 5 or fields[0].lstrip().startswith('#'):
            continue
        try:
            overhead = float(fields[0].strip().rstrip('%'))
            period, samples = int(fields[1].strip()), int(fields[2].strip())
        except ValueError:
            continue
        dso, symbol = fields[3].strip(), fields[4].strip()
        rows.append(dict(overhead_percent=overhead, period=period, samples=samples,
                         dso=dso, symbol=symbol, category=category(dso, symbol)))
    if not rows or sum(r['period'] for r in rows) <= 0:
        raise ValueError('No usable perf report samples')
    total = sum(r['period'] for r in rows)
    groups = {}
    for row in rows:
        groups[row['category']] = groups.get(row['category'], 0) + row['period']
    return dict(total_period=total, total_samples=sum(r['samples'] for r in rows),
                category_percent={k:100*v/total for k,v in groups.items()},
                top_symbols=sorted(rows, key=lambda r:r['period'], reverse=True)[:25])


def group_usage(pgid):
    rss = ticks = 0
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            stat = (entry/'stat').read_text()
            fields = stat[stat.rfind(')')+2:].split()
            if int(fields[2]) == pgid:
                rss += int(fields[21])*os.sysconf('SC_PAGE_SIZE')
                ticks += int(fields[11])+int(fields[12])
        except (OSError, ValueError, IndexError): pass
    return rss, ticks/os.sysconf('SC_CLK_TCK')


def signal_group(pgid, sig):
    try: os.killpg(pgid, sig)
    except ProcessLookupError: pass


def capture(command, log, seconds=40):
    started = time.monotonic()
    peak = cpu = 0
    with log.open('w') as output:
        child = subprocess.Popen(list(map(str,command)), stdout=output,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while child.poll() is None and time.monotonic()-started < seconds:
                rss, used = group_usage(child.pid)
                peak, cpu = max(peak,rss), max(cpu,used)
                try: child.wait(timeout=min(0.5, max(0.01,seconds-(time.monotonic()-started))))
                except subprocess.TimeoutExpired: pass
            cutoff = child.poll() is None
            if cutoff:
                signal_group(child.pid, signal.SIGTERM)
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    signal_group(child.pid, signal.SIGKILL); child.wait()
                # perf can exit before its instrumented child finishes shutdown.
                signal_group(child.pid, signal.SIGKILL)
        finally:
            if child.poll() is None:
                signal_group(child.pid, signal.SIGKILL); child.wait()
            signal_group(child.pid, signal.SIGKILL)
    return dict(profile_cutoff=cutoff, returncode=child.returncode,
                elapsed_s=time.monotonic()-started, sampled_peak_group_rss_bytes=peak,
                sampled_peak_group_cpu_seconds=cpu,
                accounting_limit='Sampled process-group sums include perf/wrapper; RSS may double-count shared pages; CPU can undercount exited tasks.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    graph=STORAGE/'profiler-validation/2026-11-01-real-input-attempt-1/twitter-nested-hash8.sg'
    tool_paths={name:STORAGE/f'profiler-builds/{digest}/hotskew.so'
                for name,digest in [('baseline',BASELINE),('local-bbl',CANDIDATE)]}
    report=dict(status='running',purpose=__doc__,deployment_approved=False,profile_seconds=40,
                graph=str(graph),graph_sha256=sha(graph),script_sha256=sha(Path(__file__)),
                runner_sha256=sha(ROOT/'experiments/run_paired.py'),
                binary_sha256=sha(ROOT/'workloads/gapbs/tc'),
                tool_sha256={k:sha(v) for k,v in tool_paths.items()},
                perf_version=subprocess.check_output(['perf','--version'],text=True).strip(),
                kernel=os.uname().release,cpu_affinity=sorted(os.sched_getaffinity(0)),profiles=[])
    def save():
        path=args.out/'study.json'; temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(path)
    def stop(sig,frame):raise KeyboardInterrupt(f'signal {sig}')
    signal.signal(signal.SIGTERM,stop)
    save()
    try:
        if report['graph_sha256']!=GRAPH_SHA or report['tool_sha256']!={'baseline':BASELINE,'local-bbl':CANDIDATE}:
            raise ValueError('Frozen graph/tool changed')
        for index,(threads,name) in enumerate([(1,'baseline'),(1,'local-bbl'),
                                             (20,'baseline'),(20,'local-bbl'),
                                             (20,'local-bbl'),(20,'baseline')]):
            directory=args.out/f'case-{index}-{threads}-{name}'
            data=args.out/f'case-{index}.perf.data'
            command=[sys.executable,ROOT/'experiments/run_paired.py','tc','--graph-prefix',graph.with_suffix(''),
                     '--graph-family','Bottleneck attribution only; fixed existing Twitter subset',
                     '--threads',str(threads),'--epoch-traffic','1','--application-stats',
                     '--tool',tool_paths[name],'--out',directory]
            if name=='local-bbl':command+=['--local-bbl']
            profile=['perf','record','-e','cpu-clock:u','-F','99','--call-graph','fp',
                     '-o',data,'--',*command]
            row=dict(case=name,threads=threads,command=list(map(str,profile)),status='sampling')
            report['profiles'].append(row);save()
            row.update(capture(profile,args.out/f'case-{index}.record.log'))
            manifest=directory/'gapbs-tc.manifest.json'
            if row['profile_cutoff']:
                if manifest.exists():
                    meta=json.loads(manifest.read_text());meta.update(status='interrupted',
                        interruption_reason='Predeclared 40-second diagnostic sampling cutoff; not completed fidelity data')
                    manifest.write_text(json.dumps(meta,indent=2)+'\n')
                row['collection_status']='bounded prefix, not a completed application'
            elif row['returncode']==0:
                checked_histograms(directory,'tc')
                if triangles(directory/'gapbs-tc.run.log')!=957682:raise ValueError('Native answer mismatch')
                row['collection_status']='complete and audited, engineering only'
            else:raise ValueError(f'perf/target failure, case {index}')
            with (args.out/f'case-{index}.symbols.csv').open('w') as output, (args.out/f'case-{index}.report.log').open('w') as errors:
                subprocess.run(['perf','report','--stdio','--stdio-color','never','--no-children','-g','none',
                                '--percent-limit','0','-t',';','-F','overhead,period,sample,dso,symbol',
                                '-i',str(data)],stdout=output,stderr=errors,check=True,timeout=30)
            row['attribution']=parse_report((args.out/f'case-{index}.symbols.csv').read_text())
            row['status']='profile complete';save()
            print(json.dumps({k:row[k] for k in ('case','threads','status','collection_status','attribution')}),flush=True)
        if all('complete and audited'==r['collection_status'].split(',')[0] for r in report['profiles'][:2]):
            report['one_thread_exact_outputs']=all(
                (args.out/'case-0-1-baseline'/f'gapbs-tc{s}').read_bytes()==
                (args.out/'case-1-1-local-bbl'/f'gapbs-tc{s}').read_bytes()
                for s in ('.epochs.csv','.paired.csv'))
        report['status']='completed attribution study'
        report['limitations']=['User CPU samples, not wall-wait fractions or lock latency.',
            'Unknown/JIT symbols retained; frame-pointer stacks may be incomplete.',
            'Short fixed prefixes contain different completed work; not a speedup measurement.',
            'External sampling perturbs timing; concurrent simulator continues unchanged.',
            'No input/settings selected against M5; no redesign or large deployment approved.']
        save()
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error));save();raise


if __name__=='__main__':main()
