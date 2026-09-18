#!/usr/bin/env python3
"""Compare the full-system simulator's Figure 4 against Pin and against M5.

    ./.venv/bin/python src/analysis/compare_sim.py \
        --sim results/simcxl/hotskew-bc --workload bc

Three columns, because the interesting question is not "does the simulator match
M5" on its own -- it is whether moving from Pin to a full-system simulator moves
us TOWARD M5, and by how much.

  M5        digitised from the paper's Figure 4 bar chart (+/-0.02)
  Pin       our pintool, results/spr-20t-ul (GAPBS) or spr-20t (liblinear)
  gem5      the probe in MemCtrl::recvTimingReq -- physical addresses, and
            kernel traffic included

The Pin column is where we disagreed with M5 (bc 0.493, sssp 0.433, liblinear
0.577 max error). The kernel blind spot is the leading explanation, and the
simulator is the only instrument here that does not have one -- so if that
explanation is right, the gem5 column should land closer to M5 than Pin does.
A result that does NOT move is just as publishable: it refutes the explanation.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hotskew as H  # noqa: E402

PIN_PATH = {
    "bc": "results/spr-20t-ul/gapbs-bc.summary.txt",
    "sssp": "results/spr-20t-ul/gapbs-sssp.summary.txt",
    "liblinear": "results/spr-20t/liblinear.summary.txt",
}
M5_KEY = {"bc": "gapbs-bc", "sssp": "gapbs-sssp", "liblinear": "liblinear"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True, help="gem5 probe summary file")
    ap.add_argument("--workload", required=True, choices=sorted(PIN_PATH))
    a = ap.parse_args()

    if not os.path.exists(a.sim):
        sys.exit(f"no simulator summary at {a.sim}")

    sim = H.figure4_from_summary(a.sim)
    m5 = H.M5_FIGURE4[M5_KEY[a.workload]]
    pin = (
        H.figure4_from_summary(PIN_PATH[a.workload])
        if os.path.exists(PIN_PATH[a.workload])
        else None
    )

    print(f"\nFigure 4 -- P(unique 64B words per 4KB page <= N),  {a.workload}\n")
    print(f"{'N':>5} {'M5':>8} {'Pin':>8} {'gem5':>8} {'|Pin-M5|':>9} {'|gem5-M5|':>10}")
    print("-" * 52)
    worst_pin = worst_sim = 0.0
    for n in H.FIG4_N:
        dp = abs(pin[n] - m5[n]) if pin else float("nan")
        ds = abs(sim[n] - m5[n])
        worst_pin = max(worst_pin, dp if dp == dp else 0.0)
        worst_sim = max(worst_sim, ds)
        print(f"{n:>5} {m5[n]:>8.3f} "
              f"{(pin[n] if pin else float('nan')):>8.3f} {sim[n]:>8.3f} "
              f"{dp:>9.3f} {ds:>10.3f}")
    print("-" * 52)
    print(f"{'max':>5} {'':>8} {'':>8} {'':>8} {worst_pin:>9.3f} {worst_sim:>10.3f}")

    print()
    if worst_sim < worst_pin:
        print(f"gem5 is CLOSER to M5 than Pin ({worst_sim:.3f} vs {worst_pin:.3f}). "
              "Consistent with the kernel blind spot explaining the gap.")
    elif worst_sim > worst_pin:
        print(f"gem5 is FARTHER from M5 than Pin ({worst_sim:.3f} vs {worst_pin:.3f}). "
              "The kernel blind spot does not explain this workload's gap.")
    else:
        print("gem5 and Pin are equally far from M5.")

    meta = H.load_summary(a.sim)
    print(f"\nsimulator run: {meta.get('epochs','?')} epoch(s), "
          f"{meta.get('dram_accesses','?')} DRAM accesses, "
          f"mean words/page {meta.get('mean_unique_words','?')}")


if __name__ == "__main__":
    main()
