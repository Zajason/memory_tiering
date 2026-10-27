#!/usr/bin/env python3
"""Check paired campaign invariants and retain compact, versionable histograms."""
import csv
import json
from pathlib import Path
import numpy as np
import hotskew as H
from plot_paired import read_hist, cdf

ROOT = Path(__file__).resolve().parents[2]

def main():
    results = []
    for directory in ('paired-v2', 'paired-v2-9way', 'paired-v2-warm'):
        for manifest in sorted((ROOT/'results'/directory).glob('*.manifest.json')):
            meta = json.loads(manifest.read_text())
            if meta['status'] != 'complete': continue
            stem = manifest.name.removesuffix('.manifest.json')
            path = manifest.parent/(stem+'.paired.csv')
            summary = H.load_summary(manifest.parent/(stem+'.summary.txt'))
            observed = {}
            for stream in ('accesses', 'fills', 'traffic'):
                hist, events = read_hist(path, 'pooled', stream, 'own')
                whole, whole_events = read_hist(path, 'whole', stream, 'own')
                assert events == whole_events
                assert int(whole.sum()) <= int(hist.sum())
                observed[stream] = hist, events, whole
                result = dict(config=directory, workload=stem, stream=stream,
                              events=events, page_windows=int(hist.sum()),
                              whole_pages=int(whole.sum()),
                              p16=float(cdf(hist)[16]), whole_p16=float(cdf(whole)[16]),
                              max_error_5points=max(abs(cdf(hist)[n]-H.M5_FIGURE4[stem][n]) for n in H.FIG4_N))
                results.append(result)
            assert observed['accesses'][1] == int(summary['mem_refs_profiled'])
            assert observed['traffic'][1] == int(summary['dram_accesses'])
            assert np.array_equal(observed['traffic'][0], summary['_unique_hist'])
            access, _ = read_hist(path, 'pooled', 'accesses', 'fill_pages')
            fills, _ = read_hist(path, 'pooled', 'fills', 'fill_pages')
            assert access.sum() == fills.sum()
            assert np.all(cdf(access) <= cdf(fills) + 1e-12)
            if not meta['warm_setup']:
                assert np.array_equal(observed['accesses'][2], observed['fills'][2])
                assert np.array_equal(observed['accesses'][2], observed['traffic'][2])
            # Only pooled/whole rows are needed to regenerate the published plots.
            compact = manifest.parent/(stem+'.paired-summary.csv')
            with path.open() as source, compact.open('w') as target:
                reader = csv.DictReader(source)
                writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
                writer.writeheader()
                writer.writerows(r for r in reader if r['scope'] != 'epoch')
            print(f'PASS {directory}/{stem}: totals, populations, CDF ordering, whole-ROI union')
    out = ROOT/'results/paired-v2/audit.csv'
    with out.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader(); writer.writerows(results)
    print('Saved', out)
    for kind in ('paired-v2-9way','paired-v2-warm'):
        for row in results:
            if row['config'] != kind or row['stream'] != 'traffic': continue
            name = row['workload']
            a, _ = read_hist(ROOT/'results/paired-v2'/f'{name}.paired.csv','pooled','traffic','own')
            b, _ = read_hist(ROOT/'results'/kind/f'{name}.paired.csv','pooled','traffic','own')
            print(f'{kind} {name}: max full-CDF change={np.max(np.abs(cdf(a)-cdf(b))):.6f}')

if __name__ == '__main__': main()
