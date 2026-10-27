#!/usr/bin/env python3
"""Sequential, restartable revalidation lanes. Never overwrites historical results.

Run the pin and sim lanes in separate systemd user services. A completed job is
reused only with matching command and executable fingerprint. Failed attempts are
kept; a later invocation creates a new attempt directory for incomplete jobs.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revalidated-2026-10-25'
PY=ROOT/'.venv/bin/python'

class PausedRun(Exception):
    pass

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def atomic(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(p)

def run(cmd,log):
    if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('less than 4 GiB free; no new job started')
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as f:
        child=subprocess.Popen([str(x) for x in cmd],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
                               env=dict(os.environ,OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE'))
        try:
            while child.poll() is None:
                if shutil.disk_usage(ROOT).free<2*1024**3:raise RuntimeError('disk safety floor reached')
                time.sleep(2)
            if child.returncode==75:raise PausedRun('checkpoint saved; run paused')
            if child.returncode:raise RuntimeError(f'exit {child.returncode}: {log}')
        finally:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()

def publish():
    subprocess.run([str(PY),'src/analysis/publish_revalidation.py'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('lane',choices=['pin','sim'])
    ap.add_argument('--checkpoint-storage',type=Path)
    ap.add_argument('--checkpoint-validation',type=Path)
    a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/f'{a.lane}.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    statefile=OUT/f'{a.lane}-status.json'
    state=json.loads(statefile.read_text()) if statefile.exists() else {'jobs':{}}
    state['pid']=os.getpid();state['status']='running';state['started']=time.time()
    def save():state['updated']=time.time();atomic(statefile,state)
    def stop(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    tool=ROOT/'src/profiler/pintool/obj-intel64/hotskew.so'
    sim=ROOT.parent/'simcxl/build/X86/gem5.opt'
    fingerprint=sha(tool if a.lane=='pin' else sim)
    if a.checkpoint_storage:
        if a.lane!='sim' or not a.checkpoint_validation:ap.error('sim checkpoints require a full-system validation report')
        proof=json.loads(a.checkpoint_validation.read_text())
        if (proof.get('status')!='passed' or proof.get('scope')!='bounded full-system dd workload'
                or proof.get('gem5_sha256')!=fingerprint):
            raise RuntimeError('full-system restore validation is missing or incompatible')
    jobs=[]
    if a.lane=='pin':
        for algo in ['spacesaving','cmsketch']:
            for name in ['bfs','cc','bc','sssp','pr','tc']:
                directory=OUT/'pin'/algo
                cmd=[PY,'experiments/run_paired.py',name,'--epoch-traffic','10','--track-algo',algo,'--out',directory]
                if algo=='spacesaving':cmd += ['--dump-pages'] if name in ['bfs','cc'] else ['--gzip-pages']
                if name in ['bc','sssp']:cmd+=['--graph-prefix','workloads/gapbs/graphs/gplus-snapshot1','--graph-family','Google+ IMC12 snapshot 1']
                jobs.append((f'{algo}-{name}',cmd,directory/f'gapbs-{name}',algo=='spacesaving'))
        for name in ['redis-a','redis-c','memcached','liblinear']:
            jobs.append((name,None,None,True))
    else:
        for name in ['bfs','cc','bc','sssp','pr','tc','liblinear']:
            jobs.append((name,None,10_000_000,False))
        for epoch in [1_000_000,100_000_000]:jobs.append((f'bc-window-{epoch}',None,epoch,False))
    state['planned_jobs']=[j[0] for j in jobs];save()
    for job,cmd,prefix,analyse in jobs:
        old=state['jobs'].get(job,{})
        if old.get('status')=='complete' and old.get('binary_sha256')==fingerprint:continue
        status={'status':'running','started':time.time(),'binary_sha256':fingerprint}
        state['jobs'][job]=status;state['current']=job;save();publish()
        try:
            if a.lane=='sim' and a.checkpoint_storage and old.get('checkpoint_state'):
                checkpoint=Path(old['checkpoint_state'])
                if (checkpoint/'latest.json').exists():
                    directory=Path(old['output']);cmd=old['command']
                    status['checkpoint_state']=str(checkpoint)
                    for key in ['config_sha256','scope','graph','guest_script_sha256']:
                        if key in old:status[key]=old[key]
            if cmd is not None:
                if a.lane=='pin':directory=prefix.parent
                manifest_path=Path(str(prefix)+'.manifest.json')
                if a.lane=='pin' and manifest_path.exists():
                    prior=json.loads(manifest_path.read_text())
                    if prior.get('status')!='complete' or prior.get('tool_sha256')!=fingerprint:
                        attempt=1
                        while (OUT/a.lane/job/f'attempt-{attempt}').exists():attempt+=1
                        directory=OUT/a.lane/job/f'attempt-{attempt}'
                        cmd[cmd.index('--out')+1]=directory
                        prefix=directory/prefix.name
            if cmd is None:
                attempt=1
                while (OUT/a.lane/job/f'attempt-{attempt}').exists():attempt+=1
                directory=OUT/a.lane/job/f'attempt-{attempt}'
                if a.lane=='pin':
                    cmd=[PY,'experiments/run_extension_workload.py',job,'--out',directory]
                    prefix=directory/job
                else:
                    directory.mkdir(parents=True)
                    workload='bc' if job.startswith('bc-window-') else job
                    cmd=[sim,'-d',directory,ROOT/'src/sim/simcxl/fs_hotskew.py','--workload',workload,
                         '--big-mem','--switch-at-roi','--max-exits','3','--llc-ways','10','--epoch',str(prefix)]
                    status['config_sha256']=sha(ROOT/'src/sim/simcxl/fs_hotskew.py')
                    status['scope']='TimingSimpleCPU from ROI entry to ROI exit; atomic warm-up; independent per-port epochs'
                    status['graph']='kron-21' if job=='tc' else 'kdda (KDD2010)' if job=='liblinear' else 'kron-23'
                    status['guest_script_sha256']=sha(ROOT.parent/f'fs_image/datadisk/run_{workload}.sh')
            status['command']=[str(x) for x in cmd];status['output']=str(directory);save()
            log=OUT/'logs'/f'{a.lane}-{job}-{int(time.time())}.run.log'
            status['log']=str(log);save()
            launch=cmd
            if a.lane=='sim' and a.checkpoint_storage:
                checkpoint=Path(status.get('checkpoint_state',a.checkpoint_storage/job/directory.name))
                status['checkpoint_state']=str(checkpoint)
                launch=[PY,'experiments/checkpoint_sim.py','run','--state-dir',checkpoint]
                for file in ['vmlinux-5.4.49','x86-ubuntu.img','data2.img']:
                    launch+=['--guard-file',ROOT.parent/'fs_image'/file]
                launch+=['--',*cmd];save()
            run(launch,log)
            if a.lane=='pin':
                manifest=json.loads(Path(str(prefix)+'.manifest.json').read_text())
                if manifest.get('status')!='complete' or manifest['tool_sha256']!=fingerprint:
                    raise RuntimeError('incomplete or incompatible workload manifest')
                if analyse:
                    run([PY,'src/analysis/revalidate_extensions.py',prefix,'--out',OUT/'analysis'/f'{job}.json'],
                        OUT/'logs'/f'analysis-{job}.run.log')
                    status['analysis']=str(OUT/'analysis'/f'{job}.json')
                status['prefix']=str(prefix)
            else:
                text=log.read_text()
                if 'exit #3' not in text or '-- stopping, summary follows' not in text:
                    raise RuntimeError('simulator did not reach ROI end')
                sys.path.insert(0,str(ROOT/'src/analysis'))
                import hotskew as H
                summaries={}
                for file in directory.glob('hotskew-*'):
                    m=H.load_summary(str(file));hist=m['_unique_hist']
                    if int(m.get('page_observations','0').split()[0])!=int(hist.sum()):
                        raise RuntimeError('simulator histogram mismatch')
                    summaries[file.name]=dict(events=int(m['dram_accesses'].split()[0]),
                                              epochs=int(m['epochs'].split()[0]),pages=int(hist.sum()))
                if not summaries or not any(v['events'] for v in summaries.values()):raise RuntimeError('no measured memory traffic')
                status['summaries']=summaries
            status['status']='complete'
            print(f'COMPLETE {a.lane}/{job}',flush=True)
        except BaseException as e:
            if isinstance(e,PausedRun):
                status.update(status='paused',error=str(e));state['status']='paused';save();publish();return 75
            status.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e))
            print(f"{status['status'].upper()} {a.lane}/{job}: {e}",flush=True)
            if isinstance(e,KeyboardInterrupt):
                state['status']='interrupted';save();publish();return 130
        finally:
            status['elapsed_s']=time.time()-status['started'];save()
        publish()
    state['status']='complete' if all(v['status']=='complete' for v in state['jobs'].values()) else 'finished-with-failures'
    state['current']=None;save();publish()
    return 0 if state['status']=='complete' else 1

if __name__=='__main__':sys.exit(main())
