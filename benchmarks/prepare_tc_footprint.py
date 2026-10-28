#!/usr/bin/env python3
"""Select TC graph by native RSS only; never read the M5 reference or a Pin CDF."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
STORE=Path('/mnt/research/memory-tiering')
OUT=ROOT/'results/fidelity-stage2-2026-10-28'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    final=OUT/'tc-footprint.json'
    if final.exists():
        saved=json.loads(final.read_text())
        if sha(saved['path'])!=saved['sha256']:raise ValueError('selected footprint input changed')
        return
    base=STORE/'datasets/tc-footprint'
    attempt=1
    while (base/f'attempt-{attempt}').exists():attempt+=1
    directory=base/f'attempt-{attempt}';directory.mkdir(parents=True)
    if shutil.disk_usage(STORE).free<100*1024**3:raise RuntimeError('need 100 GiB free')
    # Native CSR conversion has a larger peak than profiling; avoid competing
    # with the independent full-system queue for most of the host's RAM.
    while True:
        memory={row.split(':')[0]:int(row.split()[1])*1024
                for row in Path('/proc/meminfo').read_text().splitlines()}
        if memory['MemAvailable']>=26*1024**3:break
        print('Waiting for 26 GiB available before footprint preparation',flush=True)
        time.sleep(60)
    source=STORE/'datasets/twitter'
    provenance=json.loads((source/'source.json').read_text())
    for asset in provenance['assets']:
        if sha(source/asset['name'])!=asset['sha256']:raise ValueError('Twitter source hash mismatch')
    binary=directory/'prepare_twitter'
    subprocess.run(['g++','-std=c++17','-O3',str(ROOT/'benchmarks/prepare_twitter.cpp'),'-lz','-o',str(binary)],check=True)
    trials=[]
    # Order and target fixed before any candidate's Pin measurements.
    target=5_000_000_000; tolerance=.10
    for numerator in [11,10,12]:
        folder=directory/f'hash{numerator}-of16';folder.mkdir()
        with (folder/'prepare.log').open('w') as log:
            command=[str(binary),str(source),str(folder/'main.el'),str(folder/'tc.el'),
                     '41652230','1468365182',str(numerator),'16']
            selection=json.loads(subprocess.check_output(command,stderr=log))
            graph=folder/'tc.sg'
            subprocess.run([str(ROOT/'workloads/gapbs/converter'),'-f',str(folder/'tc.el'),'-s','-b',str(graph)],
                           stdout=log,stderr=log,check=True,env=dict(os.environ,OMP_NUM_THREADS='4'))
            with graph.open('rb') as f:directed,edges,nodes=struct.unpack('<?qq',f.read(17))
            if directed or graph.stat().st_size!=17+8*(nodes+1)+4*edges:raise ValueError('invalid CSR size')
            memory=folder/'memory.json'
            cmd=[str(ROOT/'workloads/gapbs/tc'),'-f',str(graph),'-n','1']
            start=time.time()
            subprocess.run(['/usr/bin/time','-f','{"peak_rss_kib":%M,"exit_code":%x}','-o',str(memory),*cmd],
                           check=True,stdout=log,stderr=log,
                           env=dict(os.environ,OMP_NUM_THREADS='20',OMP_DYNAMIC='FALSE'))
            rss=json.loads(memory.read_text());delta=abs(rss['peak_rss_kib']*1024-target)/target
            record=dict(path=str(graph),sha256=sha(graph),selection=selection,nodes=nodes,edges=edges,
                        native=rss,native_threads=20,native_command=cmd,native_elapsed_s=time.time()-start,
                        target_bytes=target,relative_footprint_error=delta,
                        rule=f'SplitMix64(original ID)%16 < {numerator}; induced; ascending relabel; symmetrize')
            trials.append(record)
            (OUT/'tc-footprint-candidates.json').write_text(json.dumps(trials,indent=2)+'\n')
            if delta<=tolerance:break
    selected=dict(min(trials,key=lambda r:r['relative_footprint_error']))
    selected.update(candidates=trials,target_unit='decimal GB; paper unit ambiguity remains',
                    within_10_percent=selected['relative_footprint_error']<=tolerance,
                    selection_criterion='native RSS only, before any Pin CDF',m5_exact_input=False,
                    selector_sha256=sha(ROOT/'benchmarks/prepare_twitter.cpp'))
    final.write_text(json.dumps(selected,indent=2)+'\n')

if __name__=='__main__':main()
