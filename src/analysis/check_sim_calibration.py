"""Verify the drained linear-sweep invariant independently of probe means."""
import argparse
import json
from pathlib import Path
import hotskew as H

def check(directory):
    summaries=[H.load_summary(str(directory/name)) for name in ['hotskew','hotskew-controller']]
    totals=[]
    for s in summaries:
        hist=s['_unique_hist']
        n=int(s['dram_accesses'].split()[0]);pages=int(s['page_observations'].split()[0])
        assert n>0 and pages==int(hist.sum())
        assert n==sum(i*int(count) for i,count in enumerate(hist)), 'retry duplication or missing coverage'
        totals.append(n)
    assert totals[0]==totals[1], 'accepted requests not drained to controller'
    assert (summaries[0]['_unique_hist']==summaries[1]['_unique_hist']).all()
    return dict(status='validated',accepted_line_requests=totals[0],
                page_observations=int(summaries[0]['page_observations'].split()[0]),
                checks=['linear event/unique-line identity','bridge/controller count equality after drain','matching histograms'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--out',type=Path)
    a=ap.parse_args();r=check(a.directory);print(json.dumps(r,indent=2))
    if a.out:a.out.write_text(json.dumps(r,indent=2)+'\n')
