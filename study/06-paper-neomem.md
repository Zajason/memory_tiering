# 6. NeoMem — "Hardware/Software Co-Design for CXL-Native Memory Tiering"

**Venue:** MICRO 2024 · **arXiv:** https://arxiv.org/abs/2403.18702 ·
**Artifact:** https://github.com/PKUZHOU/NeoMem-MICRO-2024

## One-line summary

Offload memory profiling into the CXL device controller with a count-min-sketch hot-page detector
(NeoProf), feed page hotness plus bandwidth/ping-pong telemetry to a Linux daemon, and let the
daemon adapt its promotion threshold dynamically.

## The thesis

**Profiling is the bottleneck, not migration.** Prior tiering work is limited by "low-resolution and
high-overhead memory access profiling." Fix the profiling and 4 KB page migration is fine.

Note this is a *different diagnosis* from M5's. Both build device-side hardware profilers; NeoMem
argues resolution-in-time is what's missing, M5 argues resolution-in-space is. Good tension to
present — it shows you read both rather than one.

Their sharpest motivating observation: hint-fault methods (AutoNUMA, TPP) track **TLB misses**, but
what determines CXL traffic is **LLC misses**, and the two are weakly correlated. A page can be
extremely hot in TLB terms and generate almost no CXL traffic. Promoting it is wasted work. Hardware
in the device sees the LLC-miss stream *by construction* — you literally cannot see anything else
from there. That's an elegant argument.

## NeoProf — the hardware

Sits in the CXL device controller, snooping the request stream.

**Count-min sketch instead of per-page counters.** Per-page counters for 512 GB would need 512 MB of
buffer. Instead: a 2D array, width **W** × depth **D**, indexed by **D** independent hash functions
(H3) of the page number. Increment all D counters on access; estimate a page's count as the *minimum*
across the D lanes (hence "count-min" — collisions only ever inflate, so the min is the tightest
upper bound).

Config used in the paper: **W = 512K counters, D = 2 lanes, 16-bit counters, 16K-entry hot page
buffer.**

**Three pipeline stages:**
1. Hash index computation (H3)
2. Threshold check against θ
3. Hot-page filtering

**Hot-page filtering** is the neat trick: once a page crosses θ it would otherwise be re-reported on
every subsequent access, flooding the buffer. NeoProf sets a bloom-filter-style "hot bit" in the
sketch entries on first detection and suppresses further reports.

**Error-bound control.** Sketch error grows as accesses accumulate (counters saturate, collisions
compound). NeoProf keeps a **64-bin histogram** of the counter distribution so the host can compute a
*tight* error bound rather than the loose worst case, and knows when to reset. This is the part of
the design that makes the sketch trustworthy, and it's a good detail to cite.

**Also monitored:** bandwidth utilization (read/write cycles), read/write ratio, access-frequency
distribution, and **ping-pong events** (promoted-then-quickly-demoted pages).

**Interface:** MMIO — set threshold, read hot pages, read histogram.

**Cost:** ~5.3 mm² and 152.2 mW at TSMC 22 nm. CPU-side overhead of enabling it: **0.021%**.

## Software side (Linux v6.3)

- **NeoMem daemon** — reads NeoProf, drives promotions on a `migration_interval`, resets counters on
  a `clear_interval`.
- **Cold pages: reuse the existing LRU 2Q.** Explicitly *doesn't* build hardware for demotion,
  because "detection of cold pages does not need a high resolution." Good engineering judgment,
  worth repeating.
- **Driver + `/sys/kernel/mm/neomem/`** for userspace policy tuning without recompiling.

## The dynamic threshold algorithm (Algorithm 1)

Rather than a fixed hotness threshold, θ is the **p-percentile** of the access-frequency histogram,
with p adapted each interval:

```
p ← p · (1 + B)^α / (1 + P)^β        α = 1, β = 2 by default
```
where **B** = bandwidth utilization, **P** = ping-pong severity.

Read it as: *high CXL bandwidth pressure → promote more aggressively (lower the bar); lots of
ping-ponging → back off (raise the bar), and back off twice as hard as you lean in* (β > α). Plus a
**migration quota** (default 256 MB/s) capping migration bandwidth, and an error-bound check that
raises θ when the sketch is too imprecise to trust.

This is a genuinely good feedback-control design and it's simple to implement. **Even if you pick
M5, steal this** — the ping-pong feedback term is the cheapest possible fix for the ping-pong
problem and will make your policy arm look much better.

## Granularity

**4 KB base pages.** Compatible with THP: if profiled 4 KB pages within a 2 MB region are hot, the
OS can promote the whole huge page. So NeoMem sidesteps the sub-page issue rather than addressing
it — which is precisely where M5 attacks.

## Evaluation

**Platform:** real FPGA CXL. Host Intel Sapphire Rapids, 32 cores, 32 GB DDR5-4800. Device: Intel
Agilex FPGA, CXL 1.1 Type-3, 16 GB DDR4-2666 @ 400 MHz. Fast:slow ratio 1:2.

**Baselines:** first-touch NUMA, AutoNUMA, TPP, PTE-scan (DAMON), PEBS, **Memtis**.

**Workloads:** DeathStarBench, PageRank, XSBench, GUPS, Silo (YCSB-C), Btree, SPEC 603.bwaves,
654.roms. RSS 10.3–19.7 GB, 32 threads.

**Results:** 32–67% geomean speedup over existing solutions. 1.19–1.67× on DeathStarBench, **3.5× on
XSBench, 4.7× on GUPS**, 1.58× geomean over Memtis. Migration intervals as short as **10 ms** —
impossible for PTE-scan, which is stuck in the seconds range. Sketch width plateaus at 256–512K.
Migration quota stabilizes at 128–256 MB/s.

The GUPS and XSBench numbers are the ones to quote: those are the random-access, no-spatial-locality
workloads where profiling quality dominates everything.

## If you implement NeoMem

**Pro:** the sketch is genuinely easy — D hash functions and a W×D counter array, maybe 100 lines.
The paper gives you every parameter. The dynamic threshold algorithm is a page of pseudocode.

**Con:** once the sketch works, the remaining contribution is the *kernel daemon and policy*, which
is OS work. You said you want the hardware side. In a simulator you'd implement the "daemon" as a
simulator-side policy module anyway, so this is softer than it sounds — but the intellectual center
of gravity is in software.

**Verdict:** excellent second choice, and the threshold-adaptation algorithm is worth borrowing
regardless.
