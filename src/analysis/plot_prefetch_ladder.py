#!/usr/bin/env python3
"""Figures and scorecard for the prefetch + window-ladder campaign.

Reads results at run time, so re-running after more workloads finish refreshes
everything (figures, scorecard.json, SCORECARD.md) without editing numbers.

  docs/assets/fig4_prefetch_ladder.png    curves: M5, old headline, new
  docs/assets/prefetch_ladder_error.png   error against window length
  docs/assets/fig4_prefetch_bars.png      M5-style grouped bars, same layout as fig4_fidelity_full.png
  results/prefetch-ladder-2026-11-15/scorecard.json, SCORECARD.md
"""
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ladder_report import load, err, M5, NS

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / "results/prefetch-ladder-2026-11-15"
OLD = ROOT / "results/fidelity-2026-10-27/dataset"
ORDER = ["bc", "bfs", "cc", "pr", "sssp", "tc"]
NAME = dict(bc="BC", bfs="BFS", cc="CC", pr="PageRank", sssp="SSSP", tc="TC")
INK, BLUE, RED, GREY, GRID = "#171717", "#185ADB", "#F04438", "#6B6B6B", "#D8D8D4"
LEVELS = list(range(11))
# Candidate common windows, in instructions (quarter-octave steps, 1B .. 2048B).
T_GRID = [1e9 * 2 ** (i / 4) for i in range(45)]


def spans(w, d):
    """Instructions covered by each ladder level: a proxy for elapsed time.

    A profiler samples on a timer, not every N device events, and the six
    workloads differ by ~300x in device events per instruction. So "the same
    window" across benchmarks means the same time, not the same event count.
    """
    f = NEW / f"gapbs-{w}.summary.txt"
    if not f.exists() or 0 not in d:
        return {}
    tot = next(float(l.split()[1]) for l in f.read_text().splitlines() if l.startswith("instructions"))
    per = tot / max(d[0][2], 1)
    return {k: (tot if k == "whole" else per * 2 ** k) for k in d}


def level_for(span, t):
    return min(span, key=lambda k: abs(math.log(span[k] / t)))


def window_label(k):
    if k == "whole":
        return "whole run"
    ev = 10 * 2 ** k
    return f"{ev}M" if ev < 1000 else f"{ev / 1000:.2f}G".replace(".00G", "G")


def first_with_whole(paths):
    for p in paths:
        if p.exists():
            d = load(p)
            if "whole" in d:
                return d
    return {}


def gather():
    old, new, status = {}, {}, {}
    for w in ORDER:
        old[w] = first_with_whole([OLD / f"gapbs-{w}.paired.csv", OLD / "attempt-1" / f"gapbs-{w}.paired.csv"])
        d = first_with_whole([NEW / f"gapbs-{w}.paired.csv"])
        status[w] = "complete"
        if not d:
            snap = NEW / f"gapbs-{w}.ladder.csv"
            d = load(snap) if snap.exists() else {}
            status[w] = "partial" if d else "running"
        new[w] = d
    return old, new, status


def score(old, new, status):
    done = [w for w in ORDER if status[w] == "complete"]
    table = {w: {k: err(v[0], w) for k, v in new[w].items()} for w in ORDER if new[w]}
    common = [k for k in LEVELS + ["whole"] if done and all(k in table[w] for w in done)]
    span = {w: spans(w, new[w]) for w in done}
    span = {w: v for w, v in span.items() if v}
    card = {}
    for w in ORDER:
        row = dict(status=status[w],
                   old_epoch=err(old[w][0][0], w) if 0 in old[w] else None,
                   old_whole=err(old[w]["whole"][0], w) if "whole" in old[w] else None)
        if w in table:
            others = [o for o in done if o != w]
            if others and common:
                pick = min(common, key=lambda k: sum(table[o][k] for o in others) / len(others))
                if pick in table[w]:
                    row.update(ev_loo_level=pick, ev_loo_window=window_label(pick), ev_loo_error=table[w][pick])
            others = [o for o in span if o != w]
            if others and w in span:
                cost = [sum(table[o][level_for(span[o], t)] for o in others) / len(others) for t in T_GRID]
                tied = [t for t, c in zip(T_GRID, cost) if c <= min(cost) + 1e-9]
                t = tied[len(tied) // 2]  # middle of the plateau, not its edge
                k = level_for(span[w], t)
                row.update(loo_level=k, loo_window=window_label(k), loo_error=table[w][k],
                           loo_instructions=t, level_instructions=span[w][k])
            best = min(table[w], key=lambda k: table[w][k])
            row.update(new_epoch=table[w].get(0), new_whole=table[w].get("whole"),
                       fitted_level=best, fitted_window=window_label(best), fitted_error=table[w][best])
        card[w] = row
    return card, table


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=GREY, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def fig_curves(old, new, card):
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.3), sharey=True)
    x = range(len(NS))
    for ax, w in zip(axes.flat, ORDER):
        style(ax)
        c = card[w]
        if 0 in old[w]:
            ax.plot(x, old[w][0][0], color=RED, lw=1.6, ls=(0, (4, 2)), marker="s", ms=5,
                    label="ours before: 10M window, demand-only model")
        if "loo_level" in c:
            ax.plot(x, new[w][c["loo_level"]][0], color=BLUE, lw=2.2, marker="o", ms=6, clip_on=False, zorder=4,
                    label="ours now: prefetch model, one time window for all (leave-one-out)")
        ax.plot(x, M5[w], color=INK, lw=2.6, marker="D", ms=5, label="M5 Figure 4 (published)")
        ax.set_xticks(list(x), [str(n) for n in NS])
        ax.set_ylim(0, 1)
        head = f"{NAME[w]}"
        if "loo_error" in c and c["old_epoch"] is not None:
            tail = f"max error {c['old_epoch']:.2f} → {c['loo_error']:.2f}"
            if c["status"] == "partial":
                tail += "  (run still in progress)"
        else:
            tail = "new run in progress"
        ax.set_title(head, loc="left", fontsize=12, fontweight="bold", color=INK, pad=14)
        ax.text(0, 1.02, tail, transform=ax.transAxes, fontsize=9.5, color=GREY)
    for ax in axes[1]:
        ax.set_xlabel("N  (at most N of 64 words touched)", fontsize=9.5, color=GREY)
    for ax in axes[:, 0]:
        ax.set_ylabel("P(page touches ≤ N words)", fontsize=9.5, color=GREY)
    h, l = [], []
    for ax in axes.flat:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in l:
                h.append(hh); l.append(ll)
    order = sorted(range(len(l)), key=lambda i: ("M5" not in l[i], "now" not in l[i]))
    fig.legend([h[i] for i in order], [l[i] for i in order], loc="upper center", ncol=3,
               frameon=False, fontsize=10, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ROOT / "docs/assets/fig4_prefetch_ladder.png", dpi=170, facecolor="white")
    plt.close(fig)


def fig_error(card, table):
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.0), sharey=True)
    for ax, w in zip(axes.flat, ORDER):
        style(ax)
        c = card[w]
        ax.set_title(NAME[w], loc="left", fontsize=12, fontweight="bold", color=INK)
        ax.set_ylim(0, 0.85)
        ax.set_xlim(-0.6, 11.6)
        ax.set_xticks([0, 2, 4, 6, 8, 11.2], ["10M", "40M", "160M", "640M", "2.6G", "whole"])
        ax.axvline(10.6, color=GRID, lw=0.8)
        if w not in table:
            ax.text(0.5, 0.5, "new run in progress", transform=ax.transAxes, ha="center", color=GREY, fontsize=10)
        else:
            ks = [k for k in LEVELS if k in table[w]]
            ax.plot(ks, [table[w][k] for k in ks], color=BLUE, lw=2, marker="o", ms=5,
                    label="prefetch model, window ladder")
            if "whole" in table[w]:
                ax.plot([11.2], [table[w]["whole"]], color=BLUE, marker="o", ms=7, ls="none")
            if "loo_level" in c:
                xk = 11.2 if c["loo_level"] == "whole" else c["loo_level"]
                ax.plot([xk], [c["loo_error"]], marker="o", ms=15, mfc="none", mec=INK, mew=1.6, ls="none",
                        label="common time window, chosen by the other benchmarks")
                ax.annotate(f"{c['loo_error']:.2f}", (xk, c["loo_error"]), textcoords="offset points",
                            xytext=(0, 13), ha="center", fontsize=9.5, color=INK)
        pts = [(0, c["old_epoch"]), (11.2, c["old_whole"])]
        pts = [(a, b) for a, b in pts if b is not None]
        if pts:
            ax.plot([a for a, _ in pts], [b for _, b in pts], color=RED, marker="s", ms=10, mfc="none",
                    mew=1.6, ls="none", zorder=5, label="demand-only model (before)")
    for ax in axes[1]:
        ax.set_xlabel("measurement window (device events)", fontsize=9.5, color=GREY)
    for ax in axes[:, 0]:
        ax.set_ylabel("max |error| against M5", fontsize=9.5, color=GREY)
    h, l = [], []
    for ax in axes.flat:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in l:
                h.append(hh); l.append(ll)
    fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ROOT / "docs/assets/prefetch_ladder_error.png", dpi=170, facecolor="white")
    plt.close(fig)


def fig_bars(card):
    """Same layout as fig4_fidelity_full.png (publish_fidelity.py), new numbers."""
    names = ["bfs", "cc", "sssp", "bc", "pr", "tc"]
    if not all("loo_level" in card[w] for w in names):
        return
    colors = ["#2464a3", "#15998a", "#cf9e20", "#ae4678", "#666666"]
    rows = [(None, "M5 Figure 4: digitized reference"),
            ("accesses", "Ours: application demand accesses"),
            ("traffic", "Ours: modeled device traffic (demand misses + hardware prefetches + writebacks)")]
    data = {st: {w: load(NEW / f"gapbs-{w}.paired.csv", stream=st)[card[w]["loo_level"]][0] for w in names}
            for st, _ in rows if st}
    fig, axes = plt.subplots(3, 1, figsize=(13, 8.5), sharex=True, sharey=True)
    for ax, (st, title) in zip(axes, rows):
        for i, n in enumerate(NS):
            vals = [M5[w][i] if st is None else data[st][w][i] for w in names]
            ax.bar([x + (i - 2) * .15 for x in range(6)], vals, width=.14, color=colors[i], label=f"N={n}")
        ax.set_title(title, loc="left"); ax.set_ylim(0, 1); ax.set_ylabel("CDF")
        ax.set_xticks(range(6), [w.upper() for w in names]); ax.tick_params(axis="x", labelbottom=True)
        ax.grid(axis="y", alpha=.15); ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=5)
    fig.suptitle("M5 and our reproduction: prefetch model, one common time window", y=.95)
    ts = sorted(card[w]["loo_instructions"] / 1e9 for w in names)
    fig.text(.5, .035, f"One thread; hardware-prefetch model on; one time window for all workloads "
             f"({ts[0]:.0f}-{ts[-1]:.0f}B instructions, chosen leave-one-out); own touched-page populations.",
             ha="center", fontsize=9)
    fig.text(.5, .015, "Twitter induced reductions; Google+ snapshots 4 (BC), 2 (SSSP). BC/SSSP ran 4/8 trials. "
             "Authors exact inputs/schedule unresolved.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .92))
    fig.savefig(ROOT / "docs/assets/fig4_prefetch_bars.png", dpi=180)
    plt.close(fig)


def main():
    old, new, status = gather()
    card, table = score(old, new, status)
    (NEW / "scorecard.json").write_text(json.dumps(card, indent=1))
    f = lambda v: "—" if v is None else f"{v:.3f}"
    b = lambda v: "—" if v is None else f"**{v:.3f}**"
    lines = ["| workload | status | before: 10M-event window | now: common time window (leave-one-out) | chosen by the others | that is, in events | common event window (leave-one-out) | whole run | fitted bound (not a result) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for w in ORDER:
        c = card[w]
        t = c.get("loo_instructions")
        lines.append(f"| {w} | {c['status']} | {f(c['old_epoch'])} | {b(c.get('loo_error'))} | "
                     f"{'—' if t is None else f'{t / 1e9:.0f}B instr'} | {c.get('loo_window', '—')} | "
                     f"{f(c.get('ev_loo_error'))} ({c.get('ev_loo_window', '—')}) | {f(c.get('new_whole'))} | {f(c.get('fitted_error'))} |")
    done = [c for c in card.values() if c["status"] == "complete" and c.get("loo_error") is not None]
    if done:
        m = lambda key: sum(c[key] for c in done) / len(done)
        lines.append(f"\nMean max error over {len(done)} completed workloads: before {m('old_epoch'):.3f}; "
                     f"common event window {m('ev_loo_error'):.3f}; common time window {m('loo_error'):.3f}.")
    (NEW / "SCORECARD.md").write_text("\n".join(lines) + "\n")
    fig_curves(old, new, card)
    fig_error(card, table)
    fig_bars(card)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
