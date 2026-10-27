#!/usr/bin/env python3
"""Plot simultaneous access, demand-fill and total-traffic page sparsity.

Only manifests marked complete are eligible. A small fitted error is not used as
a selection criterion. Whole ROI and predeclared reference windows are both shown.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import hotskew as H

STREAMS = ("accesses", "fills", "traffic")
LABELS = ("Demand accesses", "Modeled demand misses", "Misses + dirty writebacks")
COLORS = ("#15806c", "#2866ad", "#ac4372")

def read_hist(path, scope, stream, population):
    path = Path(path)
    if not path.exists():
        path = path.with_name(path.name.replace('.paired.csv', '.paired-summary.csv'))
    hist = np.zeros(65, dtype=np.int64)
    seen = set()
    events = None
    with open(path) as f:
        for row in csv.DictReader(f):
            if (row["scope"], row["stream"], row["population"]) != (scope, stream, population):
                continue
            n = int(row["words"])
            if n in seen or not 0 <= n <= 64:
                raise ValueError(f"duplicate/invalid histogram bin: {path}")
            seen.add(n)
            hist[n] = int(row["pages"])
            if hist[n] < 0: raise ValueError("negative page count")
            if events is not None and events != int(row["events"]):
                raise ValueError("inconsistent event count")
            events = int(row["events"])
    if len(seen) != 65:
        raise ValueError(f"incomplete histogram: {path}, {scope}/{stream}/{population}")
    return hist, events

def cdf(hist):
    return np.cumsum(hist)/hist.sum() if hist.sum() else np.full(65, np.nan)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path("results/paired-v2"))
    ap.add_argument("--out", type=Path, default=Path("docs/assets"))
    ap.add_argument("--three-rows", action="store_true",
                    help="Show M5, accesses and demand misses only in the bar figure")
    ap.add_argument("--bars-only", action="store_true",
                    help="Generate only the grouped-bar figure")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    runs = []
    for name in ("bfs", "cc", "sssp", "bc", "pr", "tc"):
        prefix = args.results/f"gapbs-{name}"
        manifest = prefix.with_suffix(".manifest.json")
        if not manifest.exists(): continue
        meta = json.loads(manifest.read_text())
        if meta["status"] != "complete":
            print(f"EXCLUDE {name}: {meta['status']}")
            continue
        compact = prefix.with_suffix('.paired-summary.csv')
        runs.append((name, compact if compact.exists() else prefix.with_suffix(".paired.csv"), meta))
    if not runs: raise SystemExit("No completed paired runs")
    settings = {(m['graph_family'], m['graph_scale'], m['epoch_refs'],
                 m.get('epoch_traffic', 0), m['warm_setup'], m['threads']) for _, _, m in runs}
    if len(settings) != 1: raise ValueError("mixed experiment settings")
    family, scale, refs, traffic, warm, threads = next(iter(settings))
    graph_label = f'synthetic kron-{scale}' if family == 'synthetic Kronecker' else family
    window = traffic or refs
    window_label = 'modeled memory-event' if traffic else 'line-operand'
    rows = []
    # Preserve the paper's grouped-bar grammar as well as full-CDF diagnostics.
    bar_streams = STREAMS[:2] if args.three_rows else STREAMS
    bar_labels = LABELS[:2] if args.three_rows else LABELS
    panels = ((None, 'M5 Figure 4 (digitized published values)'), *zip(bar_streams, bar_labels))
    fig, axes = plt.subplots(len(panels), 1,
                             figsize=(10, 8) if args.three_rows else (12, 10),
                             sharex=True, sharey=True)
    colors = ('#2464a3', '#15998a', '#cf9e20', '#ae4678', '#666666')
    x = np.arange(len(runs))
    for row_id, (stream, label) in enumerate(panels):
        ax = axes[row_id]
        for i, n in enumerate(H.FIG4_N):
            values = []
            for name, path, _ in runs:
                if stream is None:
                    values.append(H.M5_FIGURE4[f'gapbs-{name}'][n])
                else:
                    hist, _ = read_hist(path, 'pooled', stream, 'own')
                    values.append(cdf(hist)[n])
            ax.bar(x+(i-2)*.15, values, width=.14, color=colors[i], label=f'N={n}')
        ax.set_title(label, loc='left', fontsize=11)
        ax.set_ylabel('CDF'); ax.set_ylim(0,1); ax.set_yticks([0,.5,1])
        ax.grid(axis='y', alpha=.15); ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    axes[-1].set_xticks(x, [name.upper() for name,_,_ in runs])
    fig.suptitle('Figure 4-style comparison: accesses and modeled misses', fontsize=16)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center',
               bbox_to_anchor=(.5,.952), ncol=5)
    fig.text(.5,.012, f'Local: {graph_label} / {threads} thread / 1 trial / '
             f'{window/1e6:g}M {window_label} windows.\n'
             'CDF: fraction of touched pages with at most N distinct 64B lines. '
             'Misses exclude dirty writebacks. Not an exact M5 reproduction.'
             if args.three_rows else
             f'Local: {graph_label} / {threads} thread / 1 trial / '
             f'{window/1e6:g}M {window_label} windows. Not an exact M5 reproduction.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.065 if args.three_rows else .035,1,.91))
    fig.savefig(args.out/'fig4_accesses_and_misses.png', dpi=180)
    plt.close(fig)
    if args.bars_only:
        print(f'Plotted {len(runs)} completed workloads: {args.out / "fig4_accesses_and_misses.png"}')
        return
    for scope in ("pooled", "whole"):
        fig, axes = plt.subplots(2, 3, figsize=(13, 7.2), sharex=True, sharey=True)
        for ax, (name, path, meta) in zip(axes.flat, runs):
            paper = H.M5_FIGURE4[f"gapbs-{name}"]
            for stream, label, color in zip(STREAMS, LABELS, COLORS):
                hist, events = read_hist(path, scope, stream, "own")
                values = cdf(hist)
                ax.plot(range(65), values, label=label, color=color, lw=1.8)
                for n in H.FIG4_N:
                    rows.append(dict(workload=name, scope=scope, population="own", stream=stream,
                                     n=n, cdf=values[n], paper=paper[n], delta=values[n]-paper[n],
                                     pages=int(hist.sum()), events=events))
            ax.scatter(list(paper), list(paper.values()), marker="x", color="#222222",
                       s=34, label="M5 digitized (device traffic)", zorder=6)
            ax.set_title(name.upper(), fontsize=12)
            ax.set_xticks([0, 4, 8, 16, 32, 48, 64])
            ax.set_ylim(-.02, 1.02)
            ax.grid(alpha=.18)
            ax.spines[["top", "right"]].set_visible(False)
        for ax in list(axes.flat)[len(runs):]: ax.set_visible(False)
        interval = f"{window/1e6:g}M {window_label} windows (pooled page-window observations)" if scope == "pooled" else "Whole timed kernel (one observation per touched page)"
        fig.suptitle("Page sparsity: accesses versus modeled misses", fontsize=17, y=.985)
        fig.text(.5, .932, interval, ha="center", fontsize=11)
        fig.supxlabel("N: distinct 64-byte lines within a 4 KiB page", y=.055)
        fig.supylabel("P(distinct lines <= N | page touched by this stream)", x=.013)
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=9, bbox_to_anchor=(.5,-.002))
        fig.text(.5, .892, f"Stock GAPBS / {graph_label} / {threads} thread / 1 trial / "
                 f"{'setup-warmed' if warm else 'cold-at-ROI'} model. Inputs differ from M5.",
                 ha="center", fontsize=9, color="#555555")
        fig.subplots_adjust(top=.84, bottom=.14, left=.075, right=.985, hspace=.30)
        fig.savefig(args.out/f"access_vs_misses_{scope}.png", dpi=180)
        plt.close(fig)

    # Use identical page populations to distinguish filtering from selection bias.
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.0), sharex=True, sharey=True)
    for ax, (name, path, _) in zip(axes.flat, runs):
        for stream, label, color in zip(STREAMS[:2], LABELS[:2], COLORS[:2]):
            hist, _ = read_hist(path, "pooled", stream, "fill_pages")
            ax.plot(range(65), cdf(hist), color=color, label=label, lw=2)
        ax.set_title(name.upper()); ax.grid(alpha=.18); ax.set_ylim(-.02,1.02)
        ax.set_xticks([0,16,32,48,64]); ax.spines[["top","right"]].set_visible(False)
    for ax in list(axes.flat)[len(runs):]: ax.set_visible(False)
    fig.suptitle("Same pages, same windows: access coverage and miss coverage", fontsize=16)
    fig.supxlabel("N: distinct 64-byte lines within a 4 KiB page", y=.06)
    fig.supylabel("CDF over pages with at least one demand miss")
    fig.legend(*axes.flat[0].get_legend_handles_labels(), loc="lower center", ncol=2)
    fig.tight_layout(rect=(.015,.10,1,.94))
    fig.savefig(args.out/"access_vs_misses_common.png", dpi=180)
    plt.close(fig)
    target = args.results/"comparison.csv"
    with target.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f"Plotted {len(runs)} completed workloads; wrote {target}")
    for name, _, _ in runs:
        v = [r for r in rows if r['workload']==name and r['scope']=='pooled' and r['n']==16]
        print(name, " ".join(f"{r['stream']} P16={r['cdf']:.4f}" for r in v))

if __name__ == "__main__": main()
