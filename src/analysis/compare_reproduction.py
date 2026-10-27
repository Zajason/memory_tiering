#!/usr/bin/env python3
"""Report all cells of the predeclared graph/window comparison, never best-fit cells."""
import csv
import json
import tempfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import hotskew as H
from plot_paired import read_hist, cdf

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ('kron', 'refs10', ROOT/'results/paired-v2'),
    ('kron', 'traffic10', ROOT/'results/matched-family/kron-traffic10'),
    ('gplus', 'refs10', ROOT/'results/matched-family/gplus-refs10'),
    ('gplus', 'traffic10', ROOT/'results/matched-family/gplus-traffic10'),
)


def checked_histograms(directory, name):
    stem = directory/f'gapbs-{name}'
    manifest = json.loads(stem.with_suffix('.manifest.json').read_text())
    if manifest['status'] != 'complete':
        raise ValueError(f'Incomplete run: {stem}')
    compact = stem.with_suffix('.paired-summary.csv')
    raw = stem.with_suffix('.paired.csv')
    path = compact if compact.exists() else raw
    data = {}
    events = {}
    for scope in ('pooled', 'whole'):
        for stream in ('accesses', 'fills', 'traffic'):
            hist, count = read_hist(path, scope, stream, 'own')
            if not hist.sum(): raise ValueError(f'Empty {stem}/{scope}/{stream}')
            data[scope, stream] = hist
            if stream in events and count != events[stream]:
                raise ValueError('Pooled and whole event counts disagree')
            events[stream] = count
    summary = H.load_summary(stem.with_suffix('.summary.txt'))
    assert events['accesses'] == int(summary['mem_refs_profiled'])
    assert events['traffic'] == int(summary['dram_accesses'])
    assert events['fills'] <= events['traffic'] <= events['accesses'] * 3
    assert np.array_equal(data['pooled', 'traffic'], summary['_unique_hist'])
    access, _ = read_hist(path, 'pooled', 'accesses', 'fill_pages')
    fills, _ = read_hist(path, 'pooled', 'fills', 'fill_pages')
    assert access.sum() == fills.sum()
    assert np.all(cdf(access) <= cdf(fills) + 1e-12)
    if not manifest['warm_setup']:
        for stream in ('fills', 'traffic'):
            assert np.array_equal(data['whole', 'accesses'], data['whole', stream])
    if not compact.exists():
        # Publish only a closed, complete summary, including concurrent readers.
        with tempfile.TemporaryDirectory(prefix='.paired-summary-', dir=compact.parent) as temp:
            pending = Path(temp)/compact.name
            with raw.open() as source, pending.open('w') as target:
                reader = csv.DictReader(source)
                writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
                writer.writeheader()
                writer.writerows(r for r in reader if r['scope'] != 'epoch')
            pending.replace(compact)
    print(f'PASS {stem.relative_to(ROOT)}: completion, totals, populations, unions')
    return data, events, manifest


def main():
    output = ROOT/'results/matched-family'
    output.mkdir(exist_ok=True)
    all_data = {}
    rows = []
    score_rows = []
    for graph, clock, directory in CASES:
        for name in ('bc', 'sssp'):
            data, events, meta = checked_histograms(directory, name)
            all_data[graph, clock, name] = data
            assert meta['threads'] == 1 and meta['trials'] == 1 and not meta['warm_setup']
            assert meta['graph_family'] == ('synthetic Kronecker' if graph == 'kron'
                                            else 'Google+ IMC12 snapshot 1')
            if clock == 'refs10': assert meta['epoch_refs'] == 10000000
            else: assert meta['epoch_traffic'] == 10000000 and meta['epoch_refs'] == 0
            paper = H.M5_FIGURE4[f'gapbs-{name}']
            for (scope, stream), hist in data.items():
                values = cdf(hist)
                errors = [abs(values[n]-paper[n]) for n in H.FIG4_N]
                score_rows.append(dict(graph=graph, clock=clock, workload=name,
                                       scope=scope, stream=stream,
                                       max_abs_error=float(max(errors)),
                                       mean_abs_error=float(np.mean(errors)),
                                       p16=float(values[16]), events=events[stream],
                                       page_observations=int(hist.sum())))
                for n in H.FIG4_N:
                    rows.append(dict(graph=graph, clock=clock, workload=name,
                                     scope=scope, stream=stream, n=n,
                                     cdf=float(values[n]), paper=paper[n],
                                     delta=float(values[n]-paper[n])))
    for filename, records in [('comparison.csv', rows), ('scores.csv', score_rows)]:
        with (output/filename).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    source = ROOT/'workloads/gapbs/graphs/gplus-snapshot1.source.json'
    if source.exists():
        (output/'gplus-snapshot1.source.json').write_text(source.read_text())

    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
    for row, name in enumerate(('bc', 'sssp')):
        for col, (clock, scope, title) in enumerate((
            ('refs10', 'pooled', '10M raw-reference windows'),
            ('traffic10', 'pooled', '10M memory-event windows'),
            ('traffic10', 'whole', 'Whole timed kernel'),
        )):
            ax = axes[row, col]
            for graph, label, color in (('kron', 'Synthetic kron-23', '#2866ad'),
                                        ('gplus', 'Google+ snapshot 1', '#15806c')):
                values = cdf(all_data[graph, clock, name][scope, 'traffic'])
                ax.plot(range(65), values, label=label, color=color, linewidth=2)
            paper = H.M5_FIGURE4[f'gapbs-{name}']
            ax.scatter(list(paper), list(paper.values()), marker='x', color='#222222',
                       label='M5 digitized reference', zorder=4)
            ax.set_title(f'{name.upper()}: {title}', fontsize=11)
            ax.set_xticks([0, 16, 32, 48, 64]); ax.set_ylim(-.02, 1.02)
            ax.grid(alpha=.18); ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Dataset and window controls: modeled misses + writebacks', fontsize=15)
    fig.supxlabel('N: distinct 64-byte lines per 4 KiB page', y=.075)
    fig.supylabel('P(distinct lines <= N | page touched)', x=.01)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), ncol=3, loc='lower center',
               bbox_to_anchor=(.5, .025))
    fig.text(.5, .012, 'One thread, one trial, cold 40 MiB LLC model. Google+ is a published temporal subset, not M5\'s exact input.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(.025, .11, 1, .94))
    target = ROOT/'docs/assets/reproduction_controls.png'
    fig.savefig(target, dpi=180)
    print('Saved', target)
    for row in score_rows:
        if row['scope'] == 'pooled' and row['stream'] == 'traffic':
            print(f"{row['workload']:4s} {row['graph']:6s} {row['clock']:10s} "
                  f"P16={row['p16']:.4f} max5={row['max_abs_error']:.4f} "
                  f"mean5={row['mean_abs_error']:.4f}")


if __name__ == '__main__':
    main()
