#!/usr/bin/env python3
"""plot_figures.py -- reproduce M5's Figures 4 and 10 from hotskew output.

    python3 src/analysis/plot_figures.py [--results results] [--config spr-20t]

Produces, in results/figures/:

    fig4_sparsity.png      P(page has at most N unique 64 B words), our runs
    fig4_vs_paper.png      the same, next to the values read off M5's Figure 4
    fig10_page_access.png  distribution of access counts per 4 KB page
    density_cdf.png        full CDF of words-touched-per-page, all benchmarks
    hot_vs_all.png         sparsity of the hottest pages vs all pages

The last one is not in the paper. It exists because it changes the conclusion: for
the graph kernels the hottest pages turn out to be dense, and sparsity lives in the
lukewarm tail. A policy that only ever migrates the top-K pages therefore sees a
very different distribution from the one Figure 4 plots.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

# Order benchmarks the way M5's Figure 4 does, so the two read the same way.
BENCH_ORDER = [
    "liblinear",
    "gapbs-bc",
    "gapbs-bfs",
    "gapbs-cc",
    "gapbs-pr",
    "gapbs-sssp",
    "gapbs-tc",
    "redis",
]
LABEL = {
    "liblinear": "lib.",
    "gapbs-bc": "bc",
    "gapbs-bfs": "bfs",
    "gapbs-cc": "cc",
    "gapbs-pr": "pr",
    "gapbs-sssp": "sssp",
    "gapbs-tc": "tc",
    "redis": "redis",
}
# Matches the paper's series colours closely enough to compare at a glance.
SERIES_COLOR = {4: "#4472c4", 8: "#c0504d", 16: "#9bbb59", 32: "#8064a2", 48: "#4bacc6"}


def discover(results_dir: str, config: str) -> dict[str, str]:
    """Map benchmark -> summary path for everything that produced usable data."""
    d = os.path.join(results_dir, config)
    found = {}
    if not os.path.isdir(d):
        return found
    for name in sorted(os.listdir(d)):
        if not name.endswith(".summary.txt"):
            continue
        bench = name[: -len(".summary.txt")]
        path = os.path.join(d, name)
        meta = H.load_summary(path)
        if meta.get("STATUS") == "NO DATA":
            print(f"  skipping {bench}: run produced no data", file=sys.stderr)
            continue
        found[bench] = path
    return found


def _grouped_bars(ax, benches, values, labels, title, ylabel="CDF"):
    """values[bench][N] -> height. Draws M5's Figure 4 layout."""
    x = np.arange(len(benches))
    width = 0.16
    for i, n in enumerate(H.FIG4_N):
        heights = [values[b].get(n, np.nan) for b in benches]
        ax.bar(x + (i - 2) * width, heights, width, label=str(n), color=SERIES_COLOR[n])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=90)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)


def fig4(found, outdir):
    benches = [b for b in BENCH_ORDER if b in found] + [
        b for b in found if b not in BENCH_ORDER
    ]
    if not benches:
        print("  no benchmarks to plot", file=sys.stderr)
        return
    vals = {b: H.figure4_from_summary(found[b]) for b in benches}
    labels = [LABEL.get(b, b) for b in benches]

    fig, ax = plt.subplots(figsize=(max(5, 0.7 * len(benches) + 2), 3.4))
    _grouped_bars(
        ax, benches, vals, labels,
        "P(4 KB page with at most $N$ unique 64 B words accessed)",
    )
    ax.legend(title="N", ncol=5, fontsize=8, title_fontsize=8, loc="upper left")
    fig.tight_layout()
    p = os.path.join(outdir, "fig4_sparsity.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {p}")

    # Side by side with the paper.
    paired = [b for b in benches if b in H.M5_FIGURE4]
    if not paired:
        return
    fig, axes = plt.subplots(1, 2, figsize=(max(8, 1.1 * len(paired) + 3), 3.6), sharey=True)
    _grouped_bars(axes[0], paired, vals, [LABEL.get(b, b) for b in paired],
                  "This work (Pin + modelled cache)")
    _grouped_bars(axes[1], paired, {b: H.M5_FIGURE4[b] for b in paired},
                  [LABEL.get(b, b) for b in paired],
                  "M5 Figure 4 (FPGA WAC, digitised)")
    axes[0].legend(title="N", ncol=5, fontsize=8, title_fontsize=8, loc="upper left")
    fig.tight_layout()
    p = os.path.join(outdir, "fig4_vs_paper.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {p}")


def fig10(found, outdir):
    """Distribution of access counts per 4 KB page (M5 Figure 10)."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    plotted = 0
    for b in [x for x in BENCH_ORDER if x in found] + [
        x for x in found if x not in BENCH_ORDER
    ]:
        hist = H.load_summary(found[b])["_access_hist"]
        if not hist:
            continue
        buckets = sorted(hist)
        counts = np.array([hist[k] for k in buckets], dtype=float)
        total = counts.sum()
        if total == 0:
            continue
        # Plot as a survival curve: fraction of pages with >= 2^b accesses. Easier
        # to read across benchmarks whose footprints differ by orders of magnitude.
        surv = 1.0 - np.cumsum(counts) / total + counts / total
        ax.step([2.0 ** k for k in buckets], surv, where="post", label=LABEL.get(b, b))
        plotted += 1
    if not plotted:
        plt.close(fig)
        return
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("DRAM accesses to a 4 KB page in one epoch")
    ax.set_ylabel("fraction of pages with at least this many")
    ax.set_title("Distribution of access counts per 4 KB page")
    ax.grid(alpha=0.3, linewidth=0.5)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    p = os.path.join(outdir, "fig10_page_access.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {p}")


def density_cdf(found, outdir):
    """Full CDF of words-touched-per-page. Figure 4 is five points off this curve."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for b in [x for x in BENCH_ORDER if x in found] + [
        x for x in found if x not in BENCH_ORDER
    ]:
        hist = H.load_summary(found[b])["_unique_hist"]
        total = hist.sum()
        if total == 0:
            continue
        ax.plot(np.arange(65), np.cumsum(hist) / total, label=LABEL.get(b, b), lw=1.6)
    for n in H.FIG4_N:
        ax.axvline(n, color="0.8", lw=0.7, zorder=0)
    ax.set_xlabel("unique 64 B words touched in a 4 KB page (of 64)")
    ax.set_ylabel("CDF over pages")
    ax.set_xlim(0, 64)
    ax.set_ylim(0, 1)
    ax.set_title("Access density within a 4 KB page")
    ax.grid(alpha=0.3, linewidth=0.5)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    p = os.path.join(outdir, "density_cdf.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {p}")


def hot_vs_all(results_dir, config, outdir, top_k=10000):
    """Sparsity of the top-K hottest pages vs the whole population.

    Needs .pages.bin. This is the plot that qualifies the headline claim: if the
    pages a policy would actually migrate are dense, sub-page tracking buys little
    for that workload, whatever the population-wide number says.
    """
    d = os.path.join(results_dir, config)
    rows = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".pages.bin"):
            continue
        bench = name[: -len(".pages.bin")]
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        run = H.load_pages(path, tag=bench)
        rows.append((bench, run.figure4_cdf()[16], run.figure4_cdf(top_k=top_k)[16]))
    if not rows:
        return
    rows.sort(key=lambda r: BENCH_ORDER.index(r[0]) if r[0] in BENCH_ORDER else 99)

    labels = [LABEL.get(r[0], r[0]) for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(max(4.5, 0.8 * len(rows) + 2), 3.4))
    ax.bar(x - 0.2, [r[1] for r in rows], 0.4, label="all touched pages", color="#4472c4")
    ax.bar(x + 0.2, [r[2] for r in rows], 0.4, label=f"top-{top_k} hottest", color="#c0504d")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=90)
    ax.set_ylabel("P(page has $\\leq$ 16 of 64 words touched)")
    ax.set_ylim(0, 1)
    ax.set_title("Sparsity: whole population vs the pages a policy would migrate")
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = os.path.join(outdir, "hot_vs_all.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print(f"  {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--top-k", type=int, default=10000)
    args = ap.parse_args()

    outdir = args.outdir or os.path.join(args.results, "figures")
    os.makedirs(outdir, exist_ok=True)

    found = discover(args.results, args.config)
    if not found:
        print(f"no results under {args.results}/{args.config}", file=sys.stderr)
        return 1
    print(f"benchmarks: {', '.join(sorted(found))}")

    fig4(found, outdir)
    fig10(found, outdir)
    density_cdf(found, outdir)
    hot_vs_all(args.results, args.config, outdir, args.top_k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
