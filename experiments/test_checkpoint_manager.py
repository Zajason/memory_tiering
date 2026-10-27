#!/usr/bin/env python3
"""Exercise the public pause/resume interface twice and compare native output."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PY=ROOT/'.venv/bin/python'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    state=out/'state';sim=ROOT.parent/'simcxl/build/X86/gem5.opt'
    def cmd(target):return [sim,'-d',target,ROOT/'src/sim/simcxl/cxl_hotskew_test.py',
                           '--duration-ticks','50000000000','--epoch-events','100000','--with-cache','--read-percent','50']
    launch=[PY,ROOT/'experiments/checkpoint_sim.py','run','--state-dir',state,'--interval','0','--',*cmd(out/'resumed')]
    child=None
    try:
        with (out/'manager.log').open('w') as log:
            for _ in range(2):
                child=subprocess.Popen(list(map(str,launch)),stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
                deadline=time.monotonic()+120
                while True:
                    data=json.loads((state/'state.json').read_text()) if (state/'state.json').exists() else {}
                    if data.get('pid')==child.pid and data.get('status')=='running':break
                    if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('supervisor did not start')
                    time.sleep(.1)
                time.sleep(2)
                subprocess.run([PY,ROOT/'experiments/checkpoint_sim.py','pause','--state-dir',state],check=True,timeout=180)
                if child.wait(timeout=30)!=75:raise RuntimeError('expected explicit paused status')
                if json.loads((state/'state.json').read_text())['status']!='paused':raise RuntimeError('pause not persisted')
            child=subprocess.Popen(list(map(str,launch)),stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
            if child.wait(timeout=300):raise RuntimeError('restore did not complete')
        with (out/'native.log').open('w') as log:subprocess.run(cmd(out/'native'),stdout=log,stderr=log,check=True,timeout=300)
        for name in ['hotskew','hotskew-controller']:
            if (out/'native'/name).read_bytes()!=(out/'resumed'/name).read_bytes():raise RuntimeError('summary mismatch')
        pattern=r'drained @ tick (\d+)'
        native=re.search(pattern,(out/'native.log').read_text()).group(1)
        resumed=re.search(pattern,(state/'simulator.log').read_text()).group(1)
        if native!=resumed:raise RuntimeError('completion tick mismatch')
        (out/'validation.json').write_text(json.dumps(dict(status='passed',scope='cached synthetic process supervisor',
            pause_restore_cycles=2,completion_tick=int(native),summary_comparison='byte-identical'),indent=2)+'\n')
        print('PASS: two managed pause/restore cycles, exact native summaries and completion tick')
    finally:
        if child is not None and child.poll() is None:child.terminate();child.wait(timeout=30)

if __name__=='__main__':main()
