"""Small verified-data snapshot for the Greek research presentation."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    records=[]
    for kind,path in [('baseline',ROOT/'results/uniform-traffic10/scores.csv'),
                      ('real-input',ROOT/'results/fidelity-2026-10-27/scores.csv')]:
        with path.open() as f:
            for r in csv.DictReader(f):
                if kind=='real-input' and not r['case'].startswith('dataset'):continue
                if r['stream']=='fills' and r['scope']=='pooled':
                    records.append(dict(kind=kind,workload=r['workload'],error_pp=100*float(r['max_abs_error'])))
    stage=ROOT/'results/fidelity-stage2-2026-10-28/campaign.json'
    state=json.loads(stage.read_text()) if stage.exists() else {'jobs':{},'status':'not started'}
    sim=json.loads((ROOT/'results/revalidated-2026-10-25/sim-status.json').read_text())
    repetition=[]
    footprint_fill_error=None
    with (ROOT/'results/fidelity-stage2-2026-10-28/scores.csv').open() as f:
        for r in csv.DictReader(f):
            if r['case']=='footprint-tc' and r['stream']=='fills' and r['scope']=='pooled':
                footprint_fill_error=100*float(r['max_abs_error'])
            if r['case'].startswith('phase1/trials200-pool-') and r['stream']=='fills':
                repetition.append(dict(workload=r['workload'],scope=r['scope'],
                                       error_pp=100*float(r['max_abs_error'])))
    data=dict(scores=records,repetition=repetition,stage2=dict(status=state['status'],
        completed=sum(j['status']=='complete' for j in state['jobs'].values()),
        total=len(state['jobs']) or 21,current=state.get('current')),
        simulator={k:v['status'] for k,v in sim['jobs'].items()},
        sources=['results/fidelity-2026-10-27/scores.csv','results/revalidated-2026-10-25/sim-comparison/sources.json'])
    footprint=ROOT/'results/fidelity-stage2-2026-10-28/tc-footprint.json'
    if footprint.exists():
        selected=json.loads(footprint.read_text())
        data['tc_footprint']=dict(rss_gb=selected['native']['peak_rss_kib']*1024/1e9,
                                  target_gb=selected['target_bytes']/1e9,
                                  within_tolerance=selected['within_10_percent'])
        if footprint_fill_error is not None:
            data['tc_footprint']['pooled_fill_error_pp']=footprint_fill_error
    (ROOT/'presentation/data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
