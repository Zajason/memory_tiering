#!/usr/bin/env python3
"""Kill/restore a synthetic SimCXL process and compare with a native run.

This is a feasibility test, not full-system checkpoint certification. Each test
gets a new directory; incomplete or failed results are retained for inspection.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--dmtcp', type=Path, default=ROOT.parent/'dmtcp-local/bin')
    ap.add_argument('--duration-ticks', type=int, default=50000000000)
    ap.add_argument('--with-cache', action='store_true')
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    ckpt = out/'checkpoint'; ckpt.mkdir()
    portfile = out/'port'
    sim = ROOT.parent/'simcxl/build/X86/gem5.opt'
    config = ROOT/'src/sim/simcxl/cxl_hotskew_test.py'
    report = {'status': 'running', 'scope': 'synthetic CXL traffic, not full-system',
              'gem5_sha256': hashlib.file_digest(sim.open('rb'), 'sha256').hexdigest(),
              'duration_ticks': args.duration_ticks, 'with_cache': args.with_cache}
    def save(): (out/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    def command(name):
        return [str(sim), '-d', str(out/name), str(config),
                '--duration-ticks', str(args.duration_ticks), '--epoch-events', '100000',
                *(['--with-cache', '--read-percent', '50'] if args.with_cache else [])]
    process = None
    port = None
    save()
    try:
        with (out/'resumed.log').open('w') as log:
            process = subprocess.Popen([str(args.dmtcp/'dmtcp_launch'), '--new-coordinator',
                '--coord-port', '0', '--port-file', str(portfile), '--ckptdir', str(ckpt),
                *command('resumed')], stdout=log, stderr=subprocess.STDOUT, cwd=ROOT,
                env=dict(os.environ, DMTCP_GZIP='1', DMTCP_SIGCKPT='35'))
            deadline = time.monotonic()+30
            while not portfile.exists():
                if process.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError('DMTCP launch failed; inspect resumed.log')
                time.sleep(.1)
            port = portfile.read_text().strip()
            time.sleep(2)
            if process.poll() is not None: raise RuntimeError('simulation exited before checkpoint')
            with (out/'checkpoint.log').open('w') as cklog:
                subprocess.run([str(args.dmtcp/'dmtcp_command'), '-p', port, '--checkpoint'],
                               stdout=cklog, stderr=subprocess.STDOUT, check=True, timeout=180)
                deadline = time.monotonic()+180
                while True:
                    status = subprocess.run([str(args.dmtcp/'dmtcp_command'), '-p', port, '--status'],
                                            capture_output=True, text=True, check=True).stdout
                    if list(ckpt.glob('*.dmtcp')) and 'RUNNING=yes' in status: break
                    if process.poll() is not None or time.monotonic()>deadline:
                        raise RuntimeError('checkpoint did not finish; inspect DMTCP logs')
                    time.sleep(.2)
                subprocess.run([str(args.dmtcp/'dmtcp_command'), '-p', port, '--kill'],
                               stdout=cklog, stderr=subprocess.STDOUT, check=True, timeout=30)
            process.wait(timeout=30)
        images = sorted(ckpt.glob('*.dmtcp'))
        if not images: raise RuntimeError('no checkpoint images produced')
        report['checkpoint_bytes'] = sum(p.stat().st_size for p in images)
        report['original_process_exited'] = True
        save()
        with (out/'restore.log').open('w') as log:
            process = subprocess.Popen([str(args.dmtcp/'dmtcp_restart'), '--new-coordinator',
                '--coord-port', '0', *map(str,images)], stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
            if process.wait(timeout=300): raise RuntimeError('restore failed; inspect restore.log')
        with (out/'native.log').open('w') as log:
            subprocess.run(command('native'), stdout=log, stderr=subprocess.STDOUT,
                           cwd=ROOT, check=True, timeout=300)
        for name in ['hotskew','hotskew-controller']:
            native=(out/'native'/name).read_bytes()
            resumed=(out/'resumed'/name).read_bytes()
            if native != resumed: raise RuntimeError(f'restored/native mismatch: {name}')
        ticks = []
        for name in ['native.log','restore.log']:
            found = re.search(r'drained @ tick (\d+)', (out/name).read_text())
            if not found: raise RuntimeError(f'missing completion tick in {name}')
            ticks.append(int(found.group(1)))
        if ticks[0] != ticks[1]: raise RuntimeError('restored/native completion tick mismatch')
        report['completion_tick'] = ticks[0]
        report['status']='passed'
        report['comparison']='both complete probe summaries byte-identical, including tracker scores'
        print('PASS: checkpoint, process death, restore, native comparison', flush=True)
    except BaseException as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        if port:
            subprocess.run([str(args.dmtcp/'dmtcp_command'), '-p', port, '--quit'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        save()

if __name__ == '__main__': main()
