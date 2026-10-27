#!/usr/bin/env python3
"""window_fit.py -- exploratory sensitivity of page coverage to merged windows.

    python3 src/analysis/window_fit.py [--config spr-20t-ul]

Fitting to the reference does not identify its observation window or prove a
reproduction. Other configuration differences remain. The changing population of
touched pages and the final partial window can make the pooled CDF non-monotonic.

How
---
Windows are simulated offline rather than by re-running. `.pages.bin` records per-page
counts *per epoch*, and merging m consecutive epochs is exactly what a window m times
longer would have recorded:

    touched_mask  = OR  of the m masks      (a word touched in any sub-window)
    counts        = SUM of the m counts

So one profiling run at a fine epoch yields the entire window-length curve. No fitting
is involved in *producing* the curve; the only fitted quantity is where M5's published
value intersects it.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402


def cdf_at_merge(recs: np.ndarray, m: int, ns=H.FIG4_N) -> dict[int, float] | None:
    """P(page has <= N unique words) when m consecutive epochs are merged."""
    if m < 1:
        raise ValueError("merge factor must be positive")
    if recs.size == 0:
        return None
    ep = recs["epoch"].astype(np.int64)
    grp = ep // m
    # Fold (group, page) -> OR of masks. Sorting by the pair makes the fold a
    # segmented reduction, which numpy can do without a Python loop per page.
    order = np.lexsort((recs["page"], grp))
    groups, pages, masks = grp[order], recs["page"][order], recs["mask"][order]
    # boundaries of runs of equal key
    newgrp = np.empty(pages.shape, dtype=bool)
    newgrp[0] = True
    newgrp[1:] = (groups[1:] != groups[:-1]) | (pages[1:] != pages[:-1])
    idx = np.cumsum(newgrp) - 1
    n_out = idx[-1] + 1
    merged = np.zeros(n_out, dtype=np.uint64)
    np.bitwise_or.at(merged, idx, masks)
    uw = H._popcount64(merged)
    if uw.size == 0:
        return None
    return {n: float((uw <= n).mean()) for n in ns}


def error_for(bench, cdf, target="prose"):
    if target == "prose":
        if bench in H.M5_TEXT_P16:
            return abs(cdf[16] - H.M5_TEXT_P16[bench])
        if bench in H.M5_TEXT_P47:
            return abs(cdf[47] - H.M5_TEXT_P47[bench])
    return float(np.mean([abs(cdf[n] - H.M5_FIGURE4[bench][n]) for n in H.FIG4_N]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t-ul")
    ap.add_argument("--epoch-m", type=float, default=10.0,
                    help="millions of DRAM accesses per base epoch in the input")
    ap.add_argument("--target", choices=["prose", "digitised"], default="prose",
                    help="prose = one rounded P(<=16) or P(<=47) value; "
                         "digitised = mean over all five N vs bar readings")
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    print(f"\nExploratory window fit, NOT reproduction   (config: {args.config})")
    print("error = |P(<=16) - the paper's stated value| where the prose gives one"
          if args.target == "prose" else
          "error = mean |ours - M5| over N in {4,8,16,32,48}")
    print()
    print(f"{'workload':<10}{'base':>6}{'best m':>8}{'window':>12}{'err':>8}"
          f"{'err@m=1':>9}   verdict")
    print("-" * 66)

    def err_for(bench, c):
        return error_for(bench, c, args.target)

    fits = []
    loaded = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        bench = name[: -len(".pages.bin")]
        if bench not in H.M5_FIGURE4:
            continue
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        recs = H.load_pages(path, require_complete=True).records
        if recs.size == 0:
            continue
        n_ep = int(recs["epoch"].max()) + 1
        loaded.append((bench, recs))
        m5 = H.M5_FIGURE4[bench]

        best = None
        base_err = None
        # Every m, not powers of two. The coarse grid is why an earlier run
        # reported "best window varies 1x-8x": with 22 epochs it only sampled
        # m = 1, 2, 4, 8, 16, so a best at m = 11 was invisible.
        for m in range(1, max(n_ep, 1) + 1):
            c = cdf_at_merge(recs, m, ns=(*H.FIG4_N, 47))
            if c is None:
                continue
            # The prose percentages are rounded and refer to only one CDF point.
            err = err_for(bench, c)
            if m == 1:
                base_err = err
            if best is None or err < best[1]:
                best = (m, err, c)
        if best is None:
            continue
        m, err, c = best
        win = f"{m * args.epoch_m:.0f}M acc"
        v = "fitted error only"
        print(f"{bench.replace('gapbs-',''):<10}{n_ep:>6}{m:>8}{win:>12}{err:>8.3f}"
              f"{base_err:>9.3f}   {v}")
        fits.append((bench, m, err))

    if fits:
        ms = [m for _, m, _ in fits]
        print(f"\nPer-workload optima: m in {sorted(set(ms))}")
        print("Different optima do not identify the original experiment's windows.\n")

        # Global fit: minimise the WORST error across workloads over a single m.
        best_g = None
        for m in range(1, max(int(r['epoch'].max()) + 1 for _, r in loaded) + 1):
            row = {}
            for bench, recs in loaded:
                c = cdf_at_merge(recs, m, ns=(*H.FIG4_N, 47))
                if c is None:
                    break
                row[bench] = err_for(bench, c)
            if len(row) != len(loaded):
                continue
            worst = max(row.values())
            if best_g is None or worst < best_g[1]:
                best_g = (m, worst, dict(row))
        if best_g:
            m, worst, row = best_g
            base = {}
            for bench, recs in loaded:
                c = cdf_at_merge(recs, 1, ns=(*H.FIG4_N, 47))
                if c is not None:
                    base[bench] = err_for(bench, c)
            print(f"Best SINGLE window: m={m}  ({m * args.epoch_m:.0f}M accesses)")
            print(f"  worst-case error {worst:.3f}   "
                  f"(at m=1 it is {max(base.values()):.3f})")
            for b, v in sorted(row.items(), key=lambda x: -x[1]):
                tag = "fitted error"
                print(f"    {b.replace('gapbs-', ''):<6} {v:.3f}  {tag}")
            print("\nThis is a ONE-PARAMETER FIT, not a reproduction: the window was")
            print("chosen to minimise error against M5. It shows sensitivity, not causation.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
