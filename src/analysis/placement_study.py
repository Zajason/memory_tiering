#!/usr/bin/env python3
"""Exploratory placement heuristics with previous-window-only candidate selection.

Policies named hpt-driven/hwt-driven retain legacy output keys but are not a
reproduction of M5 manager behavior, migration feedback, or bounded hardware.
Capacity is fixed from the first window; no current-window page list is visible
when choosing non-oracle placements. Archived CSVs predate this correction.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402
from causal_placement import candidates, choose, fixed_capacity

PAGE_BYTES = 4096
WORD_BYTES = 64


def select(scores: np.ndarray, capacity: int) -> np.ndarray:
    """Indices of the `capacity` highest-scoring pages."""
    if scores.size <= capacity:
        return np.arange(scores.size)
    return np.argpartition(scores, -capacity)[-capacity:]


def load_tracker_topk(path: str, budget: int | None = None) -> dict:
    """Parse <prefix>.topk.csv into {epoch: {"hpt": [pages], "hwt": [words]}}.

    Rank order is preserved, so rank 0 is the tracker's hottest. We deliberately do
    not dump the tracker's own count estimates: for selecting the top-C with C <= K,
    only the ordering matters, and rank is that ordering exactly."""
    import csv as _csv
    out: dict[int, dict[str, list[int]]] = {}
    budgets_seen = set()
    with open(path) as fh:
        for row in _csv.DictReader(fh):
            n = int(row["n"])
            budgets_seen.add(n)
            if budget is not None and n != budget:
                continue
            e = int(row["epoch"])
            out.setdefault(e, {"hpt": [], "hwt": []})[row["kind"]].append(int(row["key"]))
    if not out and budgets_seen:
        raise SystemExit(f"no rows for budget {budget}; file has {sorted(budgets_seen)}")
    return out


def evaluate(path: str, fast_frac: float, hwt_words_per_page: float = 8.0,
             tracker: dict | None = None) -> dict | None:
    recs = H.load_pages(path, require_complete=True, require_unsaturated=True).records
    epochs = np.unique(recs['epoch'])
    if len(epochs) < 2: return None
    capacity = fixed_capacity(recs, fast_frac)
    policies = ('oracle', 'count-only', 'hpt-driven', 'hwt-driven')
    captured = dict.fromkeys(policies, 0.)
    useful = dict.fromkeys(policies, 0.)
    allocated = dict.fromkeys(policies, 0.)
    total = 0.
    for a, b in zip(epochs[:-1], epochs[1:]):
        prev, cur = recs[recs['epoch']==a], recs[recs['epoch']==b]
        snapshot = tracker.get(int(a), {'hpt':[], 'hwt':[]}) if tracker is not None else None
        picked = candidates(prev, capacity, hwt_words_per_page, snapshot)
        acc = (cur['reads'] + cur['writes']).astype(float)
        picked['oracle'] = choose(cur['page'], acc, capacity)
        total += acc.sum()
        words = H._popcount64(cur['mask'])
        for policy, chosen in picked.items():
            mask = np.array([int(pg) in chosen for pg in cur['page']], dtype=bool)
            captured[policy] += acc[mask].sum()
            useful[policy] += words[mask].sum()*64
            allocated[policy] += len(chosen)*4096
    return {'epochs': len(epochs), 'capacity_pages': capacity,
            'hit': {p: captured[p]/total for p in policies},
            'useful': {p: useful[p]/allocated[p] if allocated[p] else float('nan') for p in policies}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t")
    ap.add_argument("--fast-frac", type=float, default=0.5,
                    help="fast tier as a fraction of the touched footprint "
                         "(M5 caps DDR so ~50%% of pages can be migrated)")
    ap.add_argument("--tracker-csv", default=None,
                    help="score from a bounded tracker's reported top-K instead of "
                         "exact counts; path may contain {bench}")
    ap.add_argument("--tracker-n", type=int, default=None,
                    help="which tracker budget N to use from the csv")
    ap.add_argument("--hwt-words", type=float, default=8.0,
                    help="HWT hot-word budget, as words per fast-tier page")
    ap.add_argument("--csv", default=None, help="also write a CSV here")
    args = ap.parse_args()
    print("Exploratory causal placement heuristics; not a reproduction of M5's migration policy.")

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    src = (f"bounded tracker (N={args.tracker_n})" if args.tracker_csv
           else "exact previous-epoch counts")
    print(f"\nPlacement quality, fast tier = {args.fast_frac:.0%} of the touched footprint")
    print(f"config: {args.config}   scores from: {src}\n")
    print(f"{'benchmark':<16}{'oracle':>9}{'count':>9}{'hpt-drv':>9}{'hwt-drv':>9}"
          f"{'  best gain':>12}")
    print("-" * 65)

    rows = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        bench = name[: -len(".pages.bin")]
        tr = None
        if args.tracker_csv:
            tcsv = args.tracker_csv.replace("{bench}", bench)
            if not os.path.exists(tcsv):
                print(f"  skipping {bench}: no {tcsv}", file=sys.stderr)
                continue
            tr = load_tracker_topk(tcsv, args.tracker_n)
        r = evaluate(path, args.fast_frac, args.hwt_words, tr)
        if r is None:
            continue
        h = r["hit"]
        gain = max(h["hpt-driven"], h["hwt-driven"]) - h["count-only"]
        rows.append((bench, r, gain))
        print(f"{bench:<16}{h['oracle']:>9.3f}{h['count-only']:>9.3f}"
              f"{h['hpt-driven']:>9.3f}{h['hwt-driven']:>9.3f}{gain:>+12.3f}")

    if not rows:
        print("no usable data", file=sys.stderr)
        return 1

    print()
    print("Columns are the share of an epoch's accesses served from the fast tier.")
    print("'best gain' compares these heuristics only; it is not a verdict on M5.")
    print()
    print(f"{'benchmark':<16}{'useful bytes / migrated bytes (count-only policy)':<50}")
    print("-" * 65)
    for bench, r, _ in rows:
        u = r["useful"]["count-only"]
        print(f"{bench:<16}{u:>8.3f}   -> {(1-u)*100:.0f}% of every migrated page is "
              f"never touched")

    best = max(rows, key=lambda x: x[2])
    worst = min(rows, key=lambda x: x[2])
    print()
    print(f"Largest HWT gain: {best[0]} {best[2]:+.3f}")
    print(f"Smallest:         {worst[0]} {worst[2]:+.3f}")
    if abs(best[2]) < 0.02:
        print("\nNeither word-based heuristic gains meaningfully in these observations.")
        print("fast-tier size. Consistent with the top-K finding: the pages a policy")
        print("would migrate are already dense, so HWT has little to correct.")

    if args.csv:
        with open(args.csv, "w") as fh:
            fh.write("benchmark,policy,hit_rate,useful_byte_frac\n")
            for bench, r, _ in rows:
                for p in r["hit"]:
                    fh.write(f"{bench},{p},{r['hit'][p]:.6f},{r['useful'][p]:.6f}\n")
        print(f"\ncsv -> {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
