#!/usr/bin/env python3
"""Declared scope, thread, CAT and RSS controls; retain all results, never tune CDFs."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/fidelity-stage2-2026-10-28'
PY=ROOT/'.venv/bin/python'

def main():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'campaign.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=OUT/'campaign.json'
    state=json.loads(path.read_text()) if path.exists() else {'jobs':{}}
    def save():
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(path)
    def stop(sig,frame):raise KeyboardInterrupt(f'signal {sig}')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    state.update(status='waiting for declared repetition controls',pid=os.getpid());save()
    while True:
        prior=ROOT/'results/fidelity-2026-10-27/trials200-pool'
        manifests=[prior/f'gapbs-{n}.manifest.json' for n in ['bfs','cc']]
        statuses=[json.loads(p.read_text())['status'] if p.exists() else 'queued' for p in manifests]
        if statuses==['complete','complete']:break
        if any(s in ['failed','interrupted','limited'] for s in statuses):raise RuntimeError('repetition controls need attention')
        time.sleep(20)
    graphs=json.loads((ROOT/'results/fidelity-2026-10-27/inputs.json').read_text())['graphs']
    keys=dict(bfs='twitter-main',cc='twitter-main',bc='gplus-bc',sssp='gplus-sssp',pr='twitter-main',tc='twitter-tc')
    jobs=[]
    # Four shorter kernels first; expensive PR/TC controls remain in the same protocol.
    for names in [('bfs','cc','bc','sssp'),('pr','tc')]:
        for case,opts in [('process',['--scope','process']),('threads20',['--threads','20']),('ways9',['--llc-ways','9'])]:
            for name in names:jobs.append((case+'-'+name,name,opts,None))
        if len(names)==4:
            jobs.append(('prepare-tc-footprint',None,[],None))
            jobs.append(('footprint-tc','tc',[],True))
            jobs.append(('footprint20-tc','tc',['--threads','20'],True))
    for name,*_ in jobs:state['jobs'].setdefault(name,{'status':'queued'})
    state['status']='running';save()
    for key,name,opts,footprint in jobs:
        old=state['jobs'][key]
        if old['status']=='complete':continue
        state['current']=key
        while True:
            memory={line.split(':')[0]:int(line.split()[1])*1024
                    for line in Path('/proc/meminfo').read_text().splitlines()}
            if memory['MemAvailable']>=12*1024**3:break
            state['status']='waiting for 12 GiB available memory';save();time.sleep(60)
        state['status']='running'
        row={'status':'running','started':time.time()};state['jobs'][key]=row;save()
        if name is None:cmd=[PY,ROOT/'benchmarks/prepare_tc_footprint.py']
        else:
            base=OUT/key;attempt=1
            while (base/f'attempt-{attempt}').exists():attempt+=1
            directory=base/f'attempt-{attempt}';row['output']=str(directory)
            graph=(json.loads((OUT/'tc-footprint.json').read_text()) if footprint else graphs[keys[name]])
            cmd=[PY,ROOT/'experiments/run_paired.py',name,'--epoch-traffic','10','--out',directory,
                 '--graph-prefix',str(Path(graph['path']).with_suffix('')),
                 '--graph-family','Twitter RSS-selected induced reduction' if footprint else graph['family'],*opts]
        log=OUT/f'{key}-{int(time.time())}.run.log';row.update(command=list(map(str,cmd)),log=str(log));save()
        child=None
        try:
            with log.open('w') as output:
                child=subprocess.Popen(list(map(str,cmd)),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                if child.wait():raise RuntimeError(f'nonzero exit; inspect {log}')
            if name:
                manifest=json.loads((directory/f'gapbs-{name}.manifest.json').read_text())
                if manifest['status']!='complete':raise RuntimeError('incomplete instrumented run')
            row.update(status='complete',elapsed_s=time.time()-row['started']);save()
            subprocess.run([PY,ROOT/'src/analysis/publish_pin_stage2.py'],cwd=ROOT,check=True)
        except BaseException as e:
            if child and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            row.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e))
            state['status']=row['status'];save();raise
    state.update(status='complete',current=None);save()

if __name__=='__main__':main()
