#!/usr/bin/env python3
"""placement_study.py -- Deliverable 2: what is sub-page information actually worth?

    python3 src/analysis/placement_study.py [--config spr-20t] [--fast-frac 0.5]

The question
------------
M5's Hot Word Tracker exists to distinguish a *sparse* hot page (500 accesses
concentrated in 2 words) from a *dense* one (500 accesses over 40 words). The claim
is that the dense page is the better migration target, because the sparse one burns a
4 KB fast-tier frame to service 128 useful bytes.

That claim is testable. Given exact per-page and per-word counts, and a fast tier of
a fixed size, we can compare what different selection policies achieve:

  oracle        pick the pages with the most accesses *in the epoch being served*.
                Unachievable (it needs the future) but it bounds everything else.

  count-only    pick by the previous epoch's access count. This is HPT alone, and
                what AutoNUMA/DAMON approximate.

  hpt-driven    M5's HPT-driven Nominator (§5.2). Take the pages HPT reports, then
                annotate each with the 64-bit hot-word mask built from HWT's hot
                word addresses, and prefer the pages with more hot words set.
                M5's Guideline 3: "useful for applications with a mix of dense and
                sparse hot pages, such as roms and liblinear".

  hwt-driven    M5's HWT-driven Nominator (§5.2). Start from an *empty* page list and
                derive pages from hot word addresses alone; the mask population
                "serves as an access count". Ranks purely by how many hot words a
                page contains, ignoring the raw access count.
                M5's Guideline 4: "useful for applications with only sparse hot
                pages, such as Redis and Cachelib".

Getting these right matters. An earlier version of this script scored a
"density-aware" policy as count x (unique_words/64), which is *not* what M5 does and
is close to a strawman: with a page-granular fast tier every page costs 4096 bytes
regardless of density, so any monotone reweighting of a count-based ranking can only
lose hit rate. M5's nominators are different candidate-generation paths, not
reweightings, which is why they can win where a reweighting cannot.

Two metrics per policy:

  hit_rate      share of the epoch's accesses served from the fast tier. This is the
                thing that actually determines performance.

  useful_bytes  of the bytes migrated, the share that gets touched at all. Migrating
                a 4 KB page moves 4096 bytes; only unique_words x 64 are used.

The gap between count-only and density-aware IS the value of sub-page tracking, in
one number per workload. If it is zero, HWT is not worth its hardware for that
workload -- which is a result, not a failure.

Exact counts versus tracker output
---------------------------------
By default the non-oracle policies score pages by their *exact* previous-epoch access
count. That is generous: a real HPT is a bounded tracker whose counts are
approximations, and §1 of docs/hardware-evaluation.md measures how approximate
(access-count ratio ~0.75, set overlap near zero).

That generosity matters, because M5's HWT-driven nominator exists precisely to
compensate for an HPT that cannot resolve the hot set on its own. Giving the
count-only baseline perfect information removes the deficiency the nominator is
designed to cover, so a null result under exact counts says less than it appears to.

--tracker-csv switches the baseline to what a bounded tracker actually reported,
epoch by epoch, from <prefix>.topk.csv. Pages the tracker did not report score zero.
This is the fair test.

One sizing constraint: a tracker reporting K pages cannot fill a fast tier larger
than K. Run with --fast-frac small enough that capacity <= K, or the comparison
degenerates into "the tracker had nothing to say about 90% of the tier".

Caveat, stated up front: this is an open-loop trace study. Migrating a page changes
its latency, not its address, so the access stream stays valid -- but these are
placement-quality numbers, not runtime. A real speedup needs a timing simulator.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

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
    """hwt_words_per_page scales the HWT reporting budget: the hot-word list holds
    `capacity * hwt_words_per_page` words, i.e. that many hot words per fast-tier
    page on average. M5's HWT is bounded the same way."""
    recs = H.load_pages(path).records
    if recs.size == 0:
        return None
    epochs = np.unique(recs["epoch"])
    if epochs.size < 2:
        return None

    by_epoch = {int(e): recs[recs["epoch"] == e] for e in epochs}
    policies = ["oracle", "count-only", "hpt-driven", "hwt-driven"]
    hits = {p: [] for p in policies}
    useful = {p: [] for p in policies}

    for prev_e, cur_e in zip(epochs[:-1], epochs[1:]):
        prev, cur = by_epoch[int(prev_e)], by_epoch[int(cur_e)]
        if prev.size == 0 or cur.size == 0:
            continue

        # Fast tier sized as a fraction of the epoch's touched footprint. M5 caps DDR
        # so that "roughly 50% of the pages can be migrated", hence the 0.5 default.
        capacity = max(1, int(cur.size * fast_frac))

        cur_acc = (cur["reads"] + cur["writes"]).astype(np.float64)
        cur_total = cur_acc.sum()
        if cur_total <= 0:
            continue
        cur_words = H._popcount64(cur["mask"]).astype(np.float64)

        prev_acc = (prev["reads"] + prev["writes"]).astype(np.float64)
        prev_words = H._popcount64(prev["mask"]).astype(np.float64)
        prev_density = prev_words / 64.0

        # Map previous-epoch pages onto this epoch's page list.
        order = np.argsort(prev["page"])
        sp, sa, sd = prev["page"][order], prev_acc[order], prev_density[order]
        idx = np.searchsorted(sp, cur["page"])
        idx = np.clip(idx, 0, len(sp) - 1)
        known = (len(sp) > 0) & (sp[idx] == cur["page"])

        prev_count_on_cur = np.where(known, sa[idx], 0.0)

        if tracker is not None:
            # Replace the exact-count signal with the bounded tracker's ranking of the
            # *previous* epoch. Rank 0 scores highest; unreported pages score 0.
            t_prev = tracker.get(int(prev_e), {"hpt": [], "hwt": []})
            rank = {pg: len(t_prev["hpt"]) - i for i, pg in enumerate(t_prev["hpt"])}
            prev_count_on_cur = np.array(
                [float(rank.get(int(pg), 0)) for pg in cur["page"]], dtype=np.float64)

        # --- M5's hot-word list: the top-W words of the previous epoch, where W is
        # the HWT's reporting budget. A page's "mask population" is how many of its
        # own words appear in that list -- exactly the 64-bit mask M5 builds.
        pw = prev["words"].astype(np.int64)                     # (pages, 64)
        w_budget = max(1, int(capacity * hwt_words_per_page))
        flat = pw.ravel()
        if flat.size > w_budget:
            thresh = np.partition(flat, -w_budget)[-w_budget]
        else:
            thresh = 1
        thresh = max(thresh, 1)
        prev_hotword_pop = (pw >= thresh).sum(axis=1).astype(np.float64)

        so = prev_hotword_pop[order]
        prev_pop_on_cur = np.where(known, so[idx], 0.0)

        if tracker is not None:
            # HWT-driven under a bounded tracker: a page's score is how many of the
            # words the HWT actually reported fall inside it. This is M5's 64-bit
            # mask built from real hot-word addresses rather than from exact counts.
            t_prev = tracker.get(int(prev_e), {"hpt": [], "hwt": []})
            pop: dict[int, int] = {}
            for w in t_prev["hwt"]:
                pop[w >> 6] = pop.get(w >> 6, 0) + 1
            prev_pop_on_cur = np.array(
                [float(pop.get(int(pg), 0)) for pg in cur["page"]], dtype=np.float64)

        cand = {
            "oracle": cur_acc,
            "count-only": prev_count_on_cur,
            # HPT-driven: HPT supplies the candidates, the hot-word mask ranks them.
            # Pages HPT never reported are not candidates at all.
            "hpt-driven": np.where(
                prev_count_on_cur >= np.percentile(prev_count_on_cur[prev_count_on_cur > 0], 50)
                if np.any(prev_count_on_cur > 0) else False,
                prev_pop_on_cur, 0.0),
            # HWT-driven: candidates come from hot words alone; the mask population
            # is the score. Raw access count is not consulted.
            "hwt-driven": prev_pop_on_cur,
        }

        for name, score in cand.items():
            sel = select(score, capacity)
            hits[name].append(float(cur_acc[sel].sum()) / float(cur_total))
            # Of the bytes moved (capacity * 4096), how many are ever touched?
            moved = float(len(sel)) * PAGE_BYTES
            touched = float((cur_words[sel] * WORD_BYTES).sum())
            useful[name].append(touched / moved if moved else float("nan"))

    if not hits["oracle"]:
        return None
    return {
        "epochs": int(epochs.size),
        "hit": {p: float(np.mean(hits[p])) for p in policies},
        "useful": {p: float(np.mean(useful[p])) for p in policies},
    }


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
    print("'best gain' = better of M5's two nominators, minus count-only: the value")
    print("of sub-page information in the metric that determines performance.")
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
        print("\nNo workload here gains meaningfully from either M5 nominator at this")
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
