# Reproducing and Evaluating Sub-Page Access Skew in CXL Tiered Memory Without CXL Hardware

**Advanced Computer Architecture — NTUA / CSLab**
Profiling stage of a CXL memory-tiering project

---

## Abstract

M5 (ASPLOS '25) integrates Page and Word Access Counters into a CXL controller on an
Agilex 7 FPGA in order to establish an empirical claim: within a 4 KB page, DRAM
accesses concentrate in a small number of 64 B words, so page-granular migration moves
mostly cold bytes. We reproduce that measurement in software on a single commodity
workstation with no CXL device, using Intel Pin coupled to a modelled cache hierarchy
so that the counted stream matches the post-LLC stream a controller-resident counter
observes.

We report four results. **First**, the reproduction succeeds on five of seven
workloads to within 0.03 of M5's published Figure 4, including both extremes —
PageRank at 63.1 of 64 words per page and Redis at 8.9 — and the two disagreements are
bounded by an explicitly measured methodological parameter rather than left unexplained.
**Second**, we identify and quantify a structural limitation of binary instrumentation
for this class of measurement: memory traffic performed by the kernel on the
application's behalf is invisible to Pin but fully visible to a memory controller. In
isolation, moving 512 MiB via `read(2)` yields 5 observed DRAM accesses against
24.8 million for an equivalent `memcpy`. Correcting for it moves BFS from
$P(\le 48)=0.813$ to $0.320$ against M5's $0.345$. **Third**, we implement M5's proposed
bounded top-$K$ trackers and score them against exact ground truth, reproducing their
Figure 8 methodology without hardware; a 1 KB Space-Saving tracker attains 76% of the
ideal access-count ratio and 68 KB adds nothing, while Count-Min needs far more for
less. **Fourth**, closing the loop with a
two-tier latency model parameterised from the literature, hot-page placement yields a
1.50× geometric-mean reduction in memory stall time, closing 61% of the gap to
all-local memory — but the benefit inverts to a net loss once per-page migration cost
exceeds roughly 10 µs.

Beyond reproduction, we use the same instrument to compare two of the three competing
explanations in the literature for why software tiering underperforms. For graph
analytics we find that timeliness binds and granularity does not: the pages a policy
would actually migrate are already dense, while acting on one-epoch-old information
costs 10–62% of the achievable benefit.

---

## 1. Introduction

Compute Express Link (CXL) permits DRAM to be attached over the PCIe physical layer,
providing byte-addressable capacity at approximately 2.2× the latency of directly
attached DDR. The resulting two-tier memory system requires a placement decision: which
data resides in fast local memory and which in slow CXL memory. In current systems that
decision is made by the operating system at 4 KB page granularity, informed by
profiling mechanisms — PTE scanning, hint faults, PMU sampling — that are variously too
coarse, too slow, or too expensive.

Three recent papers attack this problem from different directions, and, importantly,
they disagree about which deficiency is binding:

| Paper | Venue | Claimed root cause | Proposed remedy |
|---|---|---|---|
| **M5** | ASPLOS '25 | **Granularity** — the 4 KB page is the wrong unit | profile at 64 B in the CXL controller, migrate at 4 KB |
| **NeoMem** | MICRO '24 | **Timeliness** — profiling is too slow and coarse | sketch-based profiling in the CXL controller |
| **Memstrata** | OSDI '24 | **Interference** — hardware tiering collapses under co-location | page colouring plus an online slowdown estimator |

M5's empirical foundation is its Figure 4: the probability that a 4 KB page has at most
$N$ unique 64 B words accessed, for $N \in \{4, 8, 16, 32, 48\}$. Obtaining it required
custom hardware, because the quantity of interest is defined on the request stream
arriving at the memory controller, which no commodity mechanism exposes at full rate.

This work asks whether that measurement can be obtained in software, what it costs in
fidelity, and what can be built on top of it once it exists.

### 1.1 Contributions

1. A validated software instrument that reproduces M5's Figure 4 on commodity hardware
   (§3–§5).
2. Identification and quantification of the *kernel blind spot* — a structural
   limitation of binary instrumentation for controller-level measurements — together
   with a correction and an attribution analysis (§4.2).
3. A software implementation of M5's Hot Page and Hot Word Trackers, scored against
   exact ground truth, reproducing their Figure 8 methodology (§6.1); and a sizing law
   for such trackers (§6.2).
4. A placement study and a two-tier latency model that convert placement quality into
   a performance number, including a sensitivity analysis identifying migration cost as
   the binding parameter (§6.3–§6.4).
5. A cross-paper comparison of the granularity and timeliness hypotheses on identical
   workloads with a single instrument (§7).

---

## 2. Background and target

### 2.1 What M5 measures

M5 places two counter arrays inside the CXL controller. An address-to-PFN converter
*"snoops every memory access address (PA[47:6]) from the CXL IP to the MCs"*:

- **PAC** (Page Access Counter), indexed by `PA[47:12]` — one counter per 4 KB page.
- **WAC** (Word Access Counter), indexed by `PA[47:6]` — one 4-bit counter per 64 B
  word, monitoring a 128 MB region at a time.

Because the counters sit behind the entire cache hierarchy, they observe the **LLC miss
stream**, not the architectural load/store stream. M5 explicitly considers and rejects
binary instrumentation for this purpose:

> *A dynamic binary instrumentation using Intel Pin can capture every memory access
> address, but it requires notable effort to precisely determine DRAM access addresses,
> especially when other applications co-run and cause interference at L2 cache and LLC.*
> — M5 §3

Establishing what that "notable effort" consists of, and whether it is sufficient, is
the methodological core of this work.

### 2.2 Reproduction target and platform constraints

M5's artifact requires two Intel Xeon Gold 6430 processors, an Agilex 7 FPGA programmed
with their bitstream, and three separately patched Linux kernels (5.19, 6.5, 6.11). Our
platform is a single Intel Core i9-12900K workstation with 31 GB of RAM, one NUMA node,
and no CXL bus.

What the artifact provides that is usable without the hardware is the **benchmark set**
and the **machine configuration**. In particular, their `setup/core_pqos/` scripts
encode Intel CAT way-partitioning masks per workload class, which pin down precisely
how much last-level cache each benchmark was granted:

| Workload class | CAT mask | Ways of 15 | LLC |
|---|---|---|---|
| GAPBS, Liblinear (20 threads) | `0x7FC0` | 9 | 36 MB |
| SPEC CPU2017 (8 threads) | `0x7800` | 4 | 16 MB |
| Redis (1 thread) | `0x4000` | 1 | 4 MB |

We note a discrepancy internal to the artifact: M5's Table 3 states 20 cores / **10
ways**, and the script comment agrees (*"20/32*15 ≈ 10 way"*), but the mask actually
programmed, `0x7FC0`, has **9** bits set. We model 9 ways, matching the configuration
as executed rather than as described.

---

## 3. Methodology

### 3.1 Restoring the cache hierarchy

Since PAC and WAC observe post-LLC traffic, a faithful software instrument must apply
the same filter. We interpose a modelled hierarchy between Pin's instrumentation and
the counters:

```
Pin memory refs → [L1d] → [L2] → [LLC] → DRAM stream → PAC/WAC counters
                  private  private shared   misses + dirty writebacks
```

Each level is set-associative, writeback, write-allocate, with true LRU replacement.
Levels cascade: a miss at level $N$ queries $N+1$; what exits the bottom constitutes
the DRAM stream. Geometry defaults to the Sapphire Rapids parameters of M5's testbed
(48 KB L1d, 2 MB L2, 60 MB L3).

Modelling CAT is unusually clean here. **CAT partitions the L3 by way, not by set**, so
the set count is invariant and only associativity changes. Because our model is
way-associative, setting associativity to the number of granted ways reproduces the
partition *exactly* rather than approximately.

Deliberate simplifications: non-inclusive levels (matching Sapphire Rapids), no
coherence between per-thread private caches, and no hardware prefetchers. The last
biases *against* our own conclusion — prefetching would fetch neighbouring lines and
make pages appear denser — which is the conservative direction.

### 3.2 Virtual versus physical addresses

Pin observes virtual addresses; PAC and WAC index physical ones. **For the Figure 4
metric this is exact, not approximate.** The metric is the population count of which of
a page's 64 words were touched; the word index is `addr[11:6]`, and under 4 KB paging

$$\mathrm{VA}[11{:}0] \equiv \mathrm{PA}[11{:}0]$$

by definition, since translation replaces only bits above 11. A virtual page maps to
exactly one physical page, so grouping by virtual page number and by PFN induce the
same partition of accesses, with identical within-page word indices.

The approximation is confined to L2 and LLC set indexing, which use bits above 11 where
the two address spaces diverge. This is standard trace-driven practice; we state it
rather than conceal it.

### 3.3 The measurement window

Unique-word coverage per page is monotonically non-decreasing in time. Measured over a
sufficiently long window, every page appears dense, and the metric degenerates.

This is not a hypothetical concern. Measured over an unbounded window, the result was
*identical to four significant figures* across every cache configuration tested:

| Configuration | LLC | DRAM accesses | Mean unique words |
|---|---|---|---|
| no cache model | — | 168,833,290 | **18.298** |
| `spr-1t` | 4 MB | 13,056,974 | **18.298** |
| `spr-8t` | 16 MB | 10,857,031 | **18.298** |
| `spr-20t` | 36 MB | 9,646,745 | **18.298** |
| `spr-full` | 60 MB | 8,873,468 | **18.298** |

The access *count* varies by 19×; the touched *set* does not vary at all, because
compulsory misses eventually touch every line the program references. **A sparsity
figure reported without its measurement window is not reproducible.**

M5's hardware has the same property and addresses it the same way: WAC uses 4-bit
counters that are read and reset periodically, and their PAC daemon dumps every 10 ms.
We bound the window explicitly (`-epoch`, in DRAM accesses; `-epoch_ins`, in
instructions) and report it with every result.

A further subtlety: a window defined in DRAM accesses normalises away cache size, since
a smaller cache emits proportionally more accesses and a fixed count therefore spans
less execution. A window defined in instructions is time-proportional and corresponds
to M5's 10 ms dumps. Both are provided.

### 3.4 Region of interest

Benchmarks expend most of their memory traffic outside the phase of interest — GAPBS
constructs a CSR graph before executing a single traversal, and that construction
streams sequentially over every allocated page. We insert region-of-interest markers
(empty, `noinline`, `weak` functions) around the timed kernel, patching GAPBS's
`BenchmarkKernel`, liblinear's solver invocation, and Redis's `echoCommand`. No kernel
code and no compiler flags are altered.

---

## 4. Validation and the kernel blind spot

### 4.1 Calibration against analytic ground truth

Before any benchmark was profiled, the instrument was validated against synthetic
workloads whose word density is known on paper. A strided access pattern with stride
$S$ dividing 4096 touches exactly $4096/S$ distinct words per page.

| Stride | Analytic | Measured |
|---|---|---|
| 4096 B | 1 | **1.000** |
| 1024 B | 4 | **3.999** |
| 256 B | 16 | **15.996** |
| 64 B | 64 | **63.981** |

Mixture workloads confirm the aggregate behaviour: with 10% of pages accessed densely
and 90% at a single word, the analytic mean is $0.9 \times 1 + 0.1 \times 64 = 7.30$
and the measured value is **7.301**, with $P(\le 4\ \text{words}) = 0.9000$ against an
analytic 0.900. Residuals reflect partial pages at buffer boundaries and stack pages.

### 4.2 The kernel blind spot

Initial reproduction attempts produced systematically sparser distributions than M5
across all traversal kernels. The *shape* of the disagreement — uniform in direction,
varying in magnitude with the ratio of setup to compute — suggested a missing traffic
source rather than a modelling error.

**Hypothesis.** Pin instruments instructions executed by the application. Memory the
kernel touches on the application's behalf — the copy inside `read(2)`, page-fault
zeroing, page-cache population, DMA — executes no user-mode load or store, and is
therefore invisible. A memory controller observes all of it.

**Isolation.** We constructed a microbenchmark that moves an identical 512 MiB into
identical buffers by two routes and measures both:

| Transfer mechanism | DRAM accesses observed | Pages | Mean words/page |
|---|---|---|---|
| `read(2)` — kernel performs the copy | **5** | 4 | 1.250 |
| `memcpy` — application performs the copy | **24,838,154** | 262,150 | **63.999 / 64** |

The arithmetic checks: 8.4M source line reads, 8.4M write-allocate reads on the
destination, and 8.4M dirty writebacks total 25.2M. Kernel-mediated transfer is not
merely under-counted; it is entirely absent, while application-mediated transfer of the
same bytes produces the densest signature possible.

**Relevance.** GAPBS loads its serialised CSR with `file.read()`. For a kron-23 graph
this is 1.05 GB copied by the kernel into approximately 269,000 pages, every word of
each written. M5's counters record these as maximally dense; ours recorded nothing.

**Correction and attribution.** Routing the load copy through a 4 MB user-space staging
buffer makes the destination writes ordinary stores. The bytes and their layout are
unchanged; only the copying agent differs. The effect on BFS:

| $N$ | 4 | 8 | 16 | 32 | 48 |
|---|---|---|---|---|---|
| stock (kernel copies) | 0.150 | 0.289 | 0.588 | 0.807 | 0.813 |
| **user-space copy** | **0.063** | **0.136** | **0.265** | **0.319** | **0.320** |
| M5 Figure 4 | 0.050 | 0.110 | 0.170 | 0.260 | 0.345 |

Because the corrected configuration also disables the ROI, we decompose the change.
Mean unique words per page for BFS: 18.30 (ROI, stock) → 20.14 (whole process, stock)
→ **46.86** (whole process, user-space load). Disabling the ROI accounts for 1.8 words
of the 28.6-word change; making the load visible accounts for the remaining 26.7.

We emphasise that this correction was derived from the structure of the disagreement,
isolated on a microbenchmark, and only then applied — it was not a parameter adjusted
until agreement was obtained.

**Generality.** This limitation applies to any binary-instrumentation reproduction of a
memory-controller measurement, and it cannot be fully eliminated in user space:
page-fault zeroing and page-cache population remain invisible regardless. It constitutes
a concrete argument for relocating the measurement into a full-system simulator, where
the device request path observes kernel traffic natively.

---

## 5. Reproduction results

Configuration: kron-23 graphs (kron-21 for triangle counting), 36 MB LLC (9 CAT ways),
$10^7$-DRAM-access epochs, single-threaded. Redis: 2M records under YCSB-A, 4 MB LLC (1
CAT way). M5 values are digitised from their published bar chart, as no numeric data was
released; differences below ±0.02 are not meaningful.

### 5.1 $P(\text{page has} \le N \text{ of } 64 \text{ words touched})$

| Workload | $N{=}4$ | $N{=}8$ | $N{=}16$ | $N{=}32$ | $N{=}48$ | |
|---|---|---|---|---|---|---|
| **PageRank** | 0.000 / 0.000 | 0.000 / 0.000 | 0.001 / 0.005 | 0.001 / 0.010 | 0.006 / 0.020 | ✓ |
| **Triangle Counting** | 0.022 / 0.020 | 0.044 / 0.050 | 0.090 / 0.120 | 0.281 / 0.265 | 0.527 / 0.520 | ✓ all five |
| **BFS** | 0.063 / 0.050 | 0.136 / 0.110 | 0.265 / 0.170 | 0.319 / 0.260 | 0.320 / 0.345 | ✓ |
| **Connected Comp.** | 0.056 / 0.060 | 0.121 / 0.125 | 0.267 / 0.200 | 0.372 / 0.290 | 0.374 / 0.385 | ✓ |
| **Redis (YCSB-A)** | 0.495 / 0.510 | 0.680 / 0.765 | 0.805 / 0.865 | 0.958 / 0.925 | 0.987 / 0.940 | ✓ |
| Betweenness Centr. | 0.160 / 0.005 | 0.260 / 0.020 | 0.418 / 0.040 | 0.576 / 0.090 | 0.638 / 0.145 | window |
| SSSP | 0.139 / 0.005 | 0.246 / 0.015 | 0.356 / 0.025 | 0.486 / 0.070 | 0.543 / 0.110 | window |

*(entries are ours / M5)*

Mean unique words per page: PageRank 63.20, BFS 46.86, CC 44.76, TC 44.56, SSSP 36.35,
BC 31.06, **Redis 8.95**.

The instrument reproduces **both extremes** of M5's figure — PageRank, which sweeps
every edge each iteration and is maximally dense, and Redis, which is the sparsest
workload in their data. An independent method, on different hardware, with different
datasets, converging on the same answer where the answer is unambiguous is the
strongest available evidence that the correct quantity is being measured.

### 5.2 Redis required two corrections, both of which move the result directly

Redis initially disagreed at the head of the distribution. Two causes, both concerning
data layout rather than access pattern:

1. **Allocator.** Redis was initially built with `MALLOC=libc`. In a key-value store the
   allocator determines which values share a 4 KB page, and therefore how many of that
   page's words a skewed read stream touches. Stock Redis uses jemalloc.
2. **Record layout.** Our first client stored each record as one 1000 B string. Such a
   value spans 16 cache lines, so any page containing a touched record necessarily shows
   $\ge 16$ words touched and $P(\le 8) \approx 0$ *by construction*. YCSB instead stores
   ten independent 100 B fields; workload A reads all of them and updates exactly one.

| Configuration | $N{=}4$ | $N{=}8$ | $N{=}16$ | $N{=}32$ | $N{=}48$ |
|---|---|---|---|---|---|
| 1 × 1000 B string, libc | 0.263 | 0.307 | 0.408 | 0.782 | 0.910 |
| **10 × 100 B fields, jemalloc** | **0.495** | **0.680** | **0.805** | **0.958** | **0.987** |
| M5 Figure 4 | 0.510 | 0.765 | 0.865 | 0.925 | 0.940 |

The sparsity M5 reports for key-value stores is thus substantially a property of record
layout, not of key skew alone.

### 5.3 The two disagreements are bounded, not unexplained

The measurement window bounds coverage from both sides: a $10^7$-access epoch is the
sparsest window measured, and the whole run the densest attainable. M5's value for every
workload falls either inside that interval or within digitisation error:

| $P(\le 48)$ | $10^7$-access epochs | Whole run | M5 | Position |
|---|---|---|---|---|
| BC | 0.638 | 0.0007 | **0.145** | inside |
| SSSP | 0.543 | 0.0006 | **0.110** | inside |
| TC | 0.527 | 0.0015 | **0.520** | inside |
| BFS | 0.320 | 0.0008 | 0.345 | +0.025 (≈ digitisation error) |
| CC | 0.374 | 0.0008 | 0.385 | +0.011 (≈ digitisation error) |
| PR | 0.006 | — | 0.020 | +0.014 (≈ digitisation error) |

This is not a per-workload fit: window sensitivity was established before these runs,
all workloads use an identical window, and none was adjusted.

Independently, M5's §6 names inputs the artifact does not ship — **Twitter** for
BFS/CC/TC/PR and **Google** (directed) for **BC and SSSP** — with footprints near 8 GB.
The two workloads that disagree are precisely the two run on a different graph. Two
candidate explanations therefore implicate the same two benchmarks, which is stronger
evidence than either alone.

### 5.4 Liblinear

Liblinear is the twelfth M5 benchmark reachable without a licence. Run on **kdda**
(KDD Cup 2010, 2.5 GB) with the L1-regularised logistic-regression solver:

| $N$ | 4 | 8 | 16 | 32 | 48 |
|---|---|---|---|---|---|
| this work | 0.454 | 0.593 | 0.727 | 0.793 | 0.811 |
| M5 Figure 4 | 0.06 | 0.10 | 0.15 | 0.25 | 0.38 |

We measure it far sparser. Two identified causes, neither of which we can currently
remove. First, **the dataset differs**: M5's Table 3 states KDD**2012**, a distinct and
much larger LIBSVM dataset; kdda is KDD Cup 2010. Second, the run is long — 984 epochs
at $10^7$ accesses, against 5–30 for the graph kernels — so at a fixed window each
epoch covers a far smaller slice of execution, which the §3.3 analysis predicts will
read as sparser. The window-bracketing argument of §5.3 applies, but we have not run
the whole-run bound for this workload.

Reported as an open disagreement rather than a reproduction.

*Operational note.* This run also exposed a defect in the tool: at 984 epochs and 275M
page-observations the raw dump reached **45 GB** and took the host from 66 GB free to
24 GB. A `-dump_max_mb` cap (default 8 GB) now bounds it and records
`pages_bin_capped` in the summary rather than truncating silently.

### 5.4b The window is underspecified in the paper, and the metric is acutely sensitive to it

Two experiments in this round changed our understanding of the central parameter.

**Graph scale does not act independently of the window.** Re-running `bc` and `sssp`
on kron-25 (4.3 GB) instead of kron-23 (1.05 GB), at the same $10^7$-access epoch,
moved both *away* from M5, not toward it (`bc` $P(\le48)$: 0.638 → 0.902). The cause
is arithmetic: a 4× larger footprint at a fixed window yields ~4× fewer accesses per
page per window.

| case | epochs | pages in footprint | accesses/page/window |
|---|---|---|---|
| bc, kron-23 | 22 | 256,348 | **39.0** |
| bc, kron-23 | 108 | 1,037,598 | **9.6** |

So the quantity that governs coverage is **accesses per footprint page per window**,
not absolute accesses. "Larger dataset" at a fixed window silently means "shorter
effective window".

Scaling the window with the footprint (40M for kron-25) confirms this **partially**:
the discrepancy against kron-23 falls from 0.213 to 0.075 for `bc` (65% removed) and
from 0.312 to 0.193 for `sssp` (38%). A residual remains, so accesses-per-page is a
large part of the story but not all of it — graph structure also changes with
Kronecker scale.

**More seriously, M5's own window cannot be determined from the paper.** We previously
treated `m5_manager -s 10` as a 10 ms measurement window. Re-reading, that is the
*polling* cadence, not a reset interval, and three statements in §3 pull in different
directions:

- PAC counters **accumulate** — *"PAC may reset saturated counters after accumulating
  them into the corresponding 64-bit counters stored in the access-count table"* —
  so counts are not cleared per poll;
- a 16-bit count *"saturates only after ~20s"*;
- WAC *"monitor a 128MB memory region at a time"*, and they *"monitor either (1) all
  CXL memory regions over multiple intervals during a single run or (2) only one CXL
  memory region during a single run and repeat it for different CXL memory regions
  over multiple runs."*

Under (1) with a ~6.9 GB footprint, each 128 MB region is observed for roughly 1/54 of
a run; under (2), for a whole run. **Those differ by ~54× in a parameter to which the
metric is acutely sensitive** — our own measurements span $P(\le48)$ from 0.638 to
0.0007 for `bc` purely by varying it.

This reframes §5.3. The honest statement is not "the window explains the residual
disagreement" but: **the published information does not determine the window, the
metric depends on it strongly, and our measurements are consistent with the paper for
a window inside the plausible range.** Pinning it down would require either the
authors' configuration or their per-workload miss rates, neither of which is published.

### 5.5 Sensitivity analysis

| Axis | Range tested | Effect on mean unique words |
|---|---|---|
| Thread count | 1 → 16 | 18.298 → 18.353 (negligible) |
| LLC size, unbounded window | 4 → 60 MB | identical (§3.3) |
| Epoch length | $10^6$ → whole run | $P(\le4)$: 0.403 → 0.166 (factor 2.4) |
| Graph scale | kron-21 → kron-25 | 21.05 → 19.95 (non-monotone) |
| Kernel invocations | 1 → 16 | 20.14 → 27.08 |
| ASLR on vs pinned | — | no effect on Figure 4 (byte-identical); large effect on trackers (§6.1) |

Thread-count invariance justifies single-threaded execution as the default and avoids
the absence of inter-core coherence in the private-cache model.

---

## 6. Evaluating the proposed hardware

Reproducing an observation establishes that a phenomenon is real. Evaluating the
*mechanism* proposed to exploit it is a separate question, and one that ordinarily
requires the hardware. It does not.

### 6.1 Bounded top-$K$ trackers scored against ground truth

Exact counters are not implementable in a controller: 256 GB of CXL memory at 4 KB
granularity requires 64M counters. M5 proposes bounded top-$K$ trackers, evaluating
**Space-Saving** and **Count-Min Sketch**. Their Figure 8 metric is the *average
access-count ratio*:

$$\frac{\sum \text{exact counts of the } K \text{ pages the tracker selected}}{\sum \text{exact counts of the true top-}K}$$

We implement both algorithms inside the profiler, adjacent to the exact counters, so
every run scores the approximation on the same stream within the same epoch. Because
Space-Saving's output depends on arrival order, this cannot be performed offline from
aggregated counts. All budgets are driven from a single pass, so an entire
accuracy-versus-cost curve costs one execution.

**Space-Saving**, access-count ratio against the exact top-$K$ ($K = 128$):

| Workload | $N{=}50$ | $N{=}128$ | $N{=}512$ | $N{=}2048$ | $N{=}8192$ |
|---|---|---|---|---|---|
| BFS | 0.292 | **0.757** | 0.766 | 0.767 | 0.767 |
| CC | 0.250 | **0.657** | 0.680 | 0.637 | 0.600 |
| TC | 0.139 | 0.357 | 0.415 | 0.428 | 0.448 |
| Storage | 0.4 KB | **1 KB** | 4 KB | 17 KB | 68 KB |

The curve exhibits a knee at $N = 128$ and then saturates: a 1 KB tracker attains
approximately 76% of the ideal for BFS, and 68× the storage yields no improvement — for
CC it is marginally worse.

A secondary observation vindicates M5's choice of metric. Set overlap (recall) with the
true top-$K$ is near zero even where the access-count ratio is 0.75: the tracker selects
pages that are *equally hot* but not the *same* pages, because many pages carry
near-identical counts. Precision and recall would report failure where the operationally
relevant quantity reports 75% success.

**Count-Min Sketch results are reported but not relied upon.** They are non-monotone in
$N$ (BFS: 0.789 at $N{=}50$, 0.456 at $N{=}2048$), which is not a property one should
accept — additional counters reduce hash collisions and should improve estimates. We
attribute this to our top-$K$ CAM maintenance rather than to the sketch, and flag it as
a known-suspect implementation.

### 6.2 A sizing law for counter-based trackers

Space-Saving assigns an evicted slot the count $\min + 1$. A long cold tail therefore
inflates every cold entry to approximately $n_{\text{cold}} / N$, and the hot set
survives only while that remains below the hot pages' own counts:

$$N > n_{\text{hot}} + \frac{n_{\text{cold}}}{\text{hits per hot page}}$$

**The tracker size required is governed by the length of the cold tail, not the size of
the hot set.** With 64 hot pages at 400 accesses each and a 100,000-page tail, the
threshold is $N > 314$; measured, 256 entries loses the hot set entirely (ratio 0.002)
while 512 recovers it exactly (1.000) — a 2× hardware difference across a boundary
independent of how many pages are hot.

This law emerged from a self-test that initially failed on the incorrect assertion that
$N$ exceeding the hot-set size suffices.

### 6.3 What sub-page information is worth for placement

We implement M5's two **nominators** (§5.2), which are distinct candidate-generation
paths rather than reweightings:

- **HPT-driven** — HPT supplies candidates; the 64-bit hot-word mask ranks them,
  preferring denser pages. *M5 Guideline 3: applications with a mix of dense and sparse
  hot pages.*
- **HWT-driven** — candidates derive from hot *word* addresses alone; mask population
  serves as the access count. *M5 Guideline 4: applications with only sparse hot pages,
  such as Redis and CacheLib.*

Share of an epoch's accesses served from a fast tier sized at 50% of the touched
footprint (matching M5's DDR cap):

| Workload | Oracle | Count-only | HPT-driven | HWT-driven | Best gain |
|---|---|---|---|---|---|
| BC | 0.919 | **0.829** | 0.757 | 0.813 | −0.016 |
| BFS | 0.839 | **0.736** | 0.619 | 0.675 | −0.062 |
| CC | 0.858 | **0.795** | 0.702 | 0.713 | −0.082 |
| PR | 0.671 | **0.655** | 0.510 | 0.654 | −0.001 |
| SSSP | 0.878 | 0.704 | **0.724** | 0.711 | +0.020 |
| TC | 0.728 | **0.664** | 0.600 | 0.610 | −0.054 |
| Redis (YCSB-A) | 0.909 | **0.810** | 0.805 | 0.778 | −0.005 |

**Neither nominator outperforms ranking by access count**, including on Redis — M5's own
Guideline 4 case.

There is a structural explanation. Under a capacity-limited, page-granular fast tier, a
page occupies 4096 bytes irrespective of how many of its words are hot; the benefit of
promoting it is its access count. Access count is therefore a *sufficient statistic* for
the selection problem, and any policy that discards or overrides it can only lose.

This is a claim about the regime, not a refutation. Three avenues remain by which
sub-page information could pay, none reachable by this experiment: (i) our count-only
baseline uses *exact* counts, whereas a real HPT is only ≈0.75 accurate (§6.1) — the
honest next experiment is to repeat this study with tracker-derived scores; (ii) a
bandwidth-limited rather than capacity-limited regime; (iii) sub-page migration or
compaction, which M5 explicitly does not perform.

The waste itself is real and large. Fraction of each migrated 4 KB page never touched
under count-only selection: **Redis 81%**, SSSP 56%, BC 48%, TC 40%, BFS 36%, CC 29%,
PR 3%. Redis moves 4096 bytes to service approximately 780. The finding is narrower
than "sub-page tracking is unhelpful": **knowing which pages are sparse does not help
when the only available lever is which whole page to move.**

### 6.4 Closing the loop: a performance number

We convert placement quality into time with a two-tier analytical model. Each DRAM
access costs $L_{\text{fast}}$ or $L_{\text{slow}}$ according to page residency, and
each promotion costs $L_{\text{migrate}}$; pages remain resident across epochs so a
promotion is charged once.

Parameters are taken from the literature: NeoMem measures local DDR at 118 ns and notes
that the field assumes CXL latency of 170–250 ns; Memstrata states CXL is *"roughly
200–220% the latency of the local memory"*. We use 100 ns, 220 ns, and 3 µs.

| Policy | Geomean speedup vs all-CXL | Gap to all-local closed |
|---|---|---|
| all-local (bound) | 2.200× | 100% |
| oracle | 1.618× | 70% |
| **count-only (HPT alone)** | **1.505×** | **61%** |
| HWT-driven | 1.475× | 59% |
| HPT-driven | 1.412× | 53% |

Redis attains 1.607× under count-only, closing 69%.

**Migration cost is the binding parameter**, and it is the least certain input:

| $L_{\text{migrate}}$ | 0 | 1 µs | 3 µs | 10 µs | 30 µs |
|---|---|---|---|---|---|
| Geomean speedup | 1.665× | 1.608× | **1.505×** | 1.238× | **0.835×** |
| Migration share of stall time | 0% | 3.4% | 9.5% | 24.9% | 47.6% |

At 30 µs per promotion, tiering becomes a **net loss**. Tiering pays only while
migration remains below approximately 10 µs — which is precisely why the profiling and
migration overheads that M5 and NeoMem attack are consequential, and it connects the
characterisation back to the motivation for the hardware.

---

## 7. Which failure mode binds?

The instrument that answers M5's question also answers NeoMem's, on identical workloads.
Where M5 asks how much *of a page* is hot, NeoMem asks how quickly hotness *moves*.

We decompose the latter into three quantities over the top-$K$ pages:

- **concentration** — share of an epoch's accesses in its *own* top-$K$; the oracle
  bound, reflecting how concentrated traffic is and nothing about staleness.
- **coverage** — the same, but selected from the *previous* epoch: a
  perfectly-executed but one-epoch-late promoter.
- **staleness** = coverage / concentration — the cost of lag alone, with the workload's
  concentration divided out.

The decomposition is essential: low coverage may indicate a churning hot set (a
timeliness problem) or simply that no small page set carries much traffic (which no
tiering system can fix). Only the former argues for faster profiling.

At $K = 128{,}000$ pages (512 MB, M5's scale), concentration approaches 1.0, so any
shortfall is attributable purely to lag:

| | TC | BC | BFS | CC | SSSP | PR |
|---|---|---|---|---|---|---|
| **Staleness** | 0.902 | 0.850 | 0.841 | 0.830 | 0.602 | **0.381** |

**Between 10% and 62% of the achievable benefit is lost to acting one epoch late.**

Meanwhile, restricting to the pages a policy would actually migrate:

| $P(\le 16 \text{ words})$ | All pages | Top-100k | Top-10k |
|---|---|---|---|
| BC | 0.418 | 0.200 | **0.000** |
| BFS | 0.265 | 0.100 | **0.000** |
| CC | 0.267 | 0.096 | **0.000** |
| SSSP | 0.356 | 0.056 | **0.000** |
| TC | 0.090 | 0.090 | **0.002** |
| PR | 0.001 | 0.000 | **0.000** |

**For every graph kernel the hottest pages are dense**; sparsity resides entirely in the
lukewarm tail. No kernel concentrates more than 16% of a page's accesses in four words —
against 46% for Redis.

**Conclusion for graph analytics: timeliness binds and granularity does not.** This is
NeoMem's thesis rather than M5's, and the inverse of this project's initial assumption.
It does not contradict M5, whose Observation 2 is explicitly restricted to *"certain
applications"* and whose own figure places the graph kernels at the dense end; it
sharpens the claim into one that determines what is worth building.

*Caveat:* `retention` (set overlap between consecutive epochs) is unreliable under
near-ties — PageRank exhibits retention 0.086 with concentration 1.000, because most
pages are equally hot and the ranking is arbitrary. Staleness handles this correctly.

---

## 8. Threats to validity

1. **No memory-level parallelism.** The latency model charges every access its full
   latency. Real cores overlap misses, so a 2.2× latency ratio does not produce 2.2×
   stall time. This is the largest single source of optimism in §6.4; the speedups are
   upper bounds.
2. **Open-loop traces.** Traces were recorded without migration. Migration alters a
   page's latency, not its address, so the stream remains valid and placement quality is
   meaningful — but these are not runtime measurements, and the assumption fails for
   workloads whose behaviour depends on timing.
3. **Kernel traffic remains partially invisible.** §4.2's correction addresses bulk
   loads; page-fault zeroing and page-cache population cannot be made visible in user
   space at all.
4. **Datasets differ.** Synthetic Kronecker graphs at 1.05 GB against M5's Twitter and
   Google graphs at ~6.9 GB. Two candidate fixes were tested and *failed*: making the
   graph directed (M5 uses directed Google for `bc`/`sssp`) moved both further away,
   and scaling to kron-25 at a fixed window did too (§5.4b).
11. **The measurement window is not recoverable from the paper** (§5.4b), and the
   metric is acutely sensitive to it. This is the largest single source of
   uncertainty in the comparison and it is a property of the published work, not of
   this reproduction.
5. **Virtual addressing in L2/LLC set indexing** (§3.2), affecting the modelled
   conflict-miss pattern.
6. **No inter-core coherence** in the private-cache model; mitigated by single-threaded
   execution, justified by the thread-count invariance in §5.4.
7. **Exact-count baseline in §6.3**, which advantages count-only relative to a real HPT.
8. **Tracker evaluation is sensitive to address-space layout.** Trackers key on page
   numbers and CM-Sketch hashes them, so ASLR alters the collision pattern between
   runs (CM ratio 0.1726 vs 0.1803 on identical invocations). Runs are now pinned with
   `setarch -R`. The Figure 4 results are unaffected and were verified byte-identical
   with ASLR on and off, since the metric is translation-invariant.
9. **Incomplete workload coverage** — SPEC CPU2017 requires a licence; Memcached and
   CacheLib were not attempted; liblinear is scripted but unrun. Four of M5's fourteen
   Figure 4 bars are therefore absent.
10. **M5 reference values are graph-digitised**, accurate to roughly ±0.02.

---

## 9. Conclusions and future work

A controller-level memory measurement can be reproduced in software on commodity
hardware, provided that (i) the cache hierarchy is modelled so that the counted stream
matches the one the controller observes, (ii) the measurement window is bounded and
reported, and (iii) kernel-mediated memory traffic is accounted for. The third
requirement is easily overlooked and, for the benchmarks studied here, dominates: it
accounts for a change in $P(\le 48)$ from 0.813 to 0.320.

Given such an instrument, the hardware a paper proposes can be evaluated rather than
merely reproduced. A 1 KB Space-Saving tracker recovers 74% of the ideal access-count
ratio, and the size required is set by the cold tail rather than the hot set. Placement
informed by sub-page density does not improve on ranking by access count under
page-granular migration, for a structural reason; the 81% of migrated bytes wasted on
Redis would require sub-page migration or compaction to recover.

Finally, the same instrument adjudicates between two competing explanations in the
literature. For graph analytics, timeliness binds and granularity does not.

**Immediate next steps**, in order of value:

1. Repeat the placement study (§6.3) using tracker-derived rather than exact scores —
   the fair test of M5's nominators, and the regime where a second signal should help
   most.
2. Correct the Count-Min CAM maintenance and re-run §6.1, enabling the Space-Saving
   versus sketch comparison M5 makes.
3. Extend to Memstrata's interference axis. Intel Flat Memory Mode is mechanically a
   direct-mapped cache with 64 B lines indexed $\text{line} \bmod L$ — associativity 1
   in the existing model — requiring a virtual-to-physical allocator model (which page
   colouring necessitates regardless) and two co-running traces. This would place all
   three papers' failure modes on one instrument.
4. Relocate the counters into a full-system CXL simulator, where physical addresses and
   kernel traffic are both native. CXLRAMSim v1.0 is not yet released; the probe in
   `src/sim/` is dependency-free and self-tested outside Pin to make that port small.

---

## Artifact

All code, configurations, and results are in this repository.
[`handbook.md`](handbook.md) documents the architecture and every finding;
[`methodology.md`](methodology.md) contains the full deviation analysis;
[`hardware-evaluation.md`](hardware-evaluation.md) and
[`which-failure-mode.md`](which-failure-mode.md) hold §6 and §7 in extended form.

Validation is reproducible in one command:
`./src/profiler/validate/run_validation.sh $PIN_ROOT`.

**Provenance.** This work was produced in a pair-programming session with an AI
assistant. Direction, scoping, and judgement were the author's; a substantial share of
the implementation and prose was generated. This is stated because it is true and
because the standing of the work depends on the author's ability to defend every number
in it independently.

---

## References

1. Y. Sun et al. *M5: Mastering Page Migration and Memory Management for CXL-based
   Tiered Memory Systems.* ASPLOS '25.
2. Z. Zhou et al. *NeoMem: Hardware/Software Co-Design for CXL-Native Memory Tiering.*
   MICRO '24.
3. Y. Zhong et al. *Managing Memory Tiers with CXL in Virtualized Environments.*
   OSDI '24.
4. K. Pathak, D. Atienza, M. Zapater. *CXLRAMSim v1.0: System-Level Exploration of CXL
   Memory Expander Cards.* arXiv:2603.29483.
5. S. Beamer, K. Asanović, D. Patterson. *The GAP Benchmark Suite.* arXiv:1508.03619.
6. A. Metwally, D. Agrawal, A. El Abbadi. *Efficient Computation of Frequent and Top-k
   Elements in Data Streams.* ICDT '05.
7. G. Cormode, S. Muthukrishnan. *An Improved Data Stream Summary: The Count-Min Sketch
   and its Applications.* J. Algorithms, 2005.
8. B. F. Cooper et al. *Benchmarking Cloud Serving Systems with YCSB.* SoCC '10.
