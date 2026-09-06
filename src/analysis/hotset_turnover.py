#!/usr/bin/env python3
"""hotset_turnover.py -- how fast does the hot set move?

    python3 src/analysis/hotset_turnover.py [--config spr-20t-ul] [--k 10000]

Why this exists
---------------
M5, NeoMem and Memstrata disagree about *which* problem is the reason software
tiering underperforms:

  M5         granularity  -- the 4 KB page is the wrong unit, because a page's
                             accesses concentrate in a few 64 B words
  NeoMem     timeliness   -- profiling is too slow and too coarse, so the OS is
                             always promoting yesterday's hot pages
  Memstrata  interference -- hardware tiering collapses under co-location

The profiler already answers M5's question (docs/methodology.md §7). It can answer
NeoMem's from the same data, because `.pages.bin` records per-page access counts
*per epoch*: if the top-K pages of one epoch are still the top-K pages of the next,
a slow profiler loses nothing and granularity is the binding constraint. If they
churn, no amount of sub-page resolution helps, because the information is stale
before it can be acted on.

That makes the two theses comparable on one workload with one instrument, which is
the question worth asking before choosing which paper to implement.

Metrics, per consecutive epoch pair, over the top-K hottest pages:

  retention   |top-K(t) INTERSECT top-K(t+1)| / K
              1.0 = the hot set is completely stable
              0.0 = it is entirely different next epoch

  jaccard     |A n B| / |A u B|, the symmetric version

  concent.    share of epoch t's accesses that land in epoch t's OWN top-K. This
              is the oracle bound: what a promoter with perfect, instantaneous
              information would capture. It measures how concentrated traffic is,
              nothing about staleness.

  coverage    share of epoch t+1's accesses that land in pages selected from
              epoch t. What a perfectly-executed but one-epoch-late promoter
              catches.

  staleness   coverage / concentration. This is the part attributable to *lag*
              alone, with the concentration of the workload divided out. 1.0 means
              acting on one-epoch-old information costs nothing; 0.5 means half the
              achievable benefit is lost purely to being late.

Separating these two matters. A low coverage can mean the hot set churned (a
timeliness problem, NeoMem's thesis) or simply that no small set of pages carries
much traffic (a problem no tiering system can fix). Only the first is an argument
for faster profiling.

A caveat worth stating: an epoch here is a fixed number of DRAM accesses, not a
fixed amount of time, and the promotion latency a real system pays is measured in
milliseconds. These numbers say how stable the hot set is *per unit of memory
traffic*; converting to "is a 1-second profiler fast enough" needs the miss rate.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402


def top_k_of_epoch(recs: np.ndarray, k: int) -> np.ndarray:
    """Page numbers of the k hottest pages in this epoch."""
    acc = (recs["reads"] + recs["writes"]).astype(np.int64)
    if acc.size == 0:
        return np.empty(0, np.uint64)
    idx = np.argpartition(acc, -k)[-k:] if acc.size > k else np.arange(acc.size)
    return recs["page"][idx]


def analyse(path: str, k: int) -> dict | None:
    recs = H.load_pages(path).records
    if recs.size == 0:
        return None
    epochs = np.unique(recs["epoch"])
    if epochs.size < 2:
        return {"epochs": int(epochs.size), "insufficient": True}

    by_epoch = {int(e): recs[recs["epoch"] == e] for e in epochs}
    retention, jaccard, coverage, concentration = [], [], [], []

    for a, b in zip(epochs[:-1], epochs[1:]):
        ra, rb = by_epoch[int(a)], by_epoch[int(b)]
        pa, pb = top_k_of_epoch(ra, k), top_k_of_epoch(rb, k)
        if pa.size == 0 or pb.size == 0:
            continue
        sa, sb = set(pa.tolist()), set(pb.tolist())
        inter = len(sa & sb)
        retention.append(inter / min(len(sa), len(sb)))
        jaccard.append(inter / len(sa | sb))

        # Operational view: of the accesses in epoch b, what share landed in pages
        # that epoch a would have told us to promote?
        acc_b = (rb["reads"] + rb["writes"]).astype(np.int64)
        total_b = acc_b.sum()
        if total_b:
            in_prev = np.isin(rb["page"], pa)   # selected one epoch late
            in_own = np.isin(rb["page"], pb)    # selected with perfect information
            coverage.append(float(acc_b[in_prev].sum()) / float(total_b))
            concentration.append(float(acc_b[in_own].sum()) / float(total_b))

    if not retention:
        return None
    cov = float(np.mean(coverage)) if coverage else float("nan")
    con = float(np.mean(concentration)) if concentration else float("nan")
    return {
        "epochs": int(epochs.size),
        "retention": float(np.mean(retention)),
        "retention_min": float(np.min(retention)),
        "jaccard": float(np.mean(jaccard)),
        "coverage": cov,
        "concentration": con,
        "staleness": (cov / con) if (con and con == con and con > 0) else float("nan"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t-ul")
    ap.add_argument("--k", type=int, default=10000,
                    help="hot-set size; M5 used up to 128K pages (512 MB)")
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    print(f"\nHot-set turnover between consecutive epochs, top-{args.k} pages")
    print(f"config: {args.config}\n")
    print(f"{'benchmark':<18}{'epochs':>7}{'retention':>10}{'worst':>7}"
          f"{'concent.':>10}{'coverage':>10}{'staleness':>11}")
    print("-" * 73)

    rows = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        bench = name[: -len(".pages.bin")]
        r = analyse(path, args.k)
        if r is None:
            continue
        if r.get("insufficient"):
            print(f"{bench:<18}{r['epochs']:>7}   (needs >=2 epochs to compare)")
            continue
        rows.append((bench, r))
        print(f"{bench:<18}{r['epochs']:>7}{r['retention']:>10.3f}"
              f"{r['retention_min']:>7.3f}{r['concentration']:>10.3f}"
              f"{r['coverage']:>10.3f}{r['staleness']:>11.3f}")

    if rows:
        print()
        print("retention  = share of this epoch's top-K still in the next epoch's top-K")
        print("concent.   = share of an epoch's accesses in its OWN top-K (oracle bound)")
        print("coverage   = same, but selected from the previous epoch (one epoch late)")
        print("staleness  = coverage / concent. -- the cost of lag with concentration")
        print("             divided out. 1.0 = being a step behind is free.")
        print()
        stable = [b for b, r in rows if r["staleness"] >= 0.9]
        churny = [b for b, r in rows if r["staleness"] < 0.7]
        if stable:
            print(f"Lag is nearly free (staleness >= 0.9): {', '.join(stable)}")
            print("  -> a slow profiler loses little here, so granularity is the binding")
            print("     constraint. That is M5's thesis.")
        if churny:
            print(f"Lag is expensive (staleness < 0.7): {', '.join(churny)}")
            print("  -> the hot set moves faster than a page can be promoted, so sub-page")
            print("     resolution buys little. That is NeoMem's thesis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
