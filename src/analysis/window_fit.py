#!/usr/bin/env python3
"""window_fit.py -- at what measurement window do we reproduce M5's Figure 4?

    python3 src/analysis/window_fit.py [--config spr-20t-ul]

Why
---
Every remaining disagreement with M5 points at the same parameter. Word coverage per
page is monotonically non-decreasing in the window (§3.3 of the report), the whole-run
bound sits far below M5's value, and the 10M-access bound sits far above it -- so for
each workload *some* window reproduces the paper. The question is which, and whether
one window works for all of them.

That distinction is the whole point:

  * if a SINGLE window reproduces every workload, the only real deviation left is a
    parameter M5 did not publish, and we have measured it;
  * if each workload needs its own window, the window is not the explanation and
    something workload-specific is still wrong.

The second outcome is the one that would matter, so this is a test that can fail.

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
    ep = recs["epoch"].astype(np.int64)
    grp = ep // m
    # Fold (group, page) -> OR of masks. Sorting by the pair makes the fold a
    # segmented reduction, which numpy can do without a Python loop per page.
    key = (grp.astype(np.uint64) << np.uint64(40)) ^ recs["page"].astype(np.uint64)
    order = np.argsort(key, kind="stable")
    k, masks = key[order], recs["mask"][order]
    # boundaries of runs of equal key
    newgrp = np.empty(k.shape, dtype=bool)
    newgrp[0] = True
    newgrp[1:] = k[1:] != k[:-1]
    idx = np.cumsum(newgrp) - 1
    n_out = idx[-1] + 1
    merged = np.zeros(n_out, dtype=np.uint64)
    np.bitwise_or.at(merged, idx, masks)
    uw = H._popcount64(merged)
    if uw.size == 0:
        return None
    return {n: float((uw <= n).mean()) for n in ns}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t-ul")
    ap.add_argument("--epoch-m", type=float, default=10.0,
                    help="millions of DRAM accesses per base epoch in the input")
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    print(f"\nWindow that reproduces M5's Figure 4   (config: {args.config})")
    print("error = mean |ours - M5| over N in {4,8,16,32,48}\n")
    print(f"{'workload':<10}{'base':>6}{'best m':>8}{'window':>12}{'err':>8}"
          f"{'err@m=1':>9}   verdict")
    print("-" * 66)

    fits = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        bench = name[: -len(".pages.bin")]
        if bench not in H.M5_FIGURE4:
            continue
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        recs = H.load_pages(path).records
        if recs.size == 0:
            continue
        n_ep = int(recs["epoch"].max()) + 1
        m5 = H.M5_FIGURE4[bench]

        best = None
        base_err = None
        m = 1
        while m <= max(n_ep, 1):
            c = cdf_at_merge(recs, m)
            if c is not None:
                err = float(np.mean([abs(c[n] - m5[n]) for n in H.FIG4_N]))
                if m == 1:
                    base_err = err
                if best is None or err < best[1]:
                    best = (m, err, c)
            m *= 2
        if best is None:
            continue
        m, err, c = best
        win = f"{m * args.epoch_m:.0f}M acc"
        v = "reproduced" if err <= 0.05 else "close" if err <= 0.12 else "still off"
        print(f"{bench.replace('gapbs-',''):<10}{n_ep:>6}{m:>8}{win:>12}{err:>8.3f}"
              f"{base_err:>9.3f}   {v}")
        fits.append((bench, m, err))

    if fits:
        ms = [m for _, m, _ in fits]
        print()
        if len(set(ms)) == 1:
            print(f"All workloads reproduce at the SAME window (m={ms[0]}). The window")
            print("is the only remaining deviation, and it is now measured.")
        else:
            print(f"Best window differs across workloads: m in {sorted(set(ms))}.")
            print("So the window alone does NOT explain the disagreement -- a single")
            print("unpublished parameter cannot be blamed, and something workload-")
            print("specific (most likely the dataset) is still different.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
