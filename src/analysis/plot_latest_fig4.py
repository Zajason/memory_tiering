#!/usr/bin/env python3
"""Six-workload comparison with a uniform, predeclared memory-event window."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import hotskew as H
from plot_paired import cdf, read_hist
from compare_reproduction import checked_histograms

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('bfs', 'cc', 'sssp', 'bc', 'pr', 'tc')


def preflight(root, all_synthetic=False):
    """Reject mixed protocols before reading histograms or writing figures."""
    sources = {}
    for name in NAMES:
        updated = name in ('bc', 'sssp') and not all_synthetic
        directory = 'matched-family/gplus-traffic10' if updated else 'matched-family/kron-traffic10'
        prefix = root/'results'/directory/f'gapbs-{name}'
        meta = json.loads(prefix.with_suffix('.manifest.json').read_text())
        if meta['status'] != 'complete' or meta.get('returncode') != 0:
            raise ValueError(f'Incomplete run: {prefix}')
        expected = ('Google+ IMC12 snapshot 1', 0, 10000000) if updated else (
            'synthetic Kronecker', 0, 10000000)
        actual = (meta['graph_family'], meta['epoch_refs'], meta.get('epoch_traffic', 0))
        if actual != expected or meta['threads'] != 1 or meta['trials'] != 1:
            raise ValueError(f'Caption would misdescribe {prefix}')
        if not updated and meta['graph_scale'] != 23:
            raise ValueError('Expected kron-23')
        command = meta['command']
        pin_command = command[:command.index('--')]
        for knob, value in (('-l3_kb', '40960'), ('-l3_assoc', '10'),
                            ('-paired', '1'), ('-epoch_refs', '0'),
                            ('-epoch', '10'), ('-max_epochs', '0'),
                            ('-warm_outside_roi', '0'),
                            ('-roi_begin', 'hotskew_roi_begin'),
                            ('-roi_end', 'hotskew_roi_end')):
            if (pin_command.count(knob) != 1 or
                    pin_command[pin_command.index(knob)+1] != value):
                raise ValueError(f'Unexpected {knob}: {prefix}')
        if meta['warm_setup']:
            raise ValueError('Expected cold-at-ROI caches')
        sources[name] = dict(manifest=str(prefix.with_suffix('.manifest.json').relative_to(root)),
                             **meta)
    if len({m['tool_sha256'] for m in sources.values()}) != 1:
        raise ValueError('Mixed profiler binaries')
    return sources


def check_reference(before, current):
    """Keep older path/size evidence distinct from execution-time input hashes."""
    for key in ('input', 'input_bytes', 'executable_sha256', 'threads', 'trials',
                'warm_setup', 'graph_family', 'graph_scale', 'roi'):
        if before[key] != current[key]:
            raise ValueError(f'Mismatched reference-window control: {key}')
    if (before['status'] != 'complete' or before.get('returncode') != 0
            or before['epoch_refs'] != 10000000 or before.get('epoch_traffic', 0) != 0):
        raise ValueError('Incomplete or wrong-clock reference-window control')
    for knob in ('-l3_kb', '-l3_assoc', '-max_epochs', '-warm_outside_roi',
                 '-roi_begin', '-roi_end'):
        old_cmd = before['command'][:before['command'].index('--')]
        new_cmd = current['command'][:current['command'].index('--')]
        if (old_cmd.count(knob) != 1 or
                old_cmd[old_cmd.index(knob)+1] != new_cmd[new_cmd.index(knob)+1]):
            raise ValueError(f'Mismatched reference-window control: {knob}')
    if 'input_sha256' in before:
        if before['input_sha256'] != current['input_sha256']:
            raise ValueError('Reference-window input hash mismatch')
        return 'sha256 matched'
    return 'path and size matched; baseline input hash not recorded'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--all-synthetic', action='store_true',
                    help='Use kron-23 for BC/SSSP too, as an input-controlled baseline')
    args = ap.parse_args()
    sources = preflight(ROOT, args.all_synthetic)
    data = {}
    scores = []
    points = []
    window_controls = []
    for name, meta in sources.items():
        directory = (ROOT/meta['manifest']).parent
        histograms, events, _ = checked_histograms(directory, name)
        paper = H.M5_FIGURE4[f'gapbs-{name}']
        for (scope, stream), hist in histograms.items():
            values = cdf(hist)
            if scope == 'pooled': data[name, stream] = values
            errors = [abs(values[n]-paper[n]) for n in H.FIG4_N]
            scores.append(dict(workload=name, scope=scope, stream=stream,
                               max_abs_error=float(max(errors)),
                               mean_abs_error=float(np.mean(errors)),
                               p16=float(values[16]), events=events[stream],
                               page_observations=int(hist.sum())))
            for n in H.FIG4_N:
                points.append(dict(workload=name, scope=scope, stream=stream,
                                   n=n, cdf=float(values[n]), paper=paper[n]))
        before_dir = ROOT/'results'/('matched-family/gplus-refs10'
                     if meta['graph_family'].startswith('Google+') else 'paired-v2')
        before_meta = json.loads((before_dir/f'gapbs-{name}.manifest.json').read_text())
        input_evidence = check_reference(before_meta, meta)
        for stream in ('accesses', 'fills', 'traffic'):
            before, before_events = read_hist(before_dir/f'gapbs-{name}.paired-summary.csv',
                                              'pooled', stream, 'own')
            old = cdf(before)
            new = data[name, stream]
            window_controls.append(dict(workload=name, stream=stream,
                graph=meta['graph_family'],
                raw_window_max_error=float(max(abs(old[n]-paper[n]) for n in H.FIG4_N)),
                memory_window_max_error=float(max(abs(new[n]-paper[n]) for n in H.FIG4_N)),
                raw_window_events=before_events, memory_window_events=events[stream],
                baseline_input_evidence=input_evidence,
                baseline_tool_sha256=before_meta['tool_sha256'],
                current_tool_sha256=meta['tool_sha256']))

    result_dir = ROOT/'results'/('uniform-kron-traffic10' if args.all_synthetic else 'uniform-traffic10')
    result_dir.mkdir(exist_ok=True)
    for filename, records in (('scores.csv', scores), ('comparison.csv', points),
                               ('window-controls.csv', window_controls)):
        with (result_dir/filename).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    (result_dir/'sources.json').write_text(json.dumps(sources, indent=2)+'\n')

    colors = ('#2464a3', '#15998a', '#cf9e20', '#ae4678', '#666666')
    panels = ((None, 'M5 Figure 4 (digitized published values)'),
              ('accesses', 'Our demand accesses'),
              ('fills', 'Our modeled demand misses (excluding dirty writebacks)'))
    fig, axes = plt.subplots(3, 1, figsize=(13, 8.5), sharex=True, sharey=True)
    x = np.arange(len(NAMES))
    for ax, (stream, title) in zip(axes, panels):
        for i, n in enumerate(H.FIG4_N):
            values = [H.M5_FIGURE4[f'gapbs-{name}'][n] if stream is None
                      else data[name, stream][n] for name in NAMES]
            ax.bar(x+(i-2)*.15, values, width=.14, color=colors[i], label=f'N={n}')
        ax.set_title(title, loc='left', fontsize=11)
        ax.set_ylabel('CDF'); ax.set_ylim(0, 1); ax.set_yticks([0, .5, 1])
        ax.grid(axis='y', alpha=.15); ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_xticks(x, [n.upper()+('*' if n in ('bc', 'sssp') and not args.all_synthetic else '') for n in NAMES])
        ax.tick_params(axis='x', labelbottom=True)
    fig.suptitle('M5 versus our measurements: uniform memory-event windows', fontsize=16, y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center',
               bbox_to_anchor=(.5, .95), ncol=5)
    fig.text(.5, .89, 'Each bar: fraction of page observations with at most N distinct '
             '64B lines per 4KiB page.', ha='center', fontsize=10)
    inputs = ('All workloads: synthetic kron-23.' if args.all_synthetic else
              '* BC / SSSP: Google+ snapshot 1. Others: synthetic kron-23.')
    fig.text(.5, .045, 'Our measurements: 10M modeled memory-event windows. ' + inputs,
             ha='center', fontsize=10)
    fig.text(.5, .018, 'One thread / one trial. CDF over each stream\'s touched pages. '
             'Inputs and collection protocol still differ from M5.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(.01, .08, 1, .9))
    out = ROOT/'docs/assets'/('fig4_uniform_kron.png' if args.all_synthetic else 'fig4_uniform_full.png')
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(out)


if __name__ == '__main__':
    main()
