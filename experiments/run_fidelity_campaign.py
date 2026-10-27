#!/usr/bin/env python3
"""Restartable, predeclared input/execution controls. Preserve failed attempts."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/fidelity-2026-10-27'
PY=ROOT/'.venv/bin/python'
STORAGE=Path('/mnt/research/memory-tiering')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'campaign.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=OUT/'campaign.json'
    state=json.loads(path.read_text()) if path.exists() else {'jobs':{}}
    tool=ROOT/'src/profiler/pintool/obj-intel64/hotskew.so'
    digest=hashlib.sha256(tool.read_bytes()).hexdigest()
    def publish():
        pending=path.with_suffix('.tmp');pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(path)
        subprocess.run([PY,'src/analysis/publish_fidelity.py'],cwd=ROOT,check=True)
    def stop(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def run(cmd,log):
        with log.open('w') as f:
            child=subprocess.Popen(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
                                   start_new_session=True)
            try:
                if child.wait():raise RuntimeError(f'job failed; inspect {log}')
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=30)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    jobs=[]
    for case,names,options in [
        ('threads20',['bfs','cc'],['--threads','20']),
        ('trials3-close',['bfs','cc'],['--trials','3']),
        ('trials3-pool',['bfs','cc'],['--trials','3','--roi-epoch','0']),
        ('setup-warmed',['bfs','cc'],['--warm-setup']),
        ('pr-artifact-convergence',['pr'],['--pr-iterations','1000','--pr-tolerance','0.0001'])]:
        for name in names:jobs.append((case+'-'+name,case,name,options,None))
    jobs.append(('prepare-inputs',None,None,None,None))
    for name,key in [('bfs','twitter-main'),('cc','twitter-main'),('pr','twitter-main'),('tc','twitter-tc'),
                     ('bc','gplus-bc'),('sssp','gplus-sssp')]:
        jobs.append(('dataset-'+name,'dataset',name,[],key))
    for job,*_ in jobs:state['jobs'].setdefault(job,{'status':'queued'})
    state.update(status='running',pid=os.getpid(),tool_sha256=digest);publish()
    # An earlier explicit control launch may still own the same output paths.
    while subprocess.run(['systemctl','--user','is-active','--quiet','memory-tiering-fidelity-controls']).returncode==0:
        time.sleep(5)
    for job,case,name,options,key in jobs:
        row=state['jobs'][job]
        if row.get('status')=='complete' and row.get('tool_sha256')==digest:continue
        row.update(status='running',started=time.time(),tool_sha256=digest);state['current']=job;publish()
        try:
            if job=='prepare-inputs':
                while subprocess.run(['systemctl','--user','is-active','--quiet','memory-tiering-twitter-download']).returncode==0:
                    time.sleep(5)
                cmd=[PY,'benchmarks/prepare_fidelity_inputs.py','--out',OUT/'inputs.json']
            else:
                directory=OUT/case
                manifest=directory/f'gapbs-{name}.manifest.json'
                if manifest.exists() and json.loads(manifest.read_text()).get('status')!='complete':
                    attempt=1
                    while (OUT/case/f'attempt-{attempt}').exists():attempt+=1
                    directory=OUT/case/f'attempt-{attempt}'
                cmd=[PY,'experiments/run_paired.py',name,'--epoch-traffic','10','--out',directory,*options]
                if key:
                    graph=json.loads((OUT/'inputs.json').read_text())['graphs'][key]
                    cmd+=['--graph-prefix',str(Path(graph['path']).with_suffix('')),'--graph-family',graph['family']]
                row['output']=str(directory)
            row['command']=list(map(str,cmd));publish()
            log=OUT/f'{job}-{int(time.time())}.run.log';row['log']=str(log)
            run(cmd,log)
            if name:
                meta=json.loads((directory/f'gapbs-{name}.manifest.json').read_text())
                if meta['status']!='complete':raise RuntimeError('benchmark is incomplete')
            row['status']='complete';row['elapsed_s']=time.time()-row['started'];publish()
        except BaseException as e:
            row.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e))
            state['status']=row['status'];publish();raise
    state.update(status='complete',current=None);publish()

if __name__=='__main__':main()
