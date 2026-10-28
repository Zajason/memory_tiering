#!/usr/bin/env python3
"""Figure 4-style comparisons from completed simulator jobs, never partial summaries."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import hotskew as H

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'results/revalidated-2026-10-25'
OUT=SOURCE/'sim-comparison'
NAMES=('bfs','cc','sssp','bc','pr','tc')

def validated_histogram(path, expected):
    """Reject truncated or duplicated bins even though the general reader is permissive."""
    lines=path.read_text().splitlines()
    header='# full unique-word histogram (words,pages)'
    if lines.count(header)!=1:raise ValueError('missing or duplicate histogram header')
    block=[]
    for line in lines[lines.index(header)+1:]:
        if line.startswith('#'):break
        if line.strip():block.append(line)
    bins={}
    for row in csv.reader(block):
        if len(row)!=2:raise ValueError('malformed histogram row')
        word,pages=map(int,row)
        if word in bins or not 0<=word<=64 or pages<0:raise ValueError('invalid histogram bin')
        bins[word]=pages
    if set(bins)!=set(range(65)):raise ValueError('incomplete histogram')
    hist=np.array([bins[i] for i in range(65)],dtype=np.int64)
    meta=H.load_summary(path)
    actual={key:int(meta[field].split()[0]) for key,field in
            [('events','dram_accesses'),('epochs','epochs'),('pages','page_observations')]}
    if actual!=expected:raise ValueError('summary changed since job completion')
    if hist[0] or hist.sum()!=actual['pages']:raise ValueError('invalid touched-page population')
    if actual['events']<sum(i*int(v) for i,v in enumerate(hist)):
        raise ValueError('more unique touches than requests')
    if actual['pages']==0 or actual['epochs']<1:raise ValueError('empty observation')
    return hist,actual

def completed_job(job):
    if job.get('status')!='complete':return None
    log=Path(job['log']).read_text()
    if 'exit #3' not in log or '-- stopping, summary follows' not in log:
        raise ValueError('missing ROI completion evidence')
    return job

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    state=json.loads((SOURCE/'sim-status.json').read_text())
    curves={};records=[];provenance={}
    for name,job in state['jobs'].items():
        if completed_job(job) is None:continue
        base='bc' if name.startswith('bc-window-') else name
        if 'gapbs-'+base not in H.M5_FIGURE4 and base not in H.M5_FIGURE4:continue
        ref=H.M5_FIGURE4.get('gapbs-'+base,H.M5_FIGURE4.get(base))
        for file,expected in job['summaries'].items():
            path=Path(job['output'])/file
            hist,counts=validated_histogram(path,expected)
            cdf=np.cumsum(hist)/hist.sum()
            port='bridge' if file.endswith('.bridge') else 'high-controller' if file.endswith('.high') else 'ordinary-controller'
            key=name+'/'+port
            provenance[key]=dict(summary=str(path.relative_to(ROOT)),
                summary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                command=job['command'],binary_sha256=job['binary_sha256'],
                config_sha256=job.get('config_sha256'),graph=job.get('graph'),**counts)
            for n in H.FIG4_N:
                records.append(dict(workload=name,port=port,scope='pooled page-windows',n=n,
                    cdf=float(cdf[n]),m5=float(ref[n]),delta=float(cdf[n]-ref[n]),**counts))
            if port=='bridge' and name in NAMES:curves[name]=cdf
    if not records:raise ValueError('no complete simulator measurements')
    with (OUT/'comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    (OUT/'sources.json').write_text(json.dumps(provenance,indent=2)+'\n')
    pin={}
    with (ROOT/'results/uniform-traffic10/comparison.csv').open() as f:
        for r in csv.DictReader(f):
            if r['scope']=='pooled' and r['stream']=='fills':pin[r['workload'],int(r['n'])]=float(r['cdf'])
    fig,axes=plt.subplots(3,1,figsize=(14,9),sharex=True,sharey=True)
    colors=['#2464a3','#15998a','#cf9e20','#ae4678','#666666'];x=np.arange(len(NAMES))
    for ax,kind,title in zip(axes,['paper','pin','sim'],
            ['M5 Figure 4: digitized reference','Pin baseline: modeled demand fills',
             'SimCXL: accepted CXL-bridge line requests (reads + writes)']):
        for i,n in enumerate(H.FIG4_N):
            values=[H.M5_FIGURE4['gapbs-'+name][n] if kind=='paper' else pin[name,n]
                    if kind=='pin' else curves[name][n] if name in curves else np.nan for name in NAMES]
            ax.bar(x+(i-2)*.15,values,width=.14,color=colors[i],label=f'N={n}')
        if kind=='sim':
            for i,name in enumerate(NAMES):
                if name not in curves:ax.text(i,.40,'Pending',ha='center',color='#777777')
        ax.set_title(title,loc='left',fontsize=12);ax.set_ylim(0,1);ax.set_ylabel('CDF')
        ax.set_xticks(x,[v.upper() for v in NAMES]);ax.tick_params(axis='x',labelbottom=True)
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=5)
    fig.text(.5,.035,'10M-event windows; each port has its own touched-page population. No bridge/controller pooling.',ha='center',fontsize=9)
    fig.text(.5,.015,'Different inputs and execution: Pin Google+ BC/SSSP; simulator kron-23 (TC kron-21). Not identical-trace replication.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(OUT/'figure4-m5-pin-simulator.png',dpi=180);plt.close(fig)
    kron={}
    with (ROOT/'results/uniform-kron-traffic10/comparison.csv').open() as f:
        for r in csv.DictReader(f):
            if r['scope']=='pooled' and r['stream']=='traffic':kron[r['workload'],int(r['n'])]=float(r['cdf'])
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    for ax,name in zip(axes.flat,['bfs','cc','bc','sssp']):
        ref=H.M5_FIGURE4['gapbs-'+name]
        ax.plot(H.FIG4_N,[ref[n] for n in H.FIG4_N],'kx-',label='M5 digitized')
        ax.plot(H.FIG4_N,[kron[name,n] for n in H.FIG4_N],'o--',label='Pin total traffic, kron-23')
        if name in curves:ax.plot(H.FIG4_N,[curves[name][n] for n in H.FIG4_N],'s-',label='SimCXL bridge, kron-23')
        else:ax.text(24,.5,'Simulator pending',ha='center')
        ax.set_title(name.upper());ax.set_ylim(0,1);ax.set_xticks(H.FIG4_N);ax.grid(alpha=.15)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',ncol=3)
    fig.supxlabel('N distinct 64-byte lines per 4 KiB page-window')
    fig.supylabel('CDF among touched page-window observations')
    fig.tight_layout(rect=(.03,.04,1,.94));fig.savefig(OUT/'kron-traffic-control.png',dpi=160);plt.close(fig)
    lines=['# M5 Figure 4-style simulator comparison','',
      'Only jobs marked complete with ROI-end evidence and intact full histograms enter this report. '
      'Interrupted jobs are pending, not zero-valued measurements.','',
      '![M5, Pin baseline and simulator](../results/revalidated-2026-10-25/sim-comparison/figure4-m5-pin-simulator.png)','',
      '| Job | Port | Maximum five-point difference (pp) | Events | Page-window observations |',
      '|---|---|---:|---:|---:|']
    for key,meta in provenance.items():
        name,port=key.split('/')
        rows=[r for r in records if r['workload']==name and r['port']==port]
        err=max(abs(r['delta']) for r in rows)*100
        lines.append(f"| {name} | {port} | {err:.2f} | {meta['events']:,} | {meta['pages']:,} |")
    lines+=['','## Same input-family, writeback-inclusive control','',
      'The primary overview retains the current Pin baseline, which uses Google+ for BC/SSSP. '
      'The supplementary control instead uses existing kron-23 Pin total-traffic results for all four completed graph workloads. '
      'This removes that graph-family mismatch and includes writebacks on both sides; it still does not establish identical graph files, binaries or traces.', '',
      '![All-Kronecker traffic comparison](../results/revalidated-2026-10-25/sim-comparison/kron-traffic-control.png)','',
      '| Workload | Pin kron-23 traffic error (pp) | Simulator bridge error (pp) |',
      '|---|---:|---:|']
    for name in ['bfs','cc','bc','sssp']:
        if name not in curves:continue
        ref=H.M5_FIGURE4['gapbs-'+name]
        pe=max(abs(kron[name,n]-ref[n]) for n in H.FIG4_N)*100
        se=max(abs(curves[name][n]-ref[n]) for n in H.FIG4_N)*100
        lines.append(f'| {name} | {pe:.2f} | {se:.2f} |')
    lines+=['','## Interpretation','',
      'The bridge is the primary device-side comparison; ordinary and high-memory controllers are reported separately as diagnostics. '
      'Bridge and downstream controller observe overlapping traffic and must not be added. Independent port clocks must not be pooled as synchronized windows.', '',
      'Simulator requests include physical and kernel traffic, unlike Pin user-space operands. '
      'They also reflect a different CPU, cache, OS and placement configuration. Pin demand fills exclude dirty writebacks; '
      'the bridge reads+writes stream does not. This is not an isolated kernel-visibility experiment or a paired same-input comparison.', '',
      'The simulator uses an atomic warm-up then TimingSimpleCPU within the timed ROI. '
      'Graphs are kron-23 except TC kron-21; M5 uses unavailable reduced real-world inputs. '
      'The exact original collection clock and page population remain unresolved. Reference values are digitized, approximately +/-2 pp.', '',
      'The pooled summary cannot reconstruct a whole-ROI union; no such simulator result is claimed. '
      'Raw comparison values and per-output hashes are preserved beside the figure.','']
    (ROOT/'docs/simulator-figure4.md').write_text('\n'.join(lines))
    print(f'Validated {len(provenance)} simulator port outputs; plotted {len(curves)} completed graph jobs')

if __name__=='__main__':main()
