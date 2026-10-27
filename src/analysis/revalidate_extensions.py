"""Recompute extensions from complete raw records, one epoch at a time.

No historical CSV enters this analysis. Granularity describes virtual-address
grouping, not actual huge pages. Cost ratios are open-loop serial memory costs.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
import numpy as np
import hotskew as H
from granularity_sweep import sweep_records
from hotset_turnover import top_k_of_epoch
from causal_placement import candidates, choose


def epochs(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rb') as f:
        pending = np.empty(0, H.RECORD_DTYPE)
        previous = -1
        while True:
            data = f.read(H.RECORD_DTYPE.itemsize * 32768)
            if len(data) % H.RECORD_DTYPE.itemsize:
                raise ValueError('truncated record')
            block = np.frombuffer(data, dtype=H.RECORD_DTYPE)
            allr = np.concatenate((pending, block))
            if not len(allr): break
            boundaries = np.flatnonzero(allr['epoch'][1:] != allr['epoch'][:-1])+1
            start = 0
            for end in boundaries:
                rec = allr[start:end]
                if int(rec['epoch'][0]) != previous+1: raise ValueError('non-consecutive epochs')
                previous += 1
                yield rec
                start = end
            pending = allr[start:]
            if not data:
                if int(pending['epoch'][0]) != previous+1: raise ValueError('bad final epoch')
                yield pending
                break


def analyse(prefix):
    prefix = Path(prefix)
    summary = H.load_summary(str(prefix)+'.summary.txt')
    if summary.get('collection_status') != 'complete': raise ValueError('incomplete collection')
    if summary.get('pages_bin_capped', '').startswith('yes'): raise ValueError('capped records')
    raw = Path(str(prefix)+'.pages.bin')
    if not raw.exists(): raw = Path(str(raw)+'.gz')
    gran = {}
    turnover = {k: [] for k in [128,10000,128000]}
    placements = []
    resident = {}
    capacities = {}
    histogram = np.zeros(65, dtype=np.int64)
    observed = events = count = 0
    saturated = False
    prev = None
    for rec in epochs(raw):
        if len(np.unique(rec['page'])) != len(rec): raise ValueError('duplicate pages in epoch')
        words = H._popcount64(rec['mask'])
        if not np.array_equal(words, np.count_nonzero(rec['words'],axis=1)):
            raise ValueError('touched mask/word count disagreement')
        histogram += np.bincount(words, minlength=65)
        acc = (rec['reads']+rec['writes']).astype(np.int64)
        observed += len(rec); events += int(acc.sum()); count += 1
        sat = bool(np.any(rec['words'] == 65535)); saturated |= sat
        if not sat and not np.array_equal(rec['words'].sum(axis=1), acc):
            raise ValueError('word/page count disagreement')
        for key,v in sweep_records(rec).items():
            g = gran.setdefault(key, [0,0.,0.])
            g[0] += v['pages']; g[1] += v['pages']*v['mean_frac']; g[2] += v['pages']*v['p_le_25pct']
        if prev is None:
            capacities = {f:max(1,int(len(rec)*f)) for f in [.1,.25,.5]}
        else:
            for k,rows in turnover.items():
                pa=top_k_of_epoch(prev,k); pb=top_k_of_epoch(rec,k)
                sa,sb=set(pa.tolist()),set(pb.tolist())
                hit=float(acc[np.isin(rec['page'],pa)].sum())/acc.sum()
                oracle=float(acc[np.isin(rec['page'],pb)].sum())/acc.sum()
                rows.append(dict(retention=len(sa&sb)/len(sa),jaccard=len(sa&sb)/len(sa|sb),
                                 coverage=hit,oracle_coverage=oracle,events=int(acc.sum())))
            prev_sat = bool(np.any(prev['words']==65535))
            for fraction,capacity in capacities.items():
                selections = {'count-only':choose(prev['page'],(prev['reads']+prev['writes']).astype(float),capacity)}
                if not prev_sat: selections=candidates(prev,capacity)
                selections['oracle']=choose(rec['page'],acc,capacity)
                for policy,chosen in selections.items():
                    before=resident.get((fraction,policy),set())
                    new=len(chosen-before);resident[fraction,policy]=chosen
                    fast=int(acc[np.isin(rec['page'],list(chosen))].sum())
                    for mig in [0,1000,3000,10000,30000]:
                        cost=fast*100+(int(acc.sum())-fast)*220+new*mig
                        placements.append(dict(epoch=int(rec['epoch'][0]),fast_fraction=fraction,
                            capacity_pages=capacity,policy=policy,events=int(acc.sum()),fast_events=fast,
                            promotions=new,migration_ns=mig,serial_cost_ns=cost))
        prev=rec
    expected=lambda key:int(summary[key].split()[0])
    if observed!=expected('page_observations') or events!=expected('dram_accesses') or count!=expected('epochs'):
        raise ValueError('raw records do not cover the complete summary')
    if not np.array_equal(histogram,summary['_unique_hist']): raise ValueError('raw/summary CDF mismatch')
    model=[]
    for f in capacities:
        for policy in ['count-only','hpt-driven','hwt-driven','oracle']:
            for mig in [0,1000,3000,10000,30000]:
                rows=[r for r in placements if r['fast_fraction']==f and r['policy']==policy and r['migration_ns']==mig]
                if len(rows)!=max(0,count-1) or not rows: continue
                total=sum(r['events'] for r in rows); cost=sum(r['serial_cost_ns'] for r in rows)
                model.append(dict(fast_fraction=f,policy=policy,migration_ns=mig,capacity_pages=capacities[f],
                    capture=sum(r['fast_events'] for r in rows)/total,
                    mean_serial_cost_ns=cost/total,cost_ratio_vs_all_slow=total*220/cost,
                    promotions=sum(r['promotions'] for r in rows),evaluation_events=total))
    tv=[]
    for k,rows in turnover.items():
        if not rows:continue
        total=sum(r['events'] for r in rows)
        cov=sum(r['coverage']*r['events'] for r in rows)/total
        oracle=sum(r['oracle_coverage']*r['events'] for r in rows)/total
        tv.append(dict(k=k,transitions=len(rows),mean_retention=float(np.mean([r['retention'] for r in rows])),
                       traffic_weighted_coverage=cov,traffic_weighted_oracle=oracle,lag_ratio=cov/oracle))
    tracker=Path(str(prefix)+'.tracker.csv')
    tracker_rows=list(csv.DictReader(tracker.open())) if tracker.exists() else []
    for row in tracker_rows:
        for field in ['hpt_access_ratio','hwt_access_ratio']:
            if not 0<=float(row[field])<=1.000001: raise ValueError('invalid tracker ratio')
    return dict(prefix=str(prefix),status='validated',epochs=count,page_observations=observed,events=events,
        saturated_words=saturated,tracker_word_scores_valid=not saturated,tracker=tracker_rows,
        granularity=[dict(page_bytes=ps,word_bytes=ws,observations=g[0],mean_fraction=g[1]/g[0],
                          p_le_25pct=g[2]/g[0]) for (ps,ws),g in sorted(gran.items())],
        turnover=tv,placement_cost=model,assumptions=dict(fast_ns=100,slow_ns=220,
            meaning='serial memory cost only, not application speedup; promotions charged, no demotion cost or feedback',
            capacity='fixed from first-window footprint',granularity='virtual aligned grouping, not OS huge pages'))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('prefix',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); result=analyse(a.prefix)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(f"VALIDATED {a.prefix.name}: {result['epochs']} epochs, {result['events']} memory events",flush=True)

if __name__=='__main__':main()
