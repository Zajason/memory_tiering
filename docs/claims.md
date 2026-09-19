# Claims ledger

Every headline number in this repository, with the command that regenerates it and the
file it comes from.

**Why this file exists.** Several claims were revised as the work progressed — the
accuracy summary, the Count-Min result, and the measurement-window story twice. Each
revision left stale copies in other documents, and a reader finding two different
numbers for the same quantity has no way to know which is current. This is the single
source of truth: **if a number elsewhere disagrees with this table, this table wins and
the other document is a bug.**

Verify the whole table with:

```bash
./experiments/check_claims.sh
```

---

## Calibration

| claim | value | source |
|---|---|---|
| stride 4096 B → words/page | 1.000 (analytic 1) | `run_validation.sh` |
| stride 1024 B | 3.999 (analytic 4) | " |
| stride 256 B | 15.996 (analytic 16) | " |
| stride 64 B | 63.981 (analytic 64) | " |
| 10% dense mixture, mean | 7.301 (analytic 7.300) | " |
| 10% dense mixture, P(≤4) | 0.9000 (analytic 0.900) | " |

## Reproduction of M5 Figure 4

Scored as **max error across all five N**, not at a single point. `spr-20t-ul` for
GAPBS, `spr-1t` for Redis, `spr-20t` for liblinear.

| workload | max err | verdict | source |
|---|---|---|---|
| PageRank | 0.014 | reproduced | `compare_to_paper.py --config spr-20t-ul` |
| Triangle counting | 0.030 | reproduced | " |
| CC | 0.082 | close | " |
| Redis (YCSB-A) | 0.085 | close | `--config spr-1t` |
| BFS | 0.095 | close | `--config spr-20t-ul` |
| SSSP | 0.433 | disagrees | " |
| BC | 0.493 | disagrees | " |
| liblinear | 0.577 | disagrees | `--config spr-20t` |

**Do not quote "within 0.03" without saying across what.** At N=48 alone five
workloads are within 0.03, but N=48 is where the CDF has nearly saturated and is the
cheapest point to agree at.

## Kernel blind spot

| claim | value | source |
|---|---|---|
| 512 MiB via `read(2)`, DRAM accesses seen | 5 | `kernel_blindspot.c` |
| 512 MiB via `memcpy`, DRAM accesses seen | 24,838,154 | " |
| …words/page | 63.999 / 64 | " |
| BFS P(≤48), kernel copies the graph | 0.813 | `results/spr-20t/` |
| BFS P(≤48), user-space copy | 0.320 | `results/spr-20t-ul/` |
| M5's published value | 0.345 | digitised |
| attribution: ROI off | 1.8 of 28.6 words | report §4.2 |
| attribution: load visibility | 26.7 of 28.6 words | " |

## Bounded trackers (M5 Figure 8)

Space-Saving, K=128, ASLR pinned. **Count-Min is corrected but still slightly
non-monotone on `cc`; do not present that curve as clean.**

| claim | value | source |
|---|---|---|
| BFS, N=128 (1 KB SRAM) | 0.757 | `run_trackers.sh` |
| BFS, N=8192 (68 KB) | 0.767 | " |
| CC, N=128 | 0.657 | " |
| Count-Min BFS, N=8192 | 0.302 | " |
| cold-tail sizing law | N > n_hot + n_cold/hits | `hotskew_sim --self-test` |
| …measured: 256 entries | 0.002 | " |
| …512 entries | 1.000 | " |

## Placement and latency

| claim | value | source |
|---|---|---|
| best nominator gain, exact counts | −0.015 (BFS) | `placement_study.py` |
| best nominator gain, HPT N=16384 | −0.049 (BFS) | `--tracker-csv` |
| wasted bytes/page, Redis | 81% | `placement_study.py --config spr-1t` |
| geomean stall-time speedup, count-only | 1.505× | `latency_model.py` |
| gap to all-local closed | 61% | " |
| speedup at 30 µs migration | 0.835× (net loss) | `--sensitivity` |

**The speedup is memory *stall time* with no memory-level parallelism modelled.** It
is an upper bound, not an application speedup.

## Failure-mode comparison

| claim | value | source |
|---|---|---|
| staleness, tc / pr (K=128k) | 0.902 / 0.381 | `hotset_turnover.py --k 128000` |
| P(≤16 words), top-10k pages | 0.000 all kernels | `placement_study.py` |
| top-4-word share, Redis vs graph | 0.458 vs ≤0.162 | summaries |

## Granularity sweep

| claim | value | source |
|---|---|---|
| waste 4 KB → 2 MB, bc | 51% → 76% | `granularity_sweep.py` |
| waste 4 KB → 2 MB, pr | 1% → 5% | " |
| saturation point | ~64 KB | " |
| 512 B tracker overstates Redis by | 2.51× | " |
| …overstates PageRank by | 1.01× | " |

## Full-system campaign (gem5 23.1, probe at MemCtrl::recvTimingReq)

Single core, 48kB/12 L1d, 2MB/16 L2, 36MB/9 L3 (= spr-20t), kron-23, measurement
from the CPU switch onward so the data load is included. Scored as max error
across all five N, same as the Pin column.

| workload | Pin vs M5 | gem5 vs M5 | moved | source |
|---|---|---|---|---|
| sssp | 0.433 | **0.391** | −0.042 | `compare_sim.py --workload sssp` |
| bc | 0.493 | **0.331** | −0.162 | `compare_sim.py --workload bc` |
| liblinear | 0.577 | running | — | 19 GB guest, `--big-mem` |

| claim | value | source |
|---|---|---|
| sssp: epochs / DRAM accesses | 45 / 447,210,722 | `results/simcxl/` |
| sssp: mean words/page | 48.278 / 64 | " |
| bc: epochs / DRAM accesses | 46 / 451,441,535 | " |
| bc: mean words/page | 46.851 / 64 | " |

**Both moved toward M5, neither reached it.** The kernel blind spot is real and
is worth 0.042 (sssp) and 0.162 (bc), but it is not the whole explanation. The
residual is concentrated at small N: M5 reports P(<=4) = 0.005 while we measure
0.135 (sssp) and 0.109 (bc) — we still see a population of sparsely-touched
pages that M5 does not. That is the shape the **measurement-window** ambiguity
predicts (counters reset every 10M accesses here; M5's accumulate), and a
single-window run is queued to test it.

## Simulator port (SimCXL / CXL-DMSim, gem5 23.1)

| claim | value | source |
|---|---|---|
| builds on Ubuntu 26.04 / gcc 15 / Python 3.14 | yes, 0 errors | `src/sim/simcxl/README.md` |
| linear 64B sweep, mean words/page | 63.968 / 64 | `cxl_hotskew_test.py` |
| …accesses == unique lines | 30,321 == 473x64+49 | " |
| retry double-count, if hooked at function entry | 87,558 (2.89x inflated) | " |

## Claims that were tested and **refuted**

Worth keeping visible — these are not open questions.

| hypothesis | outcome |
|---|---|
| Directed graph explains bc/sssp | **No** — made both worse (bc 0.638 → 0.708) |
| Larger graph (kron-25) closes the gap | **No** — made both worse; window didn't scale with footprint |
| Real `web-Google` graph is usable | **No** — 55 MB CSR, 125× below M5's footprint, smaller than the modelled LLC |
| A single window reproduces all workloads | **No** — best window varies 1×–8× |
| A fixed *time* window explains that spread | **No** — DRAM-access rates are near-identical (Spearman 0.086) |
| HWT compensates for a weak HPT | **No** — HWT is gated on HPT membership, so it inherits the weakness |

## Known-open

| item | status |
|---|---|
| M5's measurement window | **not recoverable from the paper** — counters accumulate, WAC region-cycling admits two readings differing ~54× |
| liblinear dataset | we used kdda; M5 used KDD2012 |
| SPEC CPU2017, Memcached, CacheLib | not run (licence / not attempted) |
| Memstrata interference axis | not measured |
| CXLRAMSim port | CXLRAMSim still unreleased. **Ported to SimCXL/CXL-DMSim instead and verified** — see `src/sim/simcxl/`. Instrument works; no workload campaign run (needs full-system kernel + disk image) |

---

## Provenance

AI-assisted pair programming; direction and scoping were the author's, much of the
implementation and prose generated. The claims above should be defensible without
notes — `handbook.md` §9 lists the reasoning chains worth being able to re-derive.
