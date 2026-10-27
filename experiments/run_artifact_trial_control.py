#!/usr/bin/env python3
"""Isolate the artifact's 200-trial BFS/CC scope after the input campaign."""
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/fidelity-2026-10-27'

def main():
    while True:
        path=OUT/'campaign.json'
        state=json.loads(path.read_text()) if path.exists() else {}
        if state.get('status')=='complete':break
        if state.get('status') in ['failed','interrupted']:
            raise RuntimeError('main fidelity campaign needs attention before the trial control')
        time.sleep(10)
    directory=OUT/'trials200-pool'
    cmd=[ROOT/'.venv/bin/python','experiments/run_paired.py','bfs','cc',
         '--trials','200','--roi-epoch','0','--epoch-traffic','10','--out',directory]
    result=subprocess.run(list(map(str,cmd)),cwd=ROOT)
    subprocess.run([ROOT/'.venv/bin/python','src/analysis/publish_fidelity.py'],cwd=ROOT,check=True)
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
