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
    data=dict(scores=records,stage2=dict(status=state['status'],
        completed=sum(j['status']=='complete' for j in state['jobs'].values()),
        total=len(state['jobs']) or 21,current=state.get('current')),
        simulator={k:v['status'] for k,v in sim['jobs'].items()},
        sources=['results/fidelity-2026-10-27/scores.csv','results/revalidated-2026-10-25/sim-comparison/sources.json'])
    (ROOT/'presentation/data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
