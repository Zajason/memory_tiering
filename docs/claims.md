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

## The measurement window, measured (this supersedes the reproduction table below)

The headline scorecard uses a **10M-DRAM-access** window. That choice was ours; the
paper never states its own. Searching the window offline -- `.pages.bin` records
per-page masks per epoch, and OR-ing *m* consecutive epochs is exactly what a window
*m* times longer would have recorded -- gives:

| workload | err at our 10M window | best window | err there |
|---|---|---|---|
| bc | 0.378 | 180M acc | **0.010** |
| sssp | 0.309 | 50M acc | **0.013** |
| cc | 0.338 | 80M acc | **0.050** |
| bfs | 0.373 | 70M acc | **0.056** |
| tc | 0.103 | 20M acc | 0.115 |

Scored against the values stated in the paper's **prose** (exact) rather than digitised
bars: `M5_TEXT_P16` for bc/bfs/cc/tc/liblinear, `M5_TEXT_P47` for pr/sssp.

**One global window, fitted once, for all of them:**

| window | bc | bfs | cc | tc | worst |
|---|---|---|---|---|---|
| 10M (ours) | 0.378 | 0.373 | 0.338 | 0.103 | 0.378 |
| **70M** | 0.062 | 0.056 | 0.082 | 0.119 | **0.119** |
| 90M | 0.013 | 0.062 | 0.050 | 0.119 | 0.119 |

**This is a one-parameter fit, not a reproduction.** We chose the window to minimise
error against M5, so it cannot be quoted as "we reproduced M5". What it does establish,
and what `window_fit.py` was written to test, is the distinction that matters: a
**single** unpublished parameter -- fitted once, not per workload -- moves every GAPBS
kernel from 0.34-0.38 to 0.06-0.12. The disagreement was dominated by a window the
paper does not report, and 10M accesses was 5-18x too short.

**Correction to the earlier refutation.** `claims.md` previously recorded "a single
window reproduces all workloads: No -- best window varies 1x-8x". That came from a
search stepping `m *= 2`, so with 22 epochs it only ever sampled m = 1, 2, 4, 8, 16 and
could not see a best at m = 7, 9 or 18. On the full grid the per-workload optima cluster
in 50-180M rather than spanning 1x-8x of a coarse grid.

**Known limit:** `tc` runs on kron-21 (0.3 GB, because triangle counting is superlinear
in edges) so it yields only 4 epochs, capping its searchable window at 40M. Its 0.115 is
a floor imposed by the data, not a fitted optimum.

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

**Both latency rows are currently UNVERIFIABLE and one is disputed.**
`latency_model.py` reads the per-page dumps, which were pruned from `results/`, so it
now exits with `no usable data` and `check_claims.sh` was silently skipping these two
rows while still printing "consistent". A linear extrapolation from the surviving
`results/latency_spr-20t.csv` reproduces 1.505x at the model's default 3 us but gives
**0.956x at 30 us, not 0.835x**. One of the two is wrong and neither can be re-derived
without re-running the profiler with `DUMP_PAGES=1`. Do not quote the 30 us figure
until that is done.

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

### Measured at the CXL device port

`bc` re-run with `--big-mem`, which makes the board instantiate a CXLBridge and
places the high memory region behind it. Counted at three points simultaneously:

| N | M5 | Pin | gem5 MemCtrl | gem5 high MemCtrl | **gem5 CXL device port** |
|---|---|---|---|---|---|
| 4 | 0.005 | 0.160 | 0.109 | 0.110 | **0.110** |
| 16 | 0.040 | 0.418 | 0.192 | 0.194 | **0.194** |
| 48 | 0.145 | 0.638 | 0.476 | 0.475 | **0.475** |
| **max err** | | 0.493 | 0.331 | 0.330 | **0.330** |

**The CXL device port and the memory controller behind it agree to a maximum
difference of 0.00033**, and mean words/page to 47.111 vs 47.110 of 64. The
docs previously asserted the two placements are equivalent for a distribution
over addresses; this measures it instead of arguing it.

It also means the counters now sit where M5 and NeoMem describe them -- on the
CXL device's request path -- and the answer did not move.

### The measurement window dominates

Re-running `bc` with a single window instead of 46 windows of 10M accesses,
same workload, same 451,441,535 DRAM accesses:

| N | M5 | Pin | gem5, 46x10M | gem5, 1 window |
|---|---|---|---|---|
| 4 | 0.005 | 0.160 | 0.109 | **0.002** |
| 8 | 0.020 | 0.260 | 0.142 | 0.004 |
| 16 | 0.040 | 0.418 | 0.192 | 0.005 |
| 32 | 0.090 | 0.576 | 0.310 | 0.006 |
| 48 | 0.145 | 0.638 | 0.476 | 0.008 |
| **max err** | | 0.493 | 0.331 | **0.137** |

mean words/page: 46.851 (46 windows) -> **63.603** (1 window), of 64.

**M5's published curve sits between our two windows at every N.** The short
window is too sparse, the long window too dense, and M5 is bracketed. This is
not a tuning knob we chose badly -- it is the free parameter the paper never
specifies, and it moves P(<=4) from 0.109 to 0.002 while M5 reports 0.005.

### Controlled attribution: kernel visibility vs window (bc)

Five measurements of the same workload, differing one factor at a time:

| # | measurement | window | kernel traffic | words/64 | max err |
|---|---|---|---|---|---|
| 1 | Pin `-ul` | ROI only | **blind** | 31.061 | 0.493 |
| 2 | gem5 `--switch-at-roi` | ROI only | visible | 43.407 | **0.406** |
| 3 | gem5 full-window | + data load | visible | 46.851 | 0.331 |
| 4 | gem5 CXL device port | + data load | visible | 47.111 | 0.330 |
| 5 | gem5 single window | whole run | visible | 63.603 | 0.137 |

Row 2 is the controlled one: same ROI as Pin, only visibility differs.

| step | Δwords | Δerr | share of gap closed |
|---|---|---|---|
| kernel visibility, window held at the ROI | +12.35 | −0.087 | **24.4%** |
| data load added to the window | +3.44 | −0.075 | **21.1%** |
| window lengthened to the whole run | +16.75 | −0.194 | **54.5%** |
| total | +32.54 | −0.356 | 100% |

**RETRACTED: the percentage split above is not a valid decomposition.** It
presumes max-error moves monotonically from Pin to the full-window run, so an
intermediate measurement can be read as partial credit. `sssp` disproves that:
Pin 0.433, ROI-gated **0.571**, full-window 0.391 -- the intermediate sits
*outside* the interval. Mean words/page rises monotonically there (36.3 -> 41.3
-> 48.3) while P(<=48) goes 0.543 -> 0.681 -> 0.501, because the ROI-gated
distribution is more bimodal: more pages under 48 words *and* a heavier tail at
64. Mean density and a CDF point are not tied, so max-error is not monotonic in
density. Where the split appeared to work (bc, cc, bfs) that was luck.

**What survives is the word delta, which is monotonic and physical:**

| workload | kernel visibility, window fixed at the ROI |
|---|---|
| bc | **+12.35** words/page |
| cc | **+7.50** |
| sssp | **+4.97** |
| bfs | **+0.90** |

All positive, spanning an order of magnitude. Kernel traffic inside the
measured region is real and workload-dependent, not a uniform offset.

**Leading hypothesis, not yet tested:** the size tracks how much the kernel
*allocates* during the ROI, so the mechanism is page-fault zeroing rather than
anything about the access pattern. bfs traverses a pre-built CSR and faults
almost nothing (+0.90); bc allocates per-source temporaries throughout its
kernel (+12.35). Testable cheaply with `getrusage` minor-fault counts around
the ROI markers, no simulation needed.

**The old claim, for the record:** Kernel visibility
is worth 12.3 words/page with the window held fixed, which is the cleanest
statement of the blind spot available -- it is not an artefact of comparing
different windows. But window choice accounts for 54.5% on its own, against
24.4% for visibility.

This also explains the sweep: the full-window runs stack *both* effects, which
is why workloads Pin already reproduced (tc, cc, bfs) were pushed past M5.

### The full sweep contradicts the two-workload reading

Extending the simulator to all six GAPBS kernels:

| workload | Pin | gem5 | moved |
|---|---|---|---|
| pr | 0.014 reproduced | **0.011** reproduced | −0.003 |
| tc | 0.030 reproduced | **0.385 disagrees** | +0.355 |
| cc | 0.082 close | **0.271 disagrees** | +0.189 |
| bfs | 0.095 close | **0.165 disagrees** | +0.069 |
| sssp | 0.433 disagrees | 0.391 disagrees | −0.043 |
| bc | 0.493 disagrees | 0.331 disagrees | −0.163 |

mean words/page rises in **every** case: tc 44.6→57.6, cc 44.8→59.9, bfs
46.9→56.1, sssp 36.3→48.3, bc 31.1→46.9, pr 63.2→63.5 (already saturated).

**This is one systematic densifying shift, not an accuracy gain.** It helps the
two workloads where Pin read too sparse and breaks three that Pin had right.
Read on two workloads it looked like the kernel blind spot explaining the gap;
read on six it does not support that.

**The comparison is also confounded and should not be quoted as-is.** The gem5
runs measure from the CPU switch onward, so the data load is inside the window.
The Pin `-ul` runs measure inside the ROI only. So the two differ in *both*
kernel visibility *and* window extent, and this table cannot separate them.
The controlled run is gem5 with `--switch-at-roi`, which measures the timed
kernel only; until that exists, treat the simulator column as "a denser
window", not as "the same measurement with the blind spot removed".

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
