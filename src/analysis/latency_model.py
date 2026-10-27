#!/usr/bin/env python3
"""Serial memory-cost model over a fixed observed stream, not measured speedup.

Cost = fast accesses * fast latency + slow accesses * slow latency + promotions
* migration cost. Latencies and migration cost are assumptions. There is no CPU
execution, memory-level parallelism, bandwidth contention or migration feedback.
Consequently the ratio is neither application speedup nor a proven upper bound.
The non-oracle policies use only the previous window. Archived CSVs used future
page membership and must not be cited as corrected results.
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


def evaluate(path: str, fast_frac: float, l_fast: float, l_slow: float,
             l_mig: float, hwt_words_per_page: float = 8.0) -> dict | None:
    recs = H.load_pages(path, require_complete=True, require_unsaturated=True).records
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
    capacity = fixed_capacity(recs, fast_frac)

    for prev_e, cur_e in zip(epochs[:-1], epochs[1:]):
        prev, cur = by_epoch[int(prev_e)], by_epoch[int(cur_e)]
        if prev.size == 0 or cur.size == 0:
            continue

        cur_acc = (cur["reads"] + cur["writes"]).astype(np.float64)
        cur_tot = cur_acc.sum()
        if cur_tot <= 0:
            continue
        total_acc += cur_tot

        cand = candidates(prev, capacity, hwt_words_per_page)
        cand['oracle'] = choose(cur['page'], cur_acc, capacity)

        for name in policies:
            if name == "all-CXL":
                stall[name] += cur_tot * l_slow
                continue
            if name == "all-local":
                # Upper bound: everything already local, nothing to migrate.
                stall[name] += cur_tot * l_fast
                continue
            chosen = cand[name]
            new = chosen - resident[name]
            migs[name] += len(new)
            resident[name] = chosen

            hit = np.array([int(pg) in chosen for pg in cur['page']], dtype=bool)
            fast = float(cur_acc[hit].sum())
            slow = float(cur_tot) - fast
            stall[name] += fast * l_fast + slow * l_slow + len(new) * l_mig

    if total_acc <= 0:
        return None
    amat = {p: stall[p] / total_acc for p in policies}
    base = amat["all-CXL"]
    return {
        "epochs": int(epochs.size),
        "capacity_pages": capacity,
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

    print(f"\nIllustrative serial memory cost (not measured stall time or speedup)")
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
