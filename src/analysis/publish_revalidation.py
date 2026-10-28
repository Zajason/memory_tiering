"""Publish only completed, validated extension outputs; show pending jobs explicitly."""
import fcntl
import csv
import json
import subprocess
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import hotskew as H

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/revalidated-2026-10-25'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'publish.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX)
    statuses={}
    for lane in ['pin','sim']:
        p=OUT/f'{lane}-status.json'
        if p.exists():statuses[lane]=json.loads(p.read_text())
    data=[]
    for file in sorted((OUT/'analysis').glob('*.json')):
        item=json.loads(file.read_text())
        if item['status']=='validated':data.append((file.stem,item))
    figures=OUT/'figures';figures.mkdir(exist_ok=True)
    trackers=[]
    for manifest in sorted((OUT/'pin').rglob('*.manifest.json')):
        meta=json.loads(manifest.read_text())
        prefix=Path(str(manifest).removesuffix('.manifest.json'))
        csvpath=Path(str(prefix)+'.tracker.csv')
        if meta.get('status')!='complete' or not csvpath.exists():continue
        summary=H.load_summary(str(prefix)+'.summary.txt')
        if summary.get('collection_status')!='complete':continue
        with csvpath.open() as f:rows=list(csv.DictReader(f))
        expected=int(summary['epochs'].split()[0])
        if not rows:continue
        keys={(int(r['epoch']),int(r['n'])) for r in rows}
        budgets={int(r['n']) for r in rows}
        if len(keys)!=len(rows) or keys!={(e,n) for e in range(expected) for n in budgets}:
            raise ValueError(f'incomplete tracker sweep: {csvpath}')
        for r in rows:
            if not 0<=float(r['hpt_access_ratio'])<=1.000001:raise ValueError('invalid HPT score')
        trackers.append((prefix.name,rows))
    if trackers:
        fig,ax=plt.subplots(figsize=(9,5))
        for name,rows in trackers:
            ns=sorted({int(r['n']) for r in rows})
            ax.plot(ns,[np.mean([float(r['hpt_access_ratio']) for r in rows if int(r['n'])==n]) for n in ns],
                    marker='o',linestyle='--' if rows[0]['algo']=='cmsketch' else '-',label=f"{name}: {rows[0]['algo']}")
        ax.set_xscale('log',base=2);ax.set_ylim(0,1.03);ax.set_xlabel('Tracker entries N (K=128)')
        ax.set_ylabel('Mean per-window HPT access-count ratio')
        ax.set_title('Bounded page trackers; separate executions, not identical traces')
        ax.legend(fontsize=7,ncol=2);ax.grid(alpha=.2);fig.tight_layout()
        fig.savefig(figures/'trackers.png',dpi=160);plt.close(fig)
    if data:
        fig,ax=plt.subplots(figsize=(9,4.8))
        for name,d in data:
            rows=[r for r in d['granularity'] if r['page_bytes']==4096]
            ax.plot([r['word_bytes'] for r in rows],[r['mean_fraction'] for r in rows],marker='o',label=name)
        ax.set_xscale('log',base=2);ax.set_xlabel('Tracking unit (bytes), fixed 4 KiB page')
        ax.set_ylabel('Mean fraction reported touched');ax.set_ylim(0,1.03)
        ax.set_title('Corrected runs: granularity sensitivity (total memory traffic)')
        ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(figures/'granularity.png',dpi=160);plt.close(fig)
        rows=[(name,next((r for r in d['turnover'] if r['k']==10000),None)) for name,d in data]
        rows=[(name,r) for name,r in rows if r]
        if rows:
            fig,ax=plt.subplots(figsize=(9,4.8));x=np.arange(len(rows))
            ax.bar(x-.18,[r['traffic_weighted_coverage'] for _,r in rows],.35,label='Previous-window top-10K')
            ax.bar(x+.18,[r['traffic_weighted_oracle'] for _,r in rows],.35,label='Current-window oracle')
            ax.set_xticks(x,[n for n,_ in rows],rotation=20,ha='right');ax.set_ylim(0,1)
            ax.set_ylabel('Fraction of memory events captured');ax.legend();fig.tight_layout()
            fig.savefig(figures/'turnover.png',dpi=160);plt.close(fig)
        costrows=[(name,[r for r in d['placement_cost'] if r['fast_fraction']==.25 and r['policy']=='count-only']) for name,d in data]
        costrows=[(name,rows) for name,rows in costrows if rows]
        if costrows:
            fig,ax=plt.subplots(figsize=(9,4.8))
            for name,rows in costrows:
                ax.plot([r['migration_ns']/1000 for r in rows],[r['cost_ratio_vs_all_slow'] for r in rows],marker='o',label=name)
            ax.axhline(1,color='gray',linestyle=':');ax.set_xlabel('Assumed promotion cost (microseconds/page)')
            ax.set_ylabel('All-slow cost / placement cost')
            ax.set_title('Serial cost model, NOT application speedup; 25% first-window capacity')
            ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout()
            fig.savefig(figures/'serial-cost.png',dpi=160);plt.close(fig)
    lines=['# Extension revalidation: 25 October 2026','',
      'This is a fresh campaign using the corrected instrument. A completed benchmark is not automatically a validated analysis. '
      'The status tables distinguish the two. Historical measurements are preserved, not relabelled.', '',
      '## Declared protocol','',
      '- Pin: one thread, timed-kernel ROI, cold model, 10M total memory-event windows including the final partial window.',
      '- GAPBS: 40 MiB / 10-way LLC, kron-23 except Google+ snapshot 1 for BC/SSSP. Space-Saving and Count-Min in separate executions, K=128 and budgets 50/128/512/2048/8192.',
      '- Redis A/C and Memcached: custom Zipfian client, 2M records and 10M operations, 4 MiB / 1-way LLC. These are local workload configurations, not exact artifact replication.',
      '- Liblinear: full local KDD2010 kdda, solver 6, tolerance 0.01, one thread. The paper uses KDD2012.',
      '- Simulator: rebuilt SimCXL, high-memory CXL path, 40 MiB / 10-way LLC, Atomic until ROI then TimingSimpleCPU, stop at ROI end. Guest TC uses kron-21, other graph workloads kron-23. This is not a paired identical-trace comparison with Pin.',
      '- Full-system memory-controller and bridge epochs are independent. Do not pool them as synchronized windows, and never add the bridge to its downstream controller (double-counting).',
      '- No workload-specific parameter fitting. ASLR disabled for Pin. No licensed SPEC workload or unmeasured CacheLib result is claimed.','',
      '## Calibration','',
      'The rebuilt simulator reports 30,321 accepted line requests and 474 page observations at both bridge and controller after draining. '
      'Their histograms agree, and sum(words × pages) equals the number of requests. Without draining, seven requests were still in flight. '
      'This validates this synthetic path, not arbitrary full-system behaviour.','',
      '## Campaign progress','']
    for lane,state in statuses.items():
        lines += [f'### {lane}: {state["status"]}','','| Job | State | Elapsed seconds |','|---|---|---:|']
        for job in state.get('planned_jobs',[]):
            d=state['jobs'].get(job,{})
            lines.append(f"| {job} | {d.get('status','queued')} | {d.get('elapsed_s',0):.1f} |")
            if d.get('error'):lines.append(f"\nFailure detail for `{job}`: `{d['error']}`\n")
        lines.append('')
    lines += ['## Validated raw-data analyses','','| Run | Epochs | Memory events | Word counts saturated |','|---|---:|---:|---|']
    for name,d in data:lines.append(f"| {name} | {d['epochs']} | {d['events']:,} | {d['saturated_words']} |")
    lines += ['', 'Raw records must cover every summary observation and event, match the full unique-line histogram, and have unique page keys within consecutive epochs. '
              'Saturated word counters invalidate word-frequency rankings, but not touched masks or 64-bit page totals. '
              'Single-epoch runs cannot support turnover or previous-window placement.', '',
              '## Figures','', '![Granularity](../results/revalidated-2026-10-25/figures/granularity.png)','',
              '![Turnover](../results/revalidated-2026-10-25/figures/turnover.png)','',
              '![Trackers](../results/revalidated-2026-10-25/figures/trackers.png)','',
              '![Serial cost sensitivity](../results/revalidated-2026-10-25/figures/serial-cost.png)','',
              '## Interpretation','',
              'Granularity is exact re-bucketing of observed virtual addresses. It does not demonstrate OS huge-page allocation or hardware migration waste. '
              'Turnover uses deterministic address tie-breaking and traffic-weighted coverage. Stability per memory-event window is not stability per second.', '',
              'Placement uses previous-window candidates and fixed first-window capacity. The illustrative serial cost uses 100 ns local, 220 ns slow, '
              'and promotion costs 0/1/3/10/30 microseconds. It omits demotion costs, CPU execution, MLP, bandwidth contention, and feedback. '
              'The cost ratio is neither application speedup nor a proven bound. Revalidation cannot turn this model into a measured speedup.', '',
              '## Code and outputs','',
              '`experiments/revalidation_campaign.py` runs the two lanes. Per-job manifests retain commands and hashes. '
              '`src/analysis/revalidate_extensions.py` processes complete raw records one epoch at a time; compressed files avoid multi-gigabyte intermediates. '
              '`results/revalidated-2026-10-25/analysis/` holds machine-readable granularity, turnover, placement and cost sensitivity results.', '',
              'Shutdown stops running work. Re-running a lane preserves completed jobs; a partially completed benchmark must restart. '
              'Pin has no mid-run checkpoint. The simulator lane can use the separately validated process-snapshot supervisor; '
              'see [checkpointing](checkpointing.md). Old interrupted jobs without snapshots restart.', '',
              '## Simulator Figure 4 comparison','',
              'The [validated simulator comparison](simulator-figure4.md) reports each port separately and excludes interrupted runs. '
              'Its three-row figure contrasts digitized M5, the Pin baseline and accepted CXL bridge requests; '
              'the streams and inputs are not identical.', '']
    path=ROOT/'docs/revalidation-2026-10-25.md';tmp=path.with_suffix('.tmp');tmp.write_text('\n'.join(lines));tmp.replace(path)
    sim=OUT/'sim-status.json'
    if sim.exists() and any(j.get('status')=='complete' for j in json.loads(sim.read_text())['jobs'].values()):
        subprocess.run([sys.executable,str(ROOT/'src/analysis/compare_simulator_m5.py')],check=True)

if __name__=='__main__':main()
