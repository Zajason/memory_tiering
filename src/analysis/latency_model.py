#!/usr/bin/env python3
"""latency_model.py -- close the loop: turn placement quality into a time number.

    python3 src/analysis/latency_model.py [--config spr-20t] [--fast-frac 0.5]

Everything else in this repository reports *distributions* -- how sparse a page is,
how good a tracker's top-K is, what share of accesses a policy captures. None of that
is a performance number, and "we characterised the problem" is a weaker claim than
"policy X cuts memory stall time by Y%".

This turns the placement results into time, using an analytical latency model over
the DRAM access stream the profiler already recorded.

The model
---------
Each DRAM access costs one of two latencies depending on where its page lives, and
each promotion costs a fixed migration penalty:

    stall_time = hits_fast x L_fast
               + hits_slow x L_slow
               + migrations x L_migrate

    AMAT       = stall_time / total_accesses

Defaults come from the papers rather than from thin air:

    L_fast      100 ns   NeoMem Fig. 1 puts local DDR at ~100 ns and measures 118 ns
    L_slow      220 ns   Memstrata: CXL is "roughly 200-220% the latency of the local
                         memory". NeoMem: the field "tends to assume a CXL-memory
                         latency of 170-250ns". 220 ns sits in both.
    L_migrate     3 us   a 4 KB page copy plus TLB shootdown and page-table work.
                         This is the literature's order of magnitude for
                         migrate_pages(), not something measured here -- sweep it
                         with --migrate-ns and see --sensitivity.

What this is NOT
----------------
This is an analytical model over a trace, not a timing simulation. Three assumptions,
all of which inflate the apparent benefit and none of which are hidden:

 1. **No memory-level parallelism.** Real cores overlap misses; a 2.2x latency ratio
    does not translate to 2.2x stall time when several misses are in flight. This is
    the big one, and it means the numbers here are an *upper bound* on the benefit.
 2. **No bandwidth contention.** Migration traffic competes with demand traffic for
    the same channels; that is not modelled.
 3. **Placement-independent access stream.** True for addresses -- migration changes
    a page's latency, not which addresses are touched -- but it breaks for anything
    whose behaviour depends on timing (a server under load, lock contention).

So: report these as *memory stall time*, and as a bound. Converting to application
speedup needs the fraction of runtime spent stalled on memory, which is why
--stall-frac exists and why it is not applied by default.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402
from placement_study import select  # noqa: E402

PAGE_BYTES = 4096


def evaluate(path: str, fast_frac: float, l_fast: float, l_slow: float,
             l_mig: float, hwt_words_per_page: float = 8.0) -> dict | None:
    recs = H.load_pages(path).records
    if recs.size == 0:
        return None
    epochs = np.unique(recs["epoch"])
    if epochs.size < 2:
        return None

    by_epoch = {int(e): recs[recs["epoch"] == e] for e in epochs}
    policies = ["all-CXL", "all-local", "oracle", "count-only", "hpt-driven", "hwt-driven"]
    stall = {p: 0.0 for p in policies}
    migs = {p: 0 for p in policies}
    total_acc = 0.0
    # Pages resident in the fast tier, carried across epochs so a promotion is only
    # paid for once. Without this every epoch re-migrates everything and migration
    # cost is meaningless.
    resident = {p: set() for p in policies}

    for prev_e, cur_e in zip(epochs[:-1], epochs[1:]):
        prev, cur = by_epoch[int(prev_e)], by_epoch[int(cur_e)]
        if prev.size == 0 or cur.size == 0:
            continue

        capacity = max(1, int(cur.size * fast_frac))
        cur_acc = (cur["reads"] + cur["writes"]).astype(np.float64)
        cur_tot = cur_acc.sum()
        if cur_tot <= 0:
            continue
        total_acc += cur_tot

        prev_acc = (prev["reads"] + prev["writes"]).astype(np.float64)
        prev_words = H._popcount64(prev["mask"]).astype(np.float64)

        order = np.argsort(prev["page"])
        sp, sa = prev["page"][order], prev_acc[order]
        idx = np.clip(np.searchsorted(sp, cur["page"]), 0, max(len(sp) - 1, 0))
        known = (len(sp) > 0) & (sp[idx] == cur["page"])
        prev_count_on_cur = np.where(known, sa[idx], 0.0)

        pw = prev["words"].astype(np.int64)
        w_budget = max(1, int(capacity * hwt_words_per_page))
        flat = pw.ravel()
        thresh = max(int(np.partition(flat, -w_budget)[-w_budget]) if flat.size > w_budget else 1, 1)
        pop = (pw >= thresh).sum(axis=1).astype(np.float64)
        so = pop[order]
        prev_pop_on_cur = np.where(known, so[idx], 0.0)

        pos = prev_count_on_cur[prev_count_on_cur > 0]
        med = np.percentile(pos, 50) if pos.size else 0.0
        cand = {
            "oracle": cur_acc,
            "count-only": prev_count_on_cur,
            "hpt-driven": np.where(prev_count_on_cur >= med, prev_pop_on_cur, 0.0),
            "hwt-driven": prev_pop_on_cur,
        }

        for name in policies:
            if name == "all-CXL":
                stall[name] += cur_tot * l_slow
                continue
            if name == "all-local":
                # Upper bound: everything already local, nothing to migrate.
                stall[name] += cur_tot * l_fast
                continue
            sel = select(cand[name], capacity)
            chosen = set(cur["page"][sel].tolist())
            new = chosen - resident[name]
            migs[name] += len(new)
            resident[name] = chosen

            hit = np.zeros(cur.shape[0], dtype=bool)
            hit[sel] = True
            fast = float(cur_acc[hit].sum())
            slow = float(cur_tot) - fast
            stall[name] += fast * l_fast + slow * l_slow + len(new) * l_mig

    if total_acc <= 0:
        return None
    amat = {p: stall[p] / total_acc for p in policies}
    base = amat["all-CXL"]
    return {
        "epochs": int(epochs.size),
        "accesses": total_acc,
        "amat": amat,
        "speedup": {p: base / amat[p] for p in policies},
        "migrations": migs,
        # What share of the achievable gain (all-CXL -> all-local) each policy gets.
        "closed": {p: (base - amat[p]) / (base - amat["all-local"])
                   for p in policies if amat["all-local"] < base},
        "mig_share": {p: (migs[p] * l_mig) / stall[p] if stall[p] else 0.0
                      for p in policies if p not in ("all-CXL", "all-local")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t")
    ap.add_argument("--fast-frac", type=float, default=0.5)
    ap.add_argument("--fast-ns", type=float, default=100.0, help="local DDR latency")
    ap.add_argument("--slow-ns", type=float, default=220.0, help="CXL latency")
    ap.add_argument("--migrate-ns", type=float, default=3000.0,
                    help="cost of promoting one 4 KB page")
    ap.add_argument("--stall-frac", type=float, default=None,
                    help="if given, also report application speedup assuming this "
                         "fraction of runtime is memory stall (Amdahl)")
    ap.add_argument("--sensitivity", action="store_true",
                    help="sweep the migration cost, which is the least certain input")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    print(f"\nMemory stall time under a two-tier latency model")
    print(f"config: {args.config}   fast tier = {args.fast_frac:.0%} of footprint")
    print(f"L_fast = {args.fast_ns:.0f} ns   L_slow = {args.slow_ns:.0f} ns "
          f"({args.slow_ns/args.fast_ns:.1f}x)   L_migrate = {args.migrate_ns/1000:.1f} us\n")

    hdr = (f"{'benchmark':<14}{'AMAT ns':>9}{'speedup':>9}{'vs local':>9}"
           f"{'gap closed':>12}{'mig cost':>10}")
    rows = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".pages.bin"):
            continue
        path = os.path.join(d, name)
        if os.path.getsize(path) == 0:
            continue
        bench = name[: -len(".pages.bin")]
        r = evaluate(path, args.fast_frac, args.fast_ns, args.slow_ns, args.migrate_ns)
        if r is None:
            continue
        rows.append((bench, r))

    if not rows:
        print("no usable data", file=sys.stderr)
        return 1

    print("Best realisable policy (count-only, i.e. HPT alone):\n")
    print(hdr)
    print("-" * len(hdr))
    for bench, r in rows:
        p = "count-only"
        print(f"{bench:<14}{r['amat'][p]:>9.1f}{r['speedup'][p]:>8.2f}x"
              f"{r['speedup']['all-local']:>8.2f}x{r['closed'][p]:>11.0%}"
              f"{r['mig_share'][p]:>9.1%}")

    gm = np.exp(np.mean([np.log(r["speedup"]["count-only"]) for _, r in rows]))
    gmo = np.exp(np.mean([np.log(r["speedup"]["oracle"]) for _, r in rows]))
    gml = np.exp(np.mean([np.log(r["speedup"]["all-local"]) for _, r in rows]))
    print()
    print(f"  geomean speedup vs all-CXL:  count-only {gm:.3f}x   "
          f"oracle {gmo:.3f}x   all-local (bound) {gml:.3f}x")

    print("\n\nAll policies, geomean speedup vs all-CXL:\n")
    print(f"  {'policy':<14}{'speedup':>9}{'gap closed':>13}")
    print("  " + "-" * 36)
    for p in ["all-local", "oracle", "count-only", "hpt-driven", "hwt-driven"]:
        g = np.exp(np.mean([np.log(r["speedup"][p]) for _, r in rows]))
        c = np.mean([r["closed"][p] for _, r in rows])
        print(f"  {p:<14}{g:>8.3f}x{c:>12.0%}")

    if args.stall_frac is not None:
        f = args.stall_frac
        print(f"\nApplication speedup, assuming {f:.0%} of runtime is memory stall "
              f"(Amdahl):")
        for p in ["oracle", "count-only"]:
            g = np.exp(np.mean([np.log(r["speedup"][p]) for _, r in rows]))
            app = 1.0 / ((1 - f) + f / g)
            print(f"  {p:<14}{app:>8.3f}x")
        print("  (this multiplies one modelled quantity by one assumed one -- treat")
        print("   it as an order of magnitude, not a measurement)")

    if args.sensitivity:
        print("\n\nSensitivity to migration cost, the least certain input")
        print("(geomean speedup of count-only vs all-CXL):\n")
        print(f"  {'L_migrate':<12}{'speedup':>9}{'migration share of stall':>28}")
        print("  " + "-" * 48)
        for mig in [0, 1000, 3000, 10000, 30000]:
            sub = []
            share = []
            for bench, _ in rows:
                rr = evaluate(os.path.join(d, bench + ".pages.bin"), args.fast_frac,
                              args.fast_ns, args.slow_ns, float(mig))
                if rr:
                    sub.append(rr["speedup"]["count-only"])
                    share.append(rr["mig_share"]["count-only"])
            if sub:
                print(f"  {mig/1000:>6.0f} us  {np.exp(np.mean(np.log(sub))):>10.3f}x"
                      f"{np.mean(share):>26.1%}")

    print("\nCaveats: no memory-level parallelism, no bandwidth contention, open-loop")
    print("trace. These are upper bounds on the benefit. See the module docstring.")

    if args.csv:
        with open(args.csv, "w") as fh:
            fh.write("benchmark,policy,amat_ns,speedup_vs_allcxl,gap_closed,migrations\n")
            for bench, r in rows:
                for p in r["amat"]:
                    fh.write(f"{bench},{p},{r['amat'][p]:.3f},{r['speedup'][p]:.4f},"
                             f"{r['closed'].get(p, float('nan')):.4f},{r['migrations'][p]}\n")
        print(f"\ncsv -> {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
