#!/usr/bin/env python3
"""Run one simulator process with disk checkpoints and explicit pause/resume.

`pause --state-dir DIR` waits for a finalized checkpoint before stopping. Exit 75
from `run` means paused. Run the same command again to restore its last snapshot.
This process mechanism still requires workload-specific restore validation.
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
BIN=ROOT.parent/'dmtcp-local/bin'

def atomic(path,value):
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['run','pause','status'])
    ap.add_argument('--state-dir',type=Path,required=True)
    ap.add_argument('--interval',type=int,default=1800)
    ap.add_argument('--guard-file',type=Path,action='append',default=[])
    argv=sys.argv[1:]
    split=argv.index('--') if '--' in argv else len(argv)
    command=argv[split+1:]
    a=ap.parse_args(argv[:split]);d=a.state_dir.resolve();statefile=d/'state.json'
    if a.action=='status':print(statefile.read_text());return 0
    if a.action=='pause':
        state=json.loads(statefile.read_text())
        if state['status'] in ['paused','complete']:print(state['status']);return 0
        if state['boot_id']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():
            raise RuntimeError('process belongs to an earlier boot; resume from its last checkpoint instead')
        os.kill(state['pid'],0)
        (d/'pause.request').touch()
        deadline=time.monotonic()+1800
        while time.monotonic()<deadline:
            state=json.loads(statefile.read_text())
            if state['status'] in ['paused','complete']:print(state['status']);return 0
            if state['status']=='failed':raise RuntimeError(state.get('error','checkpoint failed'))
            time.sleep(1)
        raise TimeoutError('pause not confirmed; do not shut down on this result')
    if not command:ap.error('run requires -- followed by a simulator command')
    if a.interval<0:ap.error('interval must be nonnegative')
    d.mkdir(parents=True,exist_ok=True)
    lock=(d/'supervisor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fingerprint={str(Path(x).resolve()):sha(x) for x in [command[0],*a.guard_file]}
    for token in command[1:]:
        if token.endswith('.py') and Path(token).is_file():fingerprint[str(Path(token).resolve())]=sha(token)
    old=json.loads(statefile.read_text()) if statefile.exists() else None
    if old and (old['command']!=command or old['files']!=fingerprint):
        raise RuntimeError('command or guarded files changed; use a new state directory')
    if old and old['status']=='complete':print((d/'simulator.log').read_text());return 0
    latest=d/'latest.json';images=d/'images';images.mkdir(exist_ok=True)
    portfile=d/'port';portfile.unlink(missing_ok=True)
    (d/'pause.request').unlink(missing_ok=True)
    env=dict(os.environ,DMTCP_GZIP='1',DMTCP_SIGCKPT='35',OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE')
    if latest.exists():
        checkpoint=json.loads(latest.read_text());image=d/checkpoint['image']
        if sha(image)!=checkpoint['sha256']:raise RuntimeError('checkpoint hash mismatch')
        launch=[BIN/'dmtcp_restart','--new-coordinator','--coord-port','0','--port-file',portfile,'--ckptdir',images,image]
    else:
        if old:raise RuntimeError('interrupted attempt has no completed checkpoint; use a new directory')
        launch=[BIN/'dmtcp_launch','--new-coordinator','--coord-port','0','--port-file',portfile,'--ckptdir',images,*command]
    state=dict(status='starting',command=command,files=fingerprint,pid=os.getpid(),
               boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),started=time.time())
    atomic(statefile,state)
    stop=False
    def signal_stop(signum,frame):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,signal_stop);signal.signal(signal.SIGINT,signal_stop)
    child=None;port=None
    try:
        with (d/'simulator.log').open('a' if latest.exists() else 'w') as log:
            child=subprocess.Popen(list(map(str,launch)),stdout=log,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
            deadline=time.monotonic()+60
            while not portfile.exists():
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('checkpoint runtime did not start')
                time.sleep(.1)
            port=portfile.read_text().strip();state.update(status='running',port=port);atomic(statefile,state)
            last=time.monotonic()
            while child.poll() is None:
                pause=stop or (d/'pause.request').exists()
                if pause or (a.interval and time.monotonic()-last>=a.interval):
                    # Keep the previous finalized snapshot available during replacement.
                    if shutil.disk_usage(d).free < 25*1024**3:
                        raise RuntimeError('checkpoint needs at least 25 GiB free on its storage drive')
                    previous=d/'history'/str(time.time_ns());previous.mkdir(parents=True)
                    if latest.exists():
                        prior=json.loads(latest.read_text())
                        old_image=d/prior['image']
                        if old_image.parent==images:
                            shutil.move(str(old_image),previous/old_image.name)
                            prior['image']=str((previous/old_image.name).relative_to(d))
                            atomic(latest,prior)
                    for image in images.glob('*.dmtcp'):
                        shutil.move(str(image),previous/('unverified-'+image.name))
                    state['status']='checkpointing';atomic(statefile,state)
                    with (d/'checkpoint.log').open('a') as cklog:
                        subprocess.run([BIN/'dmtcp_command','-p',port,'--checkpoint'],stdout=cklog,stderr=cklog,check=True)
                        deadline=time.monotonic()+1500
                        while True:
                            files=list(images.glob('*.dmtcp'))
                            status=subprocess.run([BIN/'dmtcp_command','-p',port,'--status'],capture_output=True,text=True,check=True).stdout
                            if len(files)==1 and 'RUNNING=yes' in status:break
                            if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('checkpoint not finalized')
                            time.sleep(1)
                        image=files[0]
                        atomic(latest,dict(image=str(image.relative_to(d)),sha256=sha(image),
                                          bytes=image.stat().st_size,created=time.time()))
                        state['last_checkpoint']=time.time()
                        history=sorted((d/'history').iterdir())
                        for obsolete in history[:-2]:shutil.rmtree(obsolete)
                        if pause:
                            if child.poll()==0:
                                state['status']='complete';atomic(statefile,state)
                                print((d/'simulator.log').read_text());return 0
                            subprocess.run([BIN/'dmtcp_command','-p',port,'--kill'],stdout=cklog,stderr=cklog,check=True)
                            child.wait(timeout=60);state['status']='paused';atomic(statefile,state);return 75
                    last=time.monotonic();state['status']='running';atomic(statefile,state)
                time.sleep(1)
            if child.returncode:raise RuntimeError(f'simulator exit {child.returncode}')
        state['status']='complete';atomic(statefile,state)
        print((d/'simulator.log').read_text());return 0
    except BaseException as e:
        state.update(status='failed',error=str(e));atomic(statefile,state);raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=30)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        if port:subprocess.run([BIN/'dmtcp_command','-p',port,'--quit'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':raise SystemExit(main())
