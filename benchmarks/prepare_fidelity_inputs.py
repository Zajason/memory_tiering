#!/usr/bin/env python3
"""Prepare predeclared input-family controls; never fit an M5 reference curve."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import struct
import time

ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--storage',type=Path,default=Path('/mnt/research/memory-tiering'))
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():
        meta=json.loads(a.out.read_text())
        for g in meta['graphs'].values():
            if sha(g['path'])!=g['sha256']:raise ValueError('prepared input changed')
        return
    if not a.storage.exists() or shutil.disk_usage(a.storage).free < 100*1024**3:
        raise RuntimeError('input preparation requires 100 GiB free on the research storage drive')
    base=a.storage/'datasets/fidelity-v1'
    attempt=1
    while (base/f'attempt-{attempt}').exists():attempt+=1
    directory=base/f'attempt-{attempt}';directory.mkdir(parents=True)
    log=(directory/'preparation.log').open('w')
    env=dict(os.environ,OMP_NUM_THREADS='4',OMP_DYNAMIC='FALSE')
    def run(cmd):
        print('RUN '+' '.join(map(str,cmd)),flush=True)
        subprocess.run(list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
        log.flush()
    twitter=a.storage/'datasets/twitter'
    source=json.loads((twitter/'source.json').read_text())
    for item in source['assets']:
        if sha(twitter/item['name'])!=item['sha256']:raise ValueError('Twitter source changed')
    tool=directory/'prepare_twitter'
    run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror',ROOT/'benchmarks/prepare_twitter.cpp','-lz','-o',tool])
    main_el=directory/'twitter-hash75.el';tc_el=directory/'twitter-hash25.el'
    with (directory/'twitter-selection.json').open('w') as output:
        subprocess.run([str(tool),str(twitter),str(main_el),str(tc_el)],stdout=output,stderr=log,check=True)
    converter=ROOT/'workloads/gapbs/converter'
    graphs={}
    def collect(key,path,family,rule):
        with path.open('rb') as f:directed,edges,nodes=struct.unpack('<?qq',f.read(17))
        expected=17+(1+int(directed))*((nodes+1)*8+edges*(8 if path.suffix=='.wsg' else 4))
        if path.stat().st_size!=expected:raise ValueError('GAPBS serialized size does not match header')
        graphs[key]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,
                         nodes=nodes,directed_edges=edges,directed=directed,
                         family=family,selection=rule,m5_exact_input=False)
    for key,el in [('twitter-main',main_el),('twitter-tc',tc_el)]:
        graph=el.with_suffix('.sg')
        run([converter,'-f',el,'-s','-b',graph])
        collect(key,graph,'Twitter WWW2010 induced hash reduction',
                'SplitMix64(vertex_id)%4 < '+('3' if key=='twitter-main' else '1')+
                '; retain induced edges; ascending original-ID relabel; GAPBS symmetrize/deduplicate; '
                'vertex-count sentinel self-loop removed by GAPBS')
    archive=ROOT/'workloads/gapbs/graphs/gplus.zip'
    for key,snapshot,weighted in [('gplus-bc',4,False),('gplus-sssp',2,True)]:
        el=directory/f'gplus-snapshot{snapshot}.el'
        run([ROOT/'.venv/bin/python',ROOT/'benchmarks/prepare_gplus.py',archive,el,'--snapshot',snapshot])
        graph=el.with_suffix('.wsg' if weighted else '.sg')
        cmd=[converter,'-f',el]
        if weighted:cmd+=['-w']
        run(cmd+['-b',graph])
        collect(key,graph,f'Google+ IMC12 published snapshot {snapshot}',
                f'TimeID < {snapshot}; original IDs and direction; '+
                ('GAPBS-generated weights (authors weights unavailable)' if weighted else 'unweighted'))
    native=[]
    native_env=dict(os.environ,OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE')
    for name,key in [('bfs','twitter-main'),('cc','twitter-main'),('pr','twitter-main'),
                     ('tc','twitter-tc'),('bc','gplus-bc'),('sssp','gplus-sssp')]:
        memory=directory/f'{name}-native-memory.json'
        command=[ROOT/'workloads/gapbs'/name,'-f',graphs[key]['path'],'-n','1']
        subprocess.run(['/usr/bin/time','-f','{"peak_rss_kib":%M,"exit_code":%x}',
                        '-o',str(memory),*map(str,command)],stdout=log,stderr=log,
                       env=native_env,check=True)
        native.append(dict(workload=name,threads=1,trials=1,graph=key,
                           command=list(map(str,command)),**json.loads(memory.read_text())))
    meta=dict(status='complete',graphs=graphs,twitter_source=source,
              twitter_selection=json.loads((directory/'twitter-selection.json').read_text()),
              preparer_sha256=sha(ROOT/'benchmarks/prepare_twitter.cpp'),
              converter_sha256=sha(converter),google_archive_sha256=sha(archive),
              native_memory=native,completed=time.time(),rule_selected_before_measurement=True)
    a.out.write_text(json.dumps(meta,indent=2)+'\n')
    print('COMPLETE input preparation',flush=True)

if __name__=='__main__':main()
