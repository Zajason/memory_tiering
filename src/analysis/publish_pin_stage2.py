#!/usr/bin/env python3
"""Publish all completed controls and explicitly exploratory closest-case diagnostics."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import hotskew as H
from compare_reproduction import checked_histograms
from plot_paired import cdf

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/fidelity-stage2-2026-10-28'
NAMES=('bfs','cc','sssp','bc','pr','tc')

def main():
    OUT.mkdir(exist_ok=True)
    state=json.loads((OUT/'campaign.json').read_text())
    first=json.loads((ROOT/'results/fidelity-2026-10-27/campaign.json').read_text())
    sources=[]
    baseline=json.loads((ROOT/'results/uniform-traffic10/sources.json').read_text())
    for name in NAMES:
        sources.append(('prior-baseline',name,(ROOT/baseline[name]['manifest']).parent))
    for name in NAMES:
        job=first['jobs']['dataset-'+name]
        if job['status']=='complete':sources.append(('declared-real-input',name,Path(job['output'])))
    for key,job in first['jobs'].items():
        if job['status']=='complete' and job.get('output') and not key.startswith('dataset-'):
            sources.append(('phase1/'+key,key.split('-')[-1],Path(job['output'])))
    for name in ['bfs','cc']:
        directory=ROOT/'results/fidelity-2026-10-27/trials200-pool'
        manifest=directory/f'gapbs-{name}.manifest.json'
        if manifest.exists() and json.loads(manifest.read_text()).get('status')=='complete':
            sources.append(('phase1/trials200-pool-'+name,name,directory))
    for key,job in state['jobs'].items():
        if job['status']=='complete' and job.get('output'):
            name=key.split('-')[-1];sources.append((key,name,Path(job['output'])))
    records=[];curves={};meta={}
    for case,name,path in sources:
        hist,events,manifest=checked_histograms(path,name)
        meta[case,name]=manifest
        for scope in ['pooled','whole']:
            for stream in ['accesses','fills','traffic']:
                values=cdf(hist[scope,stream]);ref=H.M5_FIGURE4['gapbs-'+name]
                curves[case,name,scope,stream]=values
                error=max(abs(values[n]-ref[n]) for n in H.FIG4_N)
                records.append(dict(case=case,workload=name,scope=scope,stream=stream,
                    max_abs_error=float(error),threads=manifest['threads'],
                    trials=manifest['trials'],roi_epoch=manifest.get('roi_epoch',1),warm_setup=manifest['warm_setup'],
                    collection=manifest.get('roi'),llc_ways=manifest['command'][manifest['command'].index('-l3_assoc')+1],
                    input_sha256=manifest['input_sha256'],events=events[stream]))
    with (OUT/'scores.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    winners={}
    for name in NAMES:
        for stream in ['accesses','fills']:
            for scope in ['pooled','whole']:
                options=[r for r in records if r['workload']==name and r['stream']==stream and r['scope']==scope]
                winners[name,scope,stream]=min(options,key=lambda r:(r['max_abs_error'],r['case']))
    fig,axes=plt.subplots(2,3,figsize=(15,8),sharex=True,sharey=True)
    for ax,name in zip(axes.flat,NAMES):
        ref=H.M5_FIGURE4['gapbs-'+name];ax.plot(H.FIG4_N,[ref[n] for n in H.FIG4_N],'kx-',label='M5 digitized')
        for stream,color in [('accesses','#2464a3'),('fills','#ad426b')]:
            base=curves['declared-real-input',name,'pooled',stream]
            ax.plot(H.FIG4_N,[base[n] for n in H.FIG4_N],linestyle=':',color=color,label='Declared '+stream)
            win=winners[name,'pooled',stream];values=curves[win['case'],name,'pooled',stream]
            ax.plot(H.FIG4_N,[values[n] for n in H.FIG4_N],marker='o',color=color,
                    label=f"Exploratory {stream}: {win['case']}")
        ax.set_title(name.upper());ax.set_xticks(H.FIG4_N);ax.set_ylim(0,1);ax.grid(alpha=.15);ax.legend(fontsize=6)
    fig.suptitle('Exploratory closest completed cases: selection on reference, NOT independent replication')
    fig.supxlabel('N distinct lines per 4 KiB page-window');fig.supylabel('CDF')
    fig.tight_layout(rect=(.02,.03,1,.95));fig.savefig(OUT/'exploratory-closest.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(14,9),sharey=True)
    x=np.arange(len(NAMES));colors=['#2464a3','#15998a','#cf9e20','#ae4678','#666666']
    for ax,stream in zip(axes,[None,'accesses','fills']):
        for i,n in enumerate(H.FIG4_N):
            values=[]
            for name in NAMES:
                if stream is None:values.append(H.M5_FIGURE4['gapbs-'+name][n])
                else:
                    win=winners[name,'pooled',stream]
                    values.append(curves[win['case'],name,'pooled',stream][n])
            ax.bar(x+(i-2)*.15,values,width=.14,color=colors[i],label=f'N={n}')
        labels=[name.upper() if stream is None else name.upper()+'\n'+winners[name,'pooled',stream]['case'] for name in NAMES]
        ax.set_xticks(x,labels,fontsize=8);ax.set_ylim(0,1);ax.set_ylabel('CDF');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        ax.set_title('M5 digitized reference' if stream is None else 'Exploratory closest pooled '+stream,loc='left')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=5)
    fig.text(.5,.02,'Reference-selected per workload/stream. Different configurations may win. NOT independent replication or a paired single experiment.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94));fig.savefig(OUT/'exploratory-closest-full.png',dpi=170);plt.close(fig)
    lines=['# Pin fidelity stage 2: 28 October 2026','',
      'All controls are preserved. The declared real-input baseline remains the primary comparison. '
      'Closest-case selection below uses the reference itself and is exploratory, not independent validation or a recovered M5 protocol.','',
      'Candidate scores include the prior uniform-window baseline and completed phase 1 execution controls; '
      'improvements from earlier inputs are not discarded when a newer input performs worse. All candidates keep the 10M-event clock.','',
      '## Declared protocol','',
      'Full observed process versus timed-kernel collection; real-input 20-thread controls; separate nine-way LLC controls. '
      'All use paired accesses/fills/traffic and 10M memory-event boundaries, with partial final windows and separate whole-ROI distributions. '
      'Footprint candidates use hash fractions 11/16, 10/16, 12/16, in that order, targeting native 20-thread TC RSS of 5,000,000,000 bytes. '
      'Stop at the first candidate within 10%; otherwise select the nearest RSS and label the mismatch. No Pin CDF enters this input selection.', '',
      '## Progress','',f"Campaign: {state['status']}",'']
    if state.get('multithread_hold'):
        lines += ['Multithreaded controls are held for separate profiler correctness and scaling validation. '
                  'The oversized TC attempt was interrupted at the user\'s request; no partial CDF is published. '
                  'One-thread controls continue with the frozen original instrument. '
                  'See [scalability validation](pin-scalability.md).','']
    lines += ['| Job | State |','|---|---|']
    for key,job in state['jobs'].items():lines.append(f"| {key} | {job['status']} |")
    lines+=['','## All completed scores','',
      '| Case | Workload | Scope | Stream | Max difference (pp) | Threads | LLC ways | Collection |',
      '|---|---|---|---|---:|---:|---:|---|']
    for r in records:
        lines.append(f"| {r['case']} | {r['workload']} | {r['scope']} | {r['stream']} | {100*r['max_abs_error']:.2f} | {r['threads']} | {r['llc_ways']} | {r['collection']} |")
    process_rows=[r for r in records if r['case'].startswith('process-')
                  and r['scope']=='pooled' and r['stream']=='fills']
    if process_rows:
        lines+=['','## Completed process-scope controls','']
        for r in process_rows:
            before=next(b for b in records if b['case']=='declared-real-input'
                        and b['workload']==r['workload'] and b['scope']=='pooled'
                        and b['stream']=='fills')
            lines.append(f"{r['workload'].upper()}: pooled demand-fill error changes from "
                         f"{100*before['max_abs_error']:.2f} to {100*r['max_abs_error']:.2f} "
                         'percentage points when observed user-space setup is included.')
        lines+=['','These are scope controls, not a recovered M5 collection procedure. '
                'Kernel copies remain invisible. The common-protocol primary figure is not replaced.']
    footprint=OUT/'tc-footprint.json'
    if footprint.exists():
        selected=json.loads(footprint.read_text())
        lines+=['','## Native RSS input selection','',
          f"Target: {selected['target_bytes']/1e9:.2f} GB. Selected native peak RSS: "
          f"{selected['native']['peak_rss_kib']*1024/1e9:.2f} GB; absolute relative mismatch "
          f"{100*selected['relative_footprint_error']:.1f}%. Within 10%: {selected['within_10_percent']}.", '',
          'The candidate is selected by native RSS only, before its Pin CDF. '
          'A nearest candidate outside tolerance is not a size-matched reproduction.', '',
          '| Candidate rule | Native peak RSS (GB) | Absolute target mismatch (%) |',
          '|---|---:|---:|']
        for candidate in selected['candidates']:
            lines.append(f"| {candidate['rule']} | {candidate['native']['peak_rss_kib']*1024/1e9:.2f} | "
                         f"{100*candidate['relative_footprint_error']:.1f} |")
    lines+=['','## Exploratory closest pooled cases','',
      '![Exploratory closest pooled controls](../results/fidelity-stage2-2026-10-28/exploratory-closest.png)','',
      '![M5, closest access and closest miss controls](../results/fidelity-stage2-2026-10-28/exploratory-closest-full.png)','',
      'Access and fill winners may use different configurations and are not a paired single experiment. '
      'No pooled result is replaced by a more flattering whole-ROI result. Neither a lower score nor a passed unit test establishes hardware equivalence.', '']
    (ROOT/'docs/pin-fidelity-stage2.md').write_text('\n'.join(lines))

if __name__=='__main__':main()
