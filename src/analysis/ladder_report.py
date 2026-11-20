#!/usr/bin/env python3
"""Score the window ladder against M5 Figure 4 without choosing a window per curve.

The pintool records, in one pass, the touched-word histogram for every window
length epoch*2^j (see paired_observer.hpp). This script reports each level and
then asks the only question that is not a per-benchmark fit:

    if ONE window length is used for every benchmark, and that length is chosen
    using the OTHER benchmarks only, how far is the held-out benchmark from M5?

That leave-one-out error is evidence. The per-benchmark best level is printed
too, labelled as what it is: a fitted lower bound.

usage: ladder_report.py DIR [DIR...]      (each DIR holds gapbs-*.paired.csv)
"""
import csv, json, sys
from pathlib import Path

NS = [4, 8, 16, 32, 48]
M5 = {  # digitised from Figure 4; identical to hotskew.M5_FIGURE4
    "bc":   [0.005, 0.02, 0.04, 0.09, 0.145],
    "bfs":  [0.05, 0.11, 0.17, 0.26, 0.345],
    "cc":   [0.06, 0.125, 0.20, 0.29, 0.385],
    "pr":   [0.00, 0.00, 0.005, 0.01, 0.02],
    "sssp": [0.005, 0.015, 0.025, 0.07, 0.11],
    "tc":   [0.02, 0.05, 0.12, 0.265, 0.52],
}


def load(path, stream="traffic", population="own"):
    """-> {level: (cdf, page_observations, windows)}; level 0 = one epoch,
    'whole' = the entire collection. Tails are merged only where a level has no
    complete window, because a lone remainder is then all the data there is."""
    hist, wins, tails = {}, {}, {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["stream"] != stream or r["population"] != population:
                continue
            sc = r["scope"]
            if sc == "epoch":
                continue
            key = {"pooled": 0, "whole": "whole"}.get(sc)
            if sc in ("ladder", "tail"):
                key = int(r["epoch"])
            target = tails if sc == "tail" else hist
            target.setdefault(key, [0] * 65)[int(r["words"])] += int(r["pages"])
            if sc == "ladder":
                wins[key] = int(r["events"])
            elif sc == "pooled":
                wins[key] = int(r["epoch"])
    out = {}
    for k, h in hist.items():
        t = sum(h[1:])
        if t:
            out[k] = ([sum(h[1:n + 1]) / t for n in NS], t, wins.get(k, 1))
    return out


def err(c, w):
    return max(abs(a - b) for a, b in zip(c, M5[w]))


PARTIAL = set()


def main():
    data = {}
    for d in map(Path, sys.argv[1:]):
        for f in sorted(d.glob("gapbs-*.paired.csv")):
            w = f.name.split("-")[1].split(".")[0]
            got = load(f)
            if not got and f.with_name(f"gapbs-{w}.ladder.csv").exists():
                # Interrupted run: fall back to the last periodic snapshot.
                got = load(f.with_name(f"gapbs-{w}.ladder.csv"))
                PARTIAL.add((d.name, w))
            data[(d.name, w)] = got
    report = {}
    for case in sorted({c for c, _ in data}):
        ws = [w for c, w in data if c == case]
        print(f"\n== {case}")
        print("wl    level  windows  " + "  ".join(f"N<={n:<2}" for n in NS) + "   maxerr")
        for w in ws:
            print(f"{w:5} M5              " + "  ".join(f"{x:.3f}" for x in M5[w]))
            for k, (c, t, n) in sorted(data[(case, w)].items(), key=lambda kv: (kv[0] == "whole", kv[0] if kv[0] != "whole" else 0)):
                print(f"      {str(k):>5}  {n:7}  " + "  ".join(f"{x:.3f}" for x in c) + f"   {err(c, w):.3f}")
        levels = [k for k in range(0, 11)] + ["whole"]
        table = {w: {k: err(v[0], w) for k, v in data[(case, w)].items()} for w in ws}
        common = [k for k in levels if all(k in table[w] for w in ws)]
        print(f"-- one window for all benchmarks (levels every benchmark reached: {common})")
        res = {}
        for w in ws:
            others = [o for o in ws if o != w]
            if not others or not common:
                continue
            pick = min(common, key=lambda k: sum(table[o][k] for o in others) / len(others))
            best = min(table[w], key=lambda k: table[w][k])
            res[w] = dict(loo_level=pick, loo_error=table[w][pick], epoch_error=table[w].get(0),
                          whole_error=table[w].get("whole"), fitted_level=best, fitted_error=table[w][best])
            print(f"   {w:5} held out: others choose level {pick!s:>5} -> error {table[w][pick]:.3f}"
                  f"   | 10M epoch {table[w].get(0, float('nan')):.3f}  whole {table[w].get('whole', float('nan')):.3f}"
                  f"  fitted-best {table[w][best]:.3f}@{best}")
        if res:
            print(f"   mean leave-one-out error {sum(r['loo_error'] for r in res.values()) / len(res):.3f}"
                  f"   (10M epoch: {sum(r['epoch_error'] for r in res.values()) / len(res):.3f})")
        report[case] = res
    if "--json" in sys.argv:
        print(json.dumps(report))


if __name__ == "__main__":
    main()
