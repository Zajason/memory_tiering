#!/usr/bin/env python3
"""Publish every completed fidelity control and keep incomplete jobs visible."""
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
OUT=ROOT/'results/fidelity-2026-10-27'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'results/uniform-traffic10/scores.csv').open() as f:
        baseline={(r['workload'],r['stream']):float(r['max_abs_error']) for r in csv.DictReader(f) if r['scope']=='pooled'}
    base_curves={name:{} for name in ['bfs','cc','pr','tc','bc','sssp']}
    with (ROOT/'results/uniform-traffic10/comparison.csv').open() as f:
        for r in csv.DictReader(f):
            if r['scope']=='pooled' and r['stream']=='fills':base_curves[r['workload']][int(r['n'])]=float(r['cdf'])
    rows=[];curves=[];dataset={}
    for file in sorted(OUT.rglob('gapbs-*.manifest.json')):
        meta=json.loads(file.read_text())
        if meta['status']!='complete':continue
        name=file.name.removeprefix('gapbs-').removesuffix('.manifest.json')
        hist,events,meta=checked_histograms(file.parent,name)
        case=str(file.parent.relative_to(OUT))
        for scope in ['pooled','whole']:
            for stream in ['accesses','fills','traffic']:
                values=cdf(hist[scope,stream]);ref=H.M5_FIGURE4['gapbs-'+name]
                rows.append(dict(case=case,workload=name,scope=scope,stream=stream,
                    threads=meta['threads'],trials=meta['trials'],roi_epoch=meta.get('roi_epoch',1),
                    warm_setup=meta['warm_setup'],graph_family=meta['graph_family'],
                    max_abs_error=max(abs(values[n]-ref[n]) for n in H.FIG4_N),
                    p16=float(values[16]),events=events[stream]))
                if scope=='pooled' and stream=='fills':curves.append((name,case,values))
                if case=='dataset' and scope=='pooled':dataset[name,stream]=values
    if rows:
        with (OUT/'scores.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey=True)
        for name,ax in zip(['bfs','cc','pr','tc','bc','sssp'],axes.flat):
            ref=H.M5_FIGURE4['gapbs-'+name]
            ax.plot(list(ref),list(ref.values()),'kx-',label='M5 digitized',linewidth=2)
            ax.plot(H.FIG4_N,[base_curves[name][n] for n in H.FIG4_N],color='#777777',linestyle='--',label='Prior baseline')
            for workload,case,values in curves:
                if workload==name:ax.plot(H.FIG4_N,[values[n] for n in H.FIG4_N],marker='o',label=case)
            ax.set_title(name.upper());ax.set_ylim(0,1);ax.set_xticks(H.FIG4_N);ax.grid(alpha=.2)
            ax.legend(fontsize=7)
        fig.supxlabel('N distinct 64-byte lines per 4 KiB page-window')
        fig.supylabel('Fraction with at most N lines');fig.suptitle('Demand fills: prior baseline and all completed fidelity controls')
        fig.tight_layout();fig.savefig(OUT/'demand-fill-controls.png',dpi=160);plt.close(fig)
    names=['bfs','cc','sssp','bc','pr','tc']
    if all((name,stream) in dataset for name in names for stream in ['accesses','fills']):
        fig,axes=plt.subplots(3,1,figsize=(13,8.5),sharex=True,sharey=True)
        colors=['#2464a3','#15998a','#cf9e20','#ae4678','#666666'];x=np.arange(6)
        for ax,(stream,title) in zip(axes,[(None,'M5 Figure 4: digitized reference'),
                                          ('accesses','Application demand accesses'),
                                          ('fills','Modeled demand misses')]):
            for i,n in enumerate(H.FIG4_N):
                values=[H.M5_FIGURE4['gapbs-'+name][n] if stream is None else dataset[name,stream][n] for name in names]
                ax.bar(x+(i-2)*.15,values,width=.14,color=colors[i],label=f'N={n}')
            ax.set_title(title,loc='left');ax.set_ylim(0,1);ax.set_ylabel('CDF')
            ax.set_xticks(x,[name.upper() for name in names]);ax.tick_params(axis='x',labelbottom=True)
            ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=5)
        fig.suptitle('M5 and documented real-input controls',y=.95)
        fig.text(.5,.035,'One thread/trial; 10M total memory-event windows; own touched-page populations.',ha='center',fontsize=9)
        fig.text(.5,.015,'Twitter induced reductions; Google+ snapshots 4 (BC), 2 (SSSP). Authors exact inputs/schedule unresolved.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.06,1,.92))
        fig.savefig(ROOT/'docs/assets/fig4_fidelity_full.png',dpi=180);plt.close(fig)
    statefile=OUT/'campaign.json'
    state=json.loads(statefile.read_text()) if statefile.exists() else {'jobs':{}}
    lines=['# M5 fidelity follow-up: 27 October 2026','',
      'All cases below were declared before collecting their new measurements. '
      'No window or graph reduction is selected by its agreement with the paper.','',
      '## Protocol','',
      '- Default controls: corrected Pin instrument, stock GAPBS, 40 MiB / 10-way LLC, 10M total memory-event windows, final partial windows retained.',
      '- Thread control: BFS/CC at 20 software threads. The model has private per-thread caches and a serialized shared LLC; no coherence or true hardware scheduling.',
      '- Trial controls: BFS/CC at three trials, with and without closing a window at each ROI boundary. Three trials are a scope sensitivity test; artifact performance commands use 200.',
      '- Additional scope control: BFS/CC with 200 trials, one thread, no forced window reset between ROI calls. Added after the three-trial pilot, using the published trial count rather than optimizing a reference score. This isolates repetition; it does not claim the complete 20-thread artifact execution.',
      '- Cache-state control: BFS/CC with caches warmed during setup. Warm-up references do not enter the observation population.',
      '- PageRank control: one trial with artifact convergence settings (-i1000 -t1e-4). The artifact performance command uses 20 trials.',
      '- Twitter: induced vertex subsets selected by SplitMix64(original ID)%4 < 3 for BFS/CC/PR, < 1 for TC. Relabel retained vertices in ascending original-ID order, then use GAPBS symmetrization/deduplication. These are our documented reductions; the authors reductions remain unavailable.',
      '- Google+: published snapshot 4 for BC and snapshot 2 for SSSP; direction preserved. SSSP weights generated by GAPBS, since authors weights are unavailable.',
      '- Dataset follow-ups use one thread/trial and unchanged 10M memory-event windows. Inputs and execution changes are assessed separately.',
      '- Accesses, demand fills and total traffic remain separate metrics. All five thresholds are scored; no best-case selection.','',
      '## Progress','', '| Job | State |','|---|---|']
    for name,job in state['jobs'].items():lines.append(f"| {name} | {job['status']} |")
    for name in ['bfs','cc']:
        file=OUT/'trials200-pool'/f'gapbs-{name}.manifest.json'
        job=json.loads(file.read_text()) if file.exists() else {'status':'queued after input campaign'}
        lines.append(f"| trials200-pool-{name} | {job['status']} |")
    lines+=['','## Completed comparisons','',
            '| Case | Workload | Scope | Access error | Fill error | Traffic error | Baseline pooled fill error |',
            '|---|---|---|---:|---:|---:|---:|']
    for case,name in sorted({(r['case'],r['workload']) for r in rows}):
        for scope in ['pooled','whole']:
            scores={r['stream']:r['max_abs_error'] for r in rows if r['case']==case and r['workload']==name and r['scope']==scope}
            lines.append(f"| {case} | {name} | {scope} | {scores['accesses']:.3f} | {scores['fills']:.3f} | {scores['traffic']:.3f} | {baseline[name,'fills']:.3f} |")
    lines+=['','Errors are maximum absolute differences from the digitized reference over N=4,8,16,32,48; 0.10 means ten percentage points. They are similarity scores, not evidence of identical methodology.']
    if curves:lines+=['','![All completed demand-fill controls](../results/fidelity-2026-10-27/demand-fill-controls.png)']
    if all((name,'fills') in dataset for name in names):
        lines+=['','![M5, accesses and demand misses on documented real-input controls](assets/fig4_fidelity_full.png)']
    if (OUT/'inputs.json').exists():
        inputs=json.loads((OUT/'inputs.json').read_text())
        lines+=['','## Native footprint checks','','| Workload | Native peak RSS (GiB) | Graph file (GiB) |','|---|---:|---:|']
        for r in inputs.get('native_memory',[]):
            size=inputs['graphs'][r['graph']]['bytes']/1024**3
            lines.append(f"| {r['workload']} | {r['peak_rss_kib']/1024**2:.3f} | {size:.3f} |")
        lines+=['','These are one-thread, one-trial native memory footprints. Pin memory overhead is excluded. File size and process RSS are different quantities. No graph reduction is retuned from its measured CDF.']
    lines+=['','## Remaining evidence gaps','',
      'The official artifact still omits its dataset-download link and a recovered Figure 4 collection runner. '
      'The exact reduced graphs, region/reset schedule, page denominator and Figure 4 trial configuration remain unresolved. '
      'The draft author request has not been sent. Additional storage removes the capacity restriction, not this evidence gap.', '',
      'The full-system checkpoint validation uses a bounded guest dd workload and compares final probe files and completion tick after process death/restore. '
      'Passing synthetic tests alone does not certify full-system recovery or reboot survival. The existing PageRank attempt has no recoverable checkpoint.','']
    (ROOT/'docs/fidelity-followup.md').write_text('\n'.join(lines))

if __name__=='__main__':main()
