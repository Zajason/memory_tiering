#!/usr/bin/env python3
"""plot_readme.py -- the figures the README leads with.

    python3 src/analysis/plot_readme.py

Four panels, each answering one question:

  hero_validation.png   does the tool measure the truth?      (calibration)
  hero_fig4.png         does it reproduce M5's Figure 4?      (the target)
  hero_tracker.png      what does the hardware budget buy?    (deliverable 1)
  hero_failuremode.png  which failure mode actually binds?    (the new result)
  hero_speedup.png      what is any of it worth, in time?      (deliverable 3+)

Styled for a dark-or-light README on GitHub: transparent background, a palette that
stays legible in both, and no reliance on colour alone to distinguish series.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

OUT = "docs/assets"
# Readable on white and on GitHub's dark background.
INK = "#8b949e"
ACC = ["#58a6ff", "#f78166", "#3fb950", "#bc8cff", "#d29922"]
plt.rcParams.update({
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.edgecolor": INK,
    "axes.titlecolor": INK,
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.18,
    "grid.linewidth": 0.6,
})


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_axisbelow(True)


def fig_validation():
    """Analytic ground truth vs measured, across four orders of granularity."""
    strides = [4096, 1024, 256, 64]
    expected = [4096 // s for s in strides]
    measured = [1.000, 3.999, 15.996, 63.981]

    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    x = np.arange(len(strides))
    ax.bar(x - 0.2, expected, 0.4, label="analytic truth", color=ACC[0])
    ax.bar(x + 0.2, measured, 0.4, label="measured", color=ACC[1])
    for i, (e, m) in enumerate(zip(expected, measured)):
        ax.text(i, max(e, m) * 1.35, f"{m:g}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"stride\n{s} B" for s in strides])
    ax.set_yscale("log")
    ax.set_ylim(0.5, 200)
    ax.set_ylabel("unique 64 B words per 4 KB page")
    ax.set_title("Calibration: exact across four orders of granularity", fontweight="bold")
    ax.legend(frameon=False, fontsize=8)
    style(ax)
    fig.tight_layout()
    p = f"{OUT}/hero_validation.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def fig4_vs_paper():
    """Ours vs M5's published Figure 4, all seven reproduced workloads."""
    order = ["gapbs-pr", "gapbs-tc", "gapbs-bfs", "gapbs-cc", "gapbs-bc",
             "gapbs-sssp", "redis"]
    label = {"gapbs-pr": "pr", "gapbs-tc": "tc", "gapbs-bfs": "bfs", "gapbs-cc": "cc",
             "gapbs-bc": "bc", "gapbs-sssp": "sssp", "redis": "redis"}
    paths = {b: f"results/spr-20t-ul/{b}.summary.txt" for b in order if b != "redis"}
    paths["redis"] = "results/spr-1t/redis-ycsba.summary.txt"
    m5key = dict(redis="redis", **{b: b for b in order if b != "redis"})

    benches, ours, theirs = [], [], []
    for b in order:
        p = paths.get(b)
        if not p or not os.path.exists(p):
            continue
        try:
            cdf = H.figure4_from_summary(p)
        except Exception:
            continue
        if np.isnan(cdf[16]):
            continue
        benches.append(label[b])
        ours.append(cdf[16])
        theirs.append(H.M5_FIGURE4[m5key[b]][16])
    if not benches:
        return None

    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    x = np.arange(len(benches))
    ax.bar(x - 0.21, ours, 0.42, label="this work (Pin, desktop)", color=ACC[0])
    ax.bar(x + 0.21, theirs, 0.42, label="M5 (Agilex 7 FPGA)", color=ACC[1])
    for i, (a, b_) in enumerate(zip(ours, theirs)):
        d = a - b_
        ax.text(i, max(a, b_) + 0.04, f"{d:+.2f}", ha="center", fontsize=7.5,
                color=ACC[2] if abs(d) < 0.1 else INK)
    ax.set_xticks(x)
    ax.set_xticklabels(benches)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("P(page has $\\leq$ 16 of 64 words touched)")
    ax.set_title("Reproducing M5 Figure 4 in software, on a desktop", fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style(ax)
    fig.tight_layout()
    p = f"{OUT}/hero_fig4.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def fig_tracker():
    """Deliverable 1: accuracy vs hardware budget for M5's HPT."""
    import csv
    d = "results/trackers"
    if not os.path.isdir(d):
        return None
    series = {}
    for name in sorted(os.listdir(d)):
        if not name.endswith(".summary.txt") or ".spacesaving" not in name:
            continue
        bench = name.split(".")[0].replace("gapbs-", "")
        pts = []
        with open(os.path.join(d, name)) as fh:
            seen = False
            for line in fh:
                if line.startswith("# N, hpt_access_ratio"):
                    seen = True
                    continue
                if seen:
                    if not line.strip() or line.startswith("#"):
                        break
                    f = line.strip().split(",")
                    if len(f) >= 6:
                        pts.append((int(f[0]), float(f[1]), int(f[5])))
        if pts:
            series[bench] = sorted(pts)
    if not series:
        return None

    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    for i, (b, pts) in enumerate(sorted(series.items())):
        n = [p[0] for p in pts]
        r = [p[1] for p in pts]
        ax.plot(n, r, "o-", label=b, color=ACC[i % len(ACC)], lw=1.8, ms=4.5)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("HPT entries $N$  (Space-Saving)")
    ax.set_ylabel("access-count ratio vs exact top-$K$")
    ax.set_ylim(0, 1.02)
    ax.axhline(1.0, color=INK, lw=0.7, ls=":")
    ax.set_title("What the hardware budget buys (M5 Figure 8)", fontweight="bold")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    style(ax)
    fig.tight_layout()
    p = f"{OUT}/hero_tracker.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def fig_failuremode():
    """Granularity vs timeliness, side by side, at a realistic fast-tier size."""
    # From docs/which-failure-mode.md, K=128,000 pages (512 MB).
    bench = ["tc", "bc", "bfs", "cc", "sssp", "pr"]
    staleness = [0.902, 0.850, 0.841, 0.830, 0.602, 0.381]
    # P(<=16 words) among the top-10k hottest pages -- the pages a policy migrates.
    sparsity_hot = [0.002, 0.000, 0.000, 0.000, 0.000, 0.000]

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    x = np.arange(len(bench))

    axes[0].bar(x, [1 - s for s in staleness], color=ACC[1])
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(bench)
    axes[0].set_ylabel("fraction of achievable benefit lost")
    axes[0].set_title("Timeliness (NeoMem)\ncost of one epoch of lag", fontsize=9.5,
                      fontweight="bold")
    for i, v in enumerate([1 - s for s in staleness]):
        axes[0].text(i, v + 0.015, f"{v:.0%}", ha="center", fontsize=7.5, color=INK)

    axes[1].bar(x, sparsity_hot, color=ACC[0])
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(bench)
    axes[1].set_title("Granularity (M5)\nsparsity among migrated pages", fontsize=9.5,
                      fontweight="bold")
    axes[1].text(len(bench) / 2 - 0.5, 0.32, "≈ 0 for every kernel:\nthe pages a policy"
                 "\nmigrates are dense", ha="center", fontsize=8.5, color=ACC[2])

    axes[0].set_ylim(0, 0.7)
    for a in axes:
        style(a)
    fig.suptitle("Which failure mode actually binds, on graph analytics",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    p = f"{OUT}/hero_failuremode.png"
    fig.savefig(p, dpi=190, transparent=True, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_speedup():
    """The closed-loop result: stall-time speedup, and where migration stops paying."""
    bench = ["bc", "tc", "cc", "bfs", "pr", "sssp"]
    count = [1.71, 1.54, 1.52, 1.45, 1.42, 1.41]
    oracle = [1.79, 1.60, 1.60, 1.56, 1.46, 1.60]
    mig_ns = [0, 1, 3, 10, 30]
    mig_sp = [1.665, 1.608, 1.505, 1.238, 0.835]

    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.2))

    x = np.arange(len(bench))
    axes[0].bar(x - 0.2, oracle, 0.4, label="oracle (bound)", color=ACC[3])
    axes[0].bar(x + 0.2, count, 0.4, label="HPT alone (realisable)", color=ACC[0])
    axes[0].axhline(2.2, color=ACC[2], ls="--", lw=1.2, label="all-local (2.2x)")
    axes[0].axhline(1.0, color=INK, lw=0.8)
    axes[0].set_xticks(x); axes[0].set_xticklabels(bench)
    axes[0].set_ylabel("memory stall-time speedup vs all-CXL")
    axes[0].set_ylim(0.9, 2.35)
    axes[0].set_title("Closing the loop: 1.50x geomean\n(61% of the achievable gap)",
                      fontsize=9.5, fontweight="bold")
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper right")

    axes[1].plot(mig_ns, mig_sp, "o-", color=ACC[1], lw=2, ms=5)
    axes[1].axhline(1.0, color=INK, lw=0.9, ls=":")
    axes[1].fill_between([0, 32], 0.7, 1.0, color=ACC[1], alpha=0.10)
    axes[1].text(16, 0.86, "migration is a net loss", fontsize=8, color=ACC[1],
                 ha="center")
    axes[1].annotate("3 us\n(assumed)", xy=(3, 1.505), xytext=(7.5, 1.62),
                     fontsize=7.5, color=INK,
                     arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
    axes[1].set_xlabel("cost of promoting one 4 KB page (us)")
    axes[1].set_ylabel("speedup vs all-CXL")
    axes[1].set_xlim(-1, 32); axes[1].set_ylim(0.7, 1.78)
    axes[1].set_title("Tiering only pays if migration\nstays under ~10 us",
                      fontsize=9.5, fontweight="bold")

    for a in axes:
        style(a)
    fig.tight_layout()
    p = f"{OUT}/hero_speedup.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for fn in (fig_validation, fig4_vs_paper, fig_tracker, fig_failuremode,
               fig_speedup):
        try:
            p = fn()
            print(f"  {p}" if p else f"  {fn.__name__}: skipped (no data yet)")
        except Exception as e:  # a missing input should not kill the rest
            print(f"  {fn.__name__}: failed ({e})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
