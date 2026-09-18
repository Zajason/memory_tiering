#!/usr/bin/env python3
"""plot_granularity.py -- figures for the granularity sweep.

    python3 src/analysis/plot_granularity.py

Produces, in docs/assets/:

  gran_pagesize.png   migration granularity — what a bigger page costs you
  gran_wordsize.png   tracking granularity — what a coarser tracker hides
  gran_surface.png    the full 2-D surface for one workload, as a heatmap

M5 fixes one cell of this grid (4 KB page, 64 B word). These plots are the rest of it.
"""

from __future__ import annotations

import csv
import os
import sys
import collections

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = "docs/assets"
INK = "#8b949e"
ACC = ["#58a6ff", "#f78166", "#3fb950", "#bc8cff", "#d29922", "#ff7b72", "#79c0ff", "#a5d6ff"]
plt.rcParams.update({
    "figure.facecolor": "none", "axes.facecolor": "none", "savefig.facecolor": "none",
    "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.edgecolor": INK, "axes.titlecolor": INK, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.18, "grid.linewidth": 0.6,
})


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_axisbelow(True)


def load():
    rows = []
    for f in ("results/granularity.csv", "results/granularity_redis.csv"):
        if os.path.exists(f):
            rows += list(csv.DictReader(open(f)))
    d = collections.defaultdict(dict)
    for r in rows:
        d[r["benchmark"]][(int(r["page_bytes"]), int(r["word_bytes"]))] = \
            float(r["mean_touched_frac"])
    return d


def lbl_bytes(b):
    return f"{b//1024} KB" if b < 2**20 else f"{b//2**20} MB"


def fig_pagesize(d):
    """Migration granularity: bigger pages move more bytes nobody asked for."""
    ps = [4096, 8192, 16384, 65536, 262144, 2097152]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for i, b in enumerate(sorted(d)):
        y = [d[b].get((p, 64)) for p in ps]
        if any(v is None for v in y):
            continue
        ax.plot(ps, [(1 - v) * 100 for v in y], "o-", color=ACC[i % len(ACC)],
                label=b, lw=1.8, ms=4.5)
    ax.set_xscale("log", base=2)
    ax.set_xticks(ps)
    ax.set_xticklabels([lbl_bytes(p) for p in ps])
    ax.set_xlabel("migration granularity (page size)")
    ax.set_ylabel("% of each migrated page never touched")
    ax.set_ylim(0, 100)
    ax.axvline(4096, color=ACC[2], ls="--", lw=1.1)
    ax.text(4300, 6, "M5 / Linux\n4 KB", fontsize=7.5, color=ACC[2])
    ax.axvline(2097152, color=ACC[1], ls="--", lw=1.1)
    ax.text(1_050_000, 92, "THP\n2 MB", fontsize=7.5, color=ACC[1], ha="right")
    ax.set_title("Migration granularity: the cost of huge pages", fontweight="bold")
    ax.legend(fontsize=7.5, ncol=2, frameon=False)
    style(ax)
    fig.tight_layout()
    p = f"{OUT}/gran_pagesize.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def fig_wordsize(d):
    """Tracking granularity: a coarse tracker overstates how much of a page is hot."""
    ws = [64, 128, 256, 512, 1024, 2048]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5))

    for i, b in enumerate(sorted(d)):
        y = [d[b].get((4096, w)) for w in ws]
        if any(v is None for v in y):
            continue
        axes[0].plot(ws, y, "o-", color=ACC[i % len(ACC)], label=b, lw=1.8, ms=4.5)
        axes[1].plot(ws, [(v / y[0] - 1) * 100 for v in y], "o-",
                     color=ACC[i % len(ACC)], lw=1.8, ms=4.5)

    for a in axes:
        a.set_xscale("log", base=2)
        a.set_xticks(ws)
        a.set_xticklabels([f"{w}B" for w in ws])
        a.set_xlabel("tracking granularity (word size), 4 KB page")
        a.axvline(64, color=ACC[2], ls="--", lw=1.1)
        style(a)
    axes[0].set_ylabel("apparent fraction of page touched")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("What a coarser tracker reports", fontsize=10, fontweight="bold")
    axes[0].legend(fontsize=7.5, ncol=2, frameon=False)
    axes[1].set_ylabel("overstatement vs 64 B ground truth (%)")
    axes[1].set_title("…and by how much it is wrong", fontsize=10, fontweight="bold")
    axes[1].axhline(0, color=INK, lw=0.8)

    fig.tight_layout()
    p = f"{OUT}/gran_wordsize.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def fig_surface(d, bench=None):
    """The whole grid for one workload; M5 measures a single cell of it."""
    if bench is None:
        bench = "redis-ycsba" if "redis-ycsba" in d else sorted(d)[0]
    ps = [4096, 8192, 16384, 65536, 262144, 2097152]
    ws = [64, 128, 256, 512, 1024, 2048, 4096]
    grid = np.full((len(ps), len(ws)), np.nan)
    for i, p_ in enumerate(ps):
        for j, w in enumerate(ws):
            v = d[bench].get((p_, w))
            if v is not None:
                grid[i, j] = v

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    im = ax.imshow(grid, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(ws)))
    ax.set_xticklabels([f"{w}B" for w in ws])
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels([lbl_bytes(p_) for p_ in ps])
    ax.set_xlabel("tracking granularity (word size)")
    ax.set_ylabel("migration granularity (page size)")
    for i in range(len(ps)):
        for j in range(len(ws)):
            if not np.isnan(grid[i, j]):
                ax.text(j, i, f"{grid[i,j]:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if grid[i, j] < 0.6 else "black")
    ax.add_patch(plt.Rectangle((-0.5, -0.5), 1, 1, fill=False, edgecolor="#f78166", lw=2.4))
    # Point at the cell from inside the axes, below it, so nothing overlaps the title.
    ax.annotate("M5 measures only this cell", xy=(0.15, 0.30), xytext=(1.9, 1.25),
                fontsize=8, color="#f78166", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#f78166", lw=1.4))
    ax.grid(False)
    ax.set_title(f"Fraction of a page actually touched — {bench}", fontweight="bold", pad=12)
    fig.colorbar(im, ax=ax, shrink=0.85, label="touched fraction")
    fig.tight_layout()
    p = f"{OUT}/gran_surface.png"
    fig.savefig(p, dpi=190, transparent=True)
    plt.close(fig)
    return p


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    d = load()
    if not d:
        print("no granularity csv found — run granularity_sweep.py first", file=sys.stderr)
        return 1
    for fn in (fig_pagesize, fig_wordsize, fig_surface):
        try:
            print(" ", fn(d))
        except Exception as e:
            print(f"  {fn.__name__} failed: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
