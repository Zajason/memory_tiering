#!/usr/bin/env python3
"""Figures for the Greek lab deck (presentation/build_lab_el.mjs).

Everything is read from results on disk at run time; nothing is typed in by
hand except the calibration values, which plot_readme.py already records.
One visual style for every figure, so the deck reads as one piece of work.

    .venv/bin/python src/analysis/plot_deck_el.py   ->  docs/assets/deck/*.png
"""
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ladder_report import load, err, M5, NS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / "results/prefetch-ladder-2026-11-15"
REV = ROOT / "results/revalidated-2026-10-25"
OUT = ROOT / "docs/assets/deck"
OUT.mkdir(parents=True, exist_ok=True)

INK, GREY, LIGHT, GRID = "#1B1F24", "#5F6670", "#A9AFB7", "#E3E6EA"
BLUE, BLUE_L, ORANGE = "#1F5FAD", "#9DBBE3", "#D9822B"
NCOL = ["#2464a3", "#15998a", "#cf9e20", "#ae4678", "#666666"]  # N = 4..48, as in the earlier figure
ORDER = ["bfs", "cc", "sssp", "bc", "pr", "tc"]
MAIN = ["bfs", "cc", "pr", "tc"]  # workloads on the main Figure-4 slide (keep in sync with build_lab_el.mjs)
NAME = dict(bfs="BFS", cc="CC", sssp="SSSP", bc="BC", pr="PR", tc="TC")

if any("Noto Sans" in f.name for f in font_manager.fontManager.ttflist):
    plt.rcParams["font.family"] = "Noto Sans"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": LIGHT, "axes.labelcolor": GREY,
                     "xtick.color": GREY, "ytick.color": GREY, "axes.titlecolor": INK})

CARD = json.loads((NEW / "scorecard.json").read_text())


def clean(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, facecolor="white")
    plt.close(fig)


def curves(stream):
    return {w: load(NEW / f"gapbs-{w}.paired.csv", stream=stream)[CARD[w]["loo_level"]][0] for w in ORDER}


def bar_rows(rows, name, height, width=12, order=ORDER):
    k = len(order)
    fig, axes = plt.subplots(len(rows), 1, figsize=(width, height), sharex=True, sharey=True)
    for ax, (title, data, notes) in zip(axes, rows):
        clean(ax)
        for i, n in enumerate(NS):
            ax.bar([x + (i - 2) * .155 for x in range(k)], [data[w][i] for w in order],
                   width=.145, color=NCOL[i], label=f"N = {n}")
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=5)
        ax.set_ylim(0, 1)
        ax.set_yticks([0, .5, 1])
        ax.set_xticks(range(k), [NAME[w] for w in order], fontsize=11, color=INK)
        ax.tick_params(axis="x", labelbottom=True)
        for x, w in enumerate(order):
            if max(data[w]) < .03:
                ax.text(x, .05, "πυκνές σελίδες", ha="center", va="bottom", fontsize=9,
                        color=LIGHT, style="italic")
        if notes:
            for x, w in enumerate(order):
                ax.text(x, .97, notes[w], ha="center", va="top", fontsize=10, color=GREY)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=5, frameon=False,
               fontsize=10.5, bbox_to_anchor=(0.5, 1.01), handlelength=1.2)
    fig.supylabel("P(σελίδα με το πολύ N από 64 words)", fontsize=10, color=GREY)
    fig.tight_layout(rect=(0.01, 0, 1, 0.95))
    save(fig, name)


def fig_main():
    acc, mis = curves("accesses"), curves("fills")
    m5 = {w: M5[w] for w in ORDER}
    note = {w: f"max |Δ| {err(mis[w], w):.2f}" for w in ORDER}
    bar_rows([("M5, Figure 4 (ASPLOS '25)", m5, None),
              ("Pintool: accesses της εφαρμογής", acc, None),
              ("Pintool + μοντέλο cache: misses προς τη συσκευή CXL", mis, note)],
             "fig4_main.png", 5.2, 8.6, order=MAIN)


def fig_cache_value():
    acc, mis = curves("accesses"), curves("fills")
    ea = [err(acc[w], w) for w in ORDER]
    em = [err(mis[w], w) for w in ORDER]
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    clean(ax)
    x = range(7)
    ea.append(sum(ea) / 6); em.append(sum(em) / 6)
    ax.bar([i - .2 for i in x], ea, .38, color=LIGHT, label="accesses (απλός Pin tracer)")
    ax.bar([i + .2 for i in x], em, .38, color=BLUE, label="misses (με μοντέλο cache)")
    for i in x:
        ax.text(i + .2, em[i] + .012, f"{em[i]:.2f}", ha="center", fontsize=9.5, color=INK)
        ax.text(i - .2, ea[i] + .012, f"{ea[i]:.2f}", ha="center", fontsize=9.5, color=GREY)
    ax.axvline(5.55, color=GRID, lw=1)
    ax.set_xticks(list(x), [NAME[w] for w in ORDER] + ["μέσος όρος"], color=INK)
    ax.set_ylabel("max |σφάλμα| έναντι M5")
    ax.set_ylim(0, .64)
    ax.legend(frameon=False, loc="upper right", fontsize=10)
    fig.tight_layout()
    save(fig, "cache_value.png")


def fig_progress():
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    clean(ax, grid="x")
    rows = ORDER + ["mean"]
    old = [CARD[w]["old_epoch"] for w in ORDER]
    new = [CARD[w]["loo_error"] for w in ORDER]
    old.append(sum(old) / 6); new.append(sum(new) / 6)
    for i, (a, b) in enumerate(zip(old, new)):
        y = len(rows) - 1 - i
        bold = rows[i] == "mean"
        ax.plot([a, b], [y, y], color=LIGHT if not bold else GREY, lw=2.2 if bold else 1.6, zorder=1)
        ax.scatter([a], [y], s=60, facecolor="white", edgecolor=ORANGE, lw=1.8, zorder=2)
        ax.scatter([b], [y], s=70 if bold else 60, color=BLUE, zorder=3)
        ax.text(b - .015 if b < a else b + .015, y + .28, f"{b:.2f}", ha="center", fontsize=9.5,
                color=INK, fontweight="bold" if bold else "normal")
    ax.set_yticks(range(len(rows)), [("μέσος όρος" if r == "mean" else NAME[r]) for r in rows][::-1], color=INK)
    ax.set_xlim(0, .85)
    ax.set_xlabel("max |σφάλμα| έναντι M5 (σε 5 σημεία N)")
    ax.scatter([], [], s=60, facecolor="white", edgecolor=ORANGE, lw=1.8, label="αρχικό μοντέλο (demand-only, 10M events)")
    ax.scatter([], [], s=60, color=BLUE, label="τελικό (prefetch + κοινό time window)")
    ax.legend(frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.36), fontsize=9.5)
    fig.tight_layout()
    save(fig, "progress.png")


def spans(w, d):
    tot = next(float(l.split()[1]) for l in (NEW / f"gapbs-{w}.summary.txt").read_text().splitlines()
               if l.startswith("instructions"))
    per = tot / max(d[0][2], 1)
    return {k: (tot if k == "whole" else per * 2 ** k) for k in d}


def fig_window():
    grid = [1e9 * 2 ** (i / 8) for i in range(0, 89)]
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    clean(ax)
    means = []
    per = {}
    for w in ORDER:
        d = load(NEW / f"gapbs-{w}.paired.csv")
        sp = spans(w, d)
        e = {k: err(d[k][0], w) for k in d}
        per[w] = [e[min(sp, key=lambda k: abs(math.log(sp[k] / t)))] for t in grid]
        ax.plot([t / 1e9 for t in grid], per[w], color=LIGHT, lw=1.1, drawstyle="steps-mid")
    ys, last = sorted((per[w][-1], w) for w in ORDER), -1
    for y, w in ys:
        y = max(y, last + .032); last = y
        ax.text(grid[-1] / 1e9 * 1.06, y, NAME[w], fontsize=8.5, color=GREY, va="center")
    means = [sum(per[w][i] for w in ORDER) / 6 for i in range(len(grid))]
    ax.plot([t / 1e9 for t in grid], means, color=BLUE, lw=2.4, drawstyle="steps-mid", label="μέσος όρος 6 workloads")
    ts = sorted(CARD[w]["loo_instructions"] / 1e9 for w in ORDER)
    ax.axvspan(ts[0], ts[-1], color=BLUE_L, alpha=.35, lw=0)
    ax.text(math.sqrt(ts[0] * ts[-1]), .74, "window που επιλέγουν\nτα υπόλοιπα 5 workloads\n(leave-one-out)",
            ha="center", va="top", fontsize=10, color=BLUE)
    ax.set_xscale("log")
    ax.set_xticks([1, 4, 16, 64, 256, 1024], ["1B", "4B", "16B", "64B", "256B", "1T"])
    ax.set_xlabel("μήκος κοινού window (instructions)")
    ax.set_ylabel("max |σφάλμα| έναντι M5")
    ax.set_ylim(0, .8)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)
    fig.tight_layout()
    save(fig, "window.png")


def fig_calibration():
    strides = [4096, 1024, 256, 64]
    expected = [1, 4, 16, 64]
    measured = [1.000, 3.999, 15.996, 63.981]  # plot_readme.py, synthetic stride kernels
    fig, ax = plt.subplots(figsize=(5.2, 3.7))
    clean(ax)
    x = range(4)
    ax.bar([i - .19 for i in x], expected, .36, color=LIGHT, label="αναλυτική τιμή")
    ax.bar([i + .19 for i in x], measured, .36, color=BLUE, label="μέτρηση pintool")
    for i, m in enumerate(measured):
        ax.text(i + .19, m * 1.25, f"{m:g}", ha="center", fontsize=10, color=INK)
    ax.set_yscale("log")
    ax.set_ylim(.6, 200)
    ax.set_xticks(list(x), [f"stride {s} B" for s in strides], color=INK)
    ax.set_ylabel("μοναδικά 64 B words ανά σελίδα 4 KB")
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    fig.tight_layout()
    save(fig, "calibration.png")


def fig_sim():
    sim = {}
    with open(REV / "sim-comparison/comparison.csv") as f:
        for r in csv.DictReader(f):
            if r["port"] == "bridge":
                sim.setdefault(r["workload"], {})[int(r["n"])] = float(r["cdf"])
    data = {w: [sim[w][n] for n in NS] for w in MAIN}
    note = {w: f"max |Δ| {max(abs(a - b) for a, b in zip(data[w], M5[w])):.2f}" for w in MAIN}
    bar_rows([("M5, Figure 4 (ASPLOS '25)", {w: M5[w] for w in MAIN}, None),
              ("SimCXL (gem5): requests στη CXL bridge, φυσικές διευθύνσεις + kernel", data, note)],
             "sim.png", 3.6, 9.6, order=MAIN)


def fig_trackers():
    import collections
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.6), sharey=True)
    for ax, algo, title in zip(axes, ["spacesaving", "cmsketch"], ["Space-Saving", "Count-Min Sketch"]):
        clean(ax)
        allv = collections.defaultdict(list)
        for w in ORDER:
            acc = collections.defaultdict(list)
            with open(REV / f"pin/{algo}/gapbs-{w}.tracker.csv") as f:
                for r in csv.DictReader(f):
                    if r.get("n") and r.get("hpt_access_ratio"):
                        acc[int(r["n"])].append(float(r["hpt_access_ratio"]))
            xs = sorted(acc)
            ys = [sum(acc[n]) / len(acc[n]) for n in xs]
            for n, y in zip(xs, ys):
                allv[n].append(y)
            ax.plot(xs, ys, color=LIGHT, lw=1.1, marker="o", ms=3)
        xs = sorted(allv)
        ax.plot(xs, [sum(allv[n]) / len(allv[n]) for n in xs], color=BLUE, lw=2.4, marker="o", ms=5,
                label="μέσος όρος 6 GAP workloads")
        ax.set_xscale("log", base=2)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("entries του tracker (K = 128)")
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("κάλυψη accesses του\nπραγματικού top-128 (HPT)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=9.5)
    fig.tight_layout()
    save(fig, "trackers.png")


def fig_granularity():
    show = [("redis-a", "Redis (YCSB-A)", BLUE), ("memcached", "Memcached", "#4C8BD6"),
            ("liblinear", "Liblinear", ORANGE)]
    graph = ["spacesaving-bfs", "spacesaving-cc", "spacesaving-tc", "spacesaving-bc",
             "spacesaving-sssp", "spacesaving-pr"]
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    clean(ax)

    def series(n):
        d = json.loads((REV / f"analysis/{n}.json").read_text())
        g = sorted((x["word_bytes"], x["mean_fraction"]) for x in d["granularity"] if x["page_bytes"] == 4096)
        return [a for a, _ in g], [b for _, b in g]

    for n in graph:
        xs, ys = series(n)
        ax.plot(xs, ys, color=GRID, lw=1.3)
    ax.plot([], [], color=GRID, lw=1.3, label="GAP workloads")
    for n, label, c in show:
        xs, ys = series(n)
        ax.plot(xs, ys, color=c, lw=2.2, marker="o", ms=4, label=label)
    xs, ys = series("redis-a")
    i = xs.index(512)
    ax.annotate(f"Redis: από {ys[0]:.2f} σε {ys[i]:.2f} (×{ys[i] / ys[0]:.1f})", (512, ys[i]), xytext=(150, .62),
                fontsize=9.5, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE, lw=.8))
    ax.set_xscale("log", base=2)
    ax.set_xticks([64, 128, 256, 512, 1024, 2048], ["64", "128", "256", "512", "1K", "2K"])
    ax.set_xlabel("μονάδα παρακολούθησης (bytes), σελίδα 4 KB")
    ax.set_ylabel("μέσο ποσοστό σελίδας\nπου φαίνεται «touched»")
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)
    fig.tight_layout()
    save(fig, "granularity.png")


if __name__ == "__main__":
    for f in (fig_main, fig_cache_value, fig_progress, fig_window, fig_calibration, fig_sim,
              fig_trackers, fig_granularity):
        f()
        print("ok", f.__name__)
