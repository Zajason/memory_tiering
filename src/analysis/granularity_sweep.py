#!/usr/bin/env python3
"""granularity_sweep.py -- extend M5's Figure 4 into a 2-D granularity surface.

    python3 src/analysis/granularity_sweep.py [--config spr-20t-ul]

Why
---
M5 fixes one point in a two-dimensional space: a **4 KB page** divided into **64 B
words**. Both numbers are chosen, not derived — 4 KB because that is Linux's mapping
unit and 64 B because that is the cache line. The interesting question the paper does
not ask is how the sparsity it reports varies when you move either axis.

Two axes, two different debates:

  **word size** (sub-page granularity) — how finely a tracker resolves hotness.
  Bigger words mean cheaper hardware (fewer counters) and coarser information. M5's
  HWT uses 64 B; the useful question is how much resolution you lose at 128 B or
  512 B, because that is a direct hardware-cost lever.

  **page size** (migration granularity) — the huge-page debate. TPP and Memtis reach
  for 2 MB pages to amortise migration cost, and the standard objection is that
  internal fragmentation becomes catastrophic: a 2 MB page promoted for one hot cache
  line wastes 99.997% of the transfer. That objection is usually asserted. Here it is
  measured.

How, and why no re-runs are needed
----------------------------------
`.pages.bin` records, for every (page, epoch), which of the page's sixty-four 64 B
words were touched. Coarser granularities are exact re-bucketings of that:

  * a 128 B word is touched iff either of its two 64 B words was → OR adjacent bits;
  * a 2 MB page is 512 consecutive 4 KB pages → its touched-word count is the sum of
    its sub-pages' counts, and its denominator is 512x larger.

The second point is where huge pages lose: sub-pages that were never touched at all
still count in the denominator. Nothing is estimated and nothing is re-run.

**64 B is a hard floor.** Below the cache line the post-LLC stream cannot distinguish
anything: a DRAM access transfers exactly one 64 B line, so "which 32 B half was
touched" is not information the memory controller has. Finer granularity is only
meaningful on the *architectural* stream (`-cache 0`), which answers a different
question. The sweep therefore starts at 64 B and this is a property of the hardware,
not a limitation of the tool.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

PAGE_SIZES = [4096, 8192, 16384, 65536, 262144, 2097152]      # 4 KB … 2 MB
WORD_SIZES = [64, 128, 256, 512, 1024, 2048, 4096]            # 64 B … 4 KB


def coarsen_popcount(masks: np.ndarray, word_size: int) -> np.ndarray:
    """Touched-word count per 4 KB page at the given word size (64 B … 4 KB)."""
    k = word_size // 64                       # 64 B words per coarse word
    if k == 1:
        return H._popcount64(masks).astype(np.int32)
    if k == 64:                               # one word == the whole 4 KB page
        return (masks != 0).astype(np.int32)
    # A coarse word is touched iff any of its k constituent bits is set.
    out = np.zeros(masks.shape, dtype=np.int32)
    for g in range(64 // k):
        grp = (np.uint64((1 << k) - 1) << np.uint64(g * k))
        out += ((masks & grp) != 0).astype(np.int32)
    return out


def sweep(path: str) -> dict:
    recs = H.load_pages(path).records
    if recs.size == 0:
        return {}
    ep = recs["epoch"].astype(np.int64)
    pg = recs["page"].astype(np.int64)
    masks = recs["mask"]

    res = {}
    for ps in PAGE_SIZES:
        j = ps // 4096                        # 4 KB sub-pages per page
        big = pg // j
        # (epoch, big page) identifies one page-sized region in one window
        key = ep * (big.max() + 2) + big
        order = np.argsort(key, kind="stable")
        k_sorted = key[order]
        starts = np.empty(k_sorted.shape, dtype=bool)
        starts[0] = True
        starts[1:] = k_sorted[1:] != k_sorted[:-1]
        grp_idx = np.cumsum(starts) - 1
        n_groups = int(grp_idx[-1]) + 1

        for ws in WORD_SIZES:
            if ws >= ps:                      # a word must be smaller than its page
                continue
            touched_sub = coarsen_popcount(masks, ws)[order]
            total = np.zeros(n_groups, dtype=np.int64)
            np.add.at(total, grp_idx, touched_sub)
            words_per_page = ps // ws
            frac = total / float(words_per_page)
            res[(ps, ws)] = {
                "mean_frac": float(frac.mean()),
                "p_le_25pct": float((frac <= 0.25).mean()),
                "wasted": float(1.0 - frac.mean()),
                "pages": int(n_groups),
            }
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t-ul")
    ap.add_argument("--csv", default="results/granularity.csv")
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    rows = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        p = os.path.join(d, name)
        if os.path.getsize(p) == 0:
            continue
        bench = name[: -len(".pages.bin")].replace("gapbs-", "")
        r = sweep(p)
        if not r:
            continue
        rows.append((bench, r))

        print(f"\n=== {bench} — fraction of a page actually touched ===")
        hdr = "  page \\ word " + "".join(f"{ws:>8}B" for ws in WORD_SIZES)
        print(hdr); print("  " + "-" * (len(hdr) - 2))
        for ps in PAGE_SIZES:
            lab = f"{ps//1024:>5} KB" if ps < 2**20 else f"{ps//2**20:>5} MB"
            line = f"  {lab}     "
            for ws in WORD_SIZES:
                line += f"{r[(ps,ws)]['mean_frac']:>9.3f}" if (ps, ws) in r else f"{'—':>9}"
            print(line)

    if rows:
        with open(args.csv, "w") as fh:
            fh.write("benchmark,page_bytes,word_bytes,mean_touched_frac,"
                     "p_le_25pct,wasted_frac,pages\n")
            for bench, r in rows:
                for (ps, ws), v in sorted(r.items()):
                    fh.write(f"{bench},{ps},{ws},{v['mean_frac']:.6f},"
                             f"{v['p_le_25pct']:.6f},{v['wasted']:.6f},{v['pages']}\n")
        print(f"\ncsv -> {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
