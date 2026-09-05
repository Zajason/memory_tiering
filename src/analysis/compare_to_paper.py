#!/usr/bin/env python3
"""compare_to_paper.py -- tabulate our Figure 4 numbers against M5's.

    python3 src/analysis/compare_to_paper.py [--config spr-20t] [--markdown]

Prints one row per benchmark: our P(<=N) for each N alongside the value read off
M5's published Figure 4, and the difference. Benchmarks we did not run are listed
separately rather than silently omitted, so the coverage of the reproduction is
visible in the same place as its accuracy.

M5's values are graph-digitised from the paper's bar chart -- no numeric data was
released with the artifact -- so differences below about 0.02 are not meaningful.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

GREEN, YELLOW, RED, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"
DIGITISATION_ERROR = 0.02


def verdict(delta: float) -> tuple[str, str]:
    a = abs(delta)
    if a <= 0.05:
        return "match", GREEN
    if a <= 0.20:
        return "close", YELLOW
    return "differs", RED


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results")
    ap.add_argument("--config", default="spr-20t")
    ap.add_argument("--markdown", action="store_true", help="emit a markdown table")
    args = ap.parse_args()

    d = os.path.join(args.results, args.config)
    if not os.path.isdir(d):
        print(f"no results under {d}", file=sys.stderr)
        return 1

    rows, no_data = [], []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".summary.txt"):
            continue
        bench = name[: -len(".summary.txt")]
        path = os.path.join(d, name)
        meta = H.load_summary(path)
        if meta.get("STATUS") == "NO DATA":
            no_data.append(bench)
            continue
        ours = H.figure4_from_summary(path)
        theirs = H.M5_FIGURE4.get(bench)
        rows.append((bench, ours, theirs, meta))

    if not rows:
        print("no usable results", file=sys.stderr)
        return 1

    if args.markdown:
        print(f"| benchmark | N | this work | M5 Fig. 4 | delta |")
        print("|---|---|---|---|---|")
        for bench, ours, theirs, _ in rows:
            for n in H.FIG4_N:
                t = f"{theirs[n]:.3f}" if theirs else "—"
                dl = f"{ours[n] - theirs[n]:+.3f}" if theirs else "—"
                print(f"| {bench} | {n} | {ours[n]:.3f} | {t} | {dl} |")
        return 0

    print(f"\nFigure 4 -- P(4 KB page has at most N unique 64 B words accessed)")
    print(f"config: {args.config}\n")
    hdr = f"{'benchmark':<14}{'N':>4}  {'ours':>7} {'M5':>7} {'delta':>8}   verdict"
    print(hdr)
    print("-" * len(hdr))
    for bench, ours, theirs, meta in rows:
        for i, n in enumerate(H.FIG4_N):
            label = bench if i == 0 else ""
            if theirs is None:
                print(f"{label:<14}{n:>4}  {ours[n]:>7.3f} {'—':>7} {'—':>8}   not in Fig. 4")
                continue
            delta = ours[n] - theirs[n]
            v, colour = verdict(delta)
            print(f"{label:<14}{n:>4}  {ours[n]:>7.3f} {theirs[n]:>7.3f} "
                  f"{delta:>+8.3f}   {colour}{v}{RESET}")
        mu = meta.get("mean_unique_words", "?")
        ep = meta.get("epochs", "?")
        win = meta.get("epoch_len_ins") or meta.get("epoch_len_dram_acc", "?")
        kind = "ins" if meta.get("epoch_len_ins") else "dram acc"
        print(f"{'':<14}      mean unique words {mu}, {ep} epochs "
              f"of {win} {kind}")
        print()

    if no_data:
        print(f"runs that produced no data: {', '.join(no_data)}")
    missing = [b for b in H.M5_FIGURE4 if b not in {r[0] for r in rows}]
    if missing:
        print(f"in M5 Figure 4 but not run here: {', '.join(sorted(missing))}")
    print(f"\nM5 values are digitised from the published bar chart; "
          f"differences under {DIGITISATION_ERROR} are not meaningful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
