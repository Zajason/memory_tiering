#!/usr/bin/env python3
"""Run a complete extra workload with corrected paired counters and compressed raw data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('workload',choices=['redis-a','redis-c','memcached','liblinear'])
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--records',type=int,default=2000000)
    ap.add_argument('--ops',type=int,default=10000000)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    prefix=a.out/a.workload
    pin=ROOT.parent/'pin/pin';tool=ROOT/'src/profiler/pintool/obj-intel64/hotskew.so'
    client=ROOT/'benchmarks/zipf_client'
    lib=a.workload=='liblinear';mc=a.workload=='memcached'
    server=ROOT/('workloads/liblinear-multicore/train' if lib else
                'workloads/memcached-1.6.21/memcached' if mc else 'workloads/redis/src/redis-server')
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    data=ROOT/'workloads/liblinear-multicore/data/kdda'
    app=([str(server),'-s','6','-m','1','-e','0.01',str(data),str(a.out/'kdda.model')] if lib else
         [str(server),'-l','127.0.0.1','-p',str(port),'-m',str(a.records//1000*2+1024),'-t','1','-u',os.environ['USER']] if mc else
         [str(server),'--bind','127.0.0.1','--port',str(port),'--save','','--appendonly','no','--protected-mode','yes'])
    cmd=['setarch',os.uname().machine,'-R',str(pin),'-t',str(tool),'-paired','1','-epoch','10',
         '-epoch_refs','0','-dump_pages','1','-dump_max_mb','0','-track','0',
         '-l1_kb','48','-l1_assoc','12','-l2_kb','2048','-l2_assoc','16',
         '-l3_kb','40960' if lib else '4096','-l3_assoc','10' if lib else '1',
         '-roi_begin','hotskew_roi_begin','-roi_end','hotskew_roi_end','-tag',a.workload,'-o',str(prefix),'--',*app]
    metadata=dict(command=cmd,tool_sha256=digest(tool),executable_sha256=digest(server),
                  workload=a.workload,records=a.records if not lib else None,ops=a.ops if not lib else None,
                  input_sha256=digest(data) if lib else None,client_sha256=None if lib else digest(client),
                  status='running',started=time.time(),epoch_traffic=10000000,
                  roi='query phase' if not lib else 'training',input_family='KDD2010 kdda' if lib else 'custom Zipfian client, not official YCSB')
    manifest=Path(str(prefix)+'.manifest.json')
    def save():
        tmp=manifest.with_suffix('.tmp');tmp.write_text(json.dumps(metadata,indent=2)+'\n');tmp.replace(manifest)
    save(); fifo=Path(str(prefix)+'.pages.bin');os.mkfifo(fifo)
    guard=os.open(fifo,os.O_RDWR|os.O_NONBLOCK)
    process=compressor=None
    try:
        with fifo.open('rb') as inp,Path(str(fifo)+'.gz').open('wb') as out:
            compressor=subprocess.Popen(['gzip','-1c'],stdin=inp,stdout=out)
        with Path(str(prefix)+'.run.log').open('w') as log:
            process=subprocess.Popen(cmd,env=dict(os.environ,OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE'),stdout=log,stderr=subprocess.STDOUT)
            if lib:
                rc=process.wait()
                if rc:raise RuntimeError(f'training exit {rc}')
            else:
                for _ in range(120):
                    if process.poll() is not None:raise RuntimeError('server exited during startup')
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=1):break
                    except OSError:time.sleep(1)
                else:raise RuntimeError('server startup timeout')
                env=dict(os.environ)
                if mc:env['PROTO']='memcached'
                with Path(str(prefix)+'.client.log').open('w') as c:
                    subprocess.run([str(client),'127.0.0.1',str(port),str(a.records),str(a.ops),'0.99',
                                    '0' if a.workload=='redis-c' else '.5'],env=env,stdout=c,stderr=subprocess.STDOUT,check=True)
                process.send_signal(signal.SIGTERM);process.wait(timeout=60)
        os.close(guard);guard=None
        if compressor.wait(timeout=120):raise RuntimeError('gzip failed')
        summary=Path(str(prefix)+'.summary.txt').read_text()
        if 'collection_status  complete' not in summary or 'pages_bin_capped   yes' in summary:
            raise RuntimeError('collection incomplete or capped')
        metadata.update(status='complete',returncode=process.returncode)
    except BaseException as e:
        metadata.update(status='failed',error=str(e));raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if guard is not None:os.close(guard)
        if compressor is not None and compressor.poll() is None:
            compressor.terminate();compressor.wait()
        fifo.unlink(missing_ok=True)
        metadata['elapsed_s']=time.time()-metadata['started'];save()
    print(f'COMPLETE {a.workload}',flush=True)

if __name__=='__main__':main()
