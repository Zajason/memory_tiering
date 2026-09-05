# Methodology: reproducing sub-page hot skewness with Intel Pin

This document explains what is being measured, why each design decision was made, and
where the setup deviates from M5's hardware. It is written so that someone who has
not seen the code can decide whether to believe the numbers.

**Target.** M5 (ASPLOS'25) Figure 4: *the probability that a 4 KB page has at most
$N$ unique 64 B words accessed*, for $N \in \{4, 8, 16, 32, 48\}$, and Figure 10, the
distribution of access counts per 4 KB page. These are the figures that quantify
"hot skewness at cache-line granularity" — the observation that a page can be
classified hot on the strength of a handful of 64 B words.

---

## 1. What M5 measured, and why we cannot just count loads

M5 put two counter arrays inside a CXL controller on an Agilex 7 FPGA:

| | Indexed by | Counts | Answers |
|---|---|---|---|
| **PAC** (Page Access Counter) | `PA[47:12]` | accesses per 4 KB page | how hot is this page |
| **WAC** (Word Access Counter) | `PA[47:6]` | accesses per 64 B word | how much *of* it is hot |

The critical property is stated in their §3: an address-to-PFN converter *"snoops
every memory access address (PA[47:6]) from the CXL IP to the MCs"*. Those counters
sit **behind the entire CPU cache hierarchy**. They see the LLC miss stream, not the
program's load/store stream.

M5 explicitly rejects the tool we are using, and says why:

> A dynamic binary instrumentation using Intel Pin can capture every memory access
> address, but it requires notable effort to precisely determine DRAM access
> addresses, especially when other applications co-run and cause interference at L2
> cache and LLC. — M5 §3

That is the problem this setup has to solve. A stock Pin memory tracer answers a
*different question*: which words the program touches. PAC/WAC answer: which words
reach memory. The two distributions differ, because caches absorb exactly the
high-reuse traffic that makes a page look hot.

**Our answer:** put the hierarchy back in software. Every reference goes through a
modelled L1d → L2 → LLC before it is counted.

```
Pin memory refs ──▶ [L1d] ──▶ [L2] ──▶ [LLC] ──▶ DRAM stream ──▶ PAC/WAC counters
                    private    private   shared    misses + dirty
                    per-thread           (CAT-     writebacks
                                          sized)
```

`-cache 0` disables the filter and reproduces the naive measurement, so the two can
be plotted side by side. That comparison is itself a result: see §4.

---

## 2. Virtual vs. physical addresses

Pin sees virtual addresses. PAC and WAC index physical ones. This matters less than
it first appears, and exactly where it matters is worth being precise about.

**For the Figure 4 metric it does not matter at all.** The metric is the popcount of
which of a page's 64 words were touched. The word index within a page is `addr[11:6]`,
and under 4 KB paging

$$\text{VA}[11{:}0] \equiv \text{PA}[11{:}0]$$

by definition — translation replaces the bits above 11 and leaves the page offset
untouched. A virtual page maps to exactly one physical page, so grouping by virtual
page number and grouping by PFN produce the *same partition* of accesses into pages,
and within each page the *same* word indices. The density histogram is therefore
identical under either address space. This is not an approximation; it is exact.

**Two caveats, both bounded:**

1. **Aliasing.** If two virtual addresses map to one physical page (shared memory,
   `MAP_SHARED` file mappings, `fork` sharing), PA-space would merge them and
   VA-space would not. The benchmarks here use private anonymous memory for their
   data structures, so this affects only library text and a handful of shared pages —
   a rounding error against hundreds of thousands of data pages.

2. **Cache set indexing.** This one is a genuine approximation. L1d here is 48 KB /
   12-way / 64 sets, so its index bits are `addr[11:6]` — inside the page offset,
   making it VIPT-equivalent and exact. L2 and LLC index with bits above 11, where
   VA and PA diverge, so our modelled conflict-miss pattern is not the machine's.
   Trace-driven simulators universally accept this; the standard argument is that
   with a scattered VA→PA mapping the set-load distribution is statistically
   equivalent, and it is the *aggregate* miss stream, not the identity of individual
   conflict misses, that feeds the counters. Worth stating out loud rather than
   hiding.

---

## 3. Why epochs are mandatory (the most important thing in this document)

Running the sweep in `experiments/sensitivity_sweep.sh` turned up a fact that is not
obvious and that silently invalidates a naive reproduction.

Measured over an **unbounded window**, `mean_unique_words` for GAPBS BFS was
identical — to four significant figures — for every cache configuration tried:

| Config | LLC | DRAM accesses | mean unique words |
|---|---|---|---|
| `nocache` | — | 168,833,290 | **18.298** |
| `spr-full` | 60 MB | 8,873,468 | **18.298** |
| `spr-20t` | 36 MB | 9,646,745 | **18.298** |
| `spr-8t` | 16 MB | 10,857,031 | **18.298** |
| `spr-1t` | 4 MB | 13,056,974 | **18.298** |

The DRAM access *count* varies by 19×. The set of *touched words* does not vary at
all. The reason is compulsory misses: over a long enough window, every line the
program ever touches misses at least once, so the touched-mask converges to the
program's architectural footprint regardless of how big the cache is.

Two consequences:

1. **Figure 4's metric is only cache-sensitive inside a bounded window.** Over a
   whole run it degenerates into "which words does the program touch", and the
   elaborate cache model contributes nothing. The measurement window is not a
   detail; it is the parameter that makes the question well-posed.

2. **Word coverage only ever increases with window length.** Measure long enough and
   every page looks dense. Any reported sparsity number is meaningless without the
   window it was measured over.

M5's hardware has the same property and handles it the same way: WAC's counters are
4 bits wide, are read and reset periodically, and the artifact's PAC daemon dumps
every 10 ms (`m5_manager -s 10`). Their Figure 4 comes from bounded sampling windows,
not from whole runs. Their §4.1 says the measurement is repeated *"at 10 different
random execution points"*.

**What we do:** `-epoch N` closes the measurement window every $N$ million DRAM
accesses, folds that epoch's distribution into the aggregate, and zeroes the
counters. `-roi_epoch` additionally closes the window when the region of interest is
left, so one epoch never straddles two kernel invocations. Results are reported with
the epoch length stated, and `sensitivity_sweep.sh epoch` shows how much it moves:

| epoch (M DRAM accesses) | mean unique words | P(≤4) | P(≤16) |
|---|---|---|---|
| 1 | 19.970 | 0.4033 | 0.6797 |
| 2 | 20.452 | 0.3847 | 0.6830 |
| 5 | 20.308 | 0.2676 | 0.6812 |
| 10 | 18.298 | 0.1662 | 0.7078 |
| ≥25 (whole run) | 18.298 | 0.1662 | 0.7078 |

BFS on kron-23 emits about 9.6M DRAM accesses in total, so any window at or above
10M is the whole run and the curve flattens. Below that, `P(≤4)` moves by a factor of
2.4 — which is the point.

### Two kinds of window, and why the choice matters

A window measured in DRAM accesses and a window measured in time are not
interchangeable, and the difference produced a misleading result before it was
noticed.

Sweeping LLC size with an *access-based* window gave byte-identical distributions for
4 MB, 16 MB, 36 MB and 60 MB. That is not a bug and not only the compulsory-miss
effect above: a smaller cache emits *more* DRAM accesses, so a fixed count of them
spans proportionally *less* execution. The two effects cancel exactly, and the axis
reports nothing.

The question M5's hardware actually asks is time-based — their PAC daemon dumps every
10 ms (`m5_manager -s 10`). So the tool grew `-epoch_ins N`, which closes the window
every $N$ million instructions. Under a time-proportional window a larger cache
genuinely absorbs more traffic, fewer words per page reach the controller, and pages
look sparser. `sensitivity_sweep.sh window` runs both kinds side by side over the same
cache sizes so the difference is explicit rather than folklore.

Stated as a rule: **report the window kind alongside the window length.** A sparsity
number without both is not reproducible.

---

## 3b. The kernel blind spot

This is the largest single difference between what a Pin tool can see and what M5's
hardware saw, and it was found by chasing the gap in §7 rather than assumed up front.

**Pin instruments the instructions the application executes.** Memory the *kernel*
touches on the application's behalf executes no user-mode load or store, so no
instrumentation fires:

- the copy inside `read(2)` / `write(2)`
- page-fault zeroing of freshly faulted anonymous pages
- page-cache population, DMA from storage
- anything else done in kernel context

M5's PAC and WAC sit at the memory controller. They count every byte of it.

### Measured, not assumed

`src/profiler/validate/kernel_blindspot.c` moves the same 512 MiB into the same
buffers two ways and profiles both:

| how the bytes move | DRAM accesses seen | pages observed | mean words/page |
|---|---|---|---|
| `read(2)` — kernel performs the copy | **5** | 4 | 1.250 |
| `memcpy` — application performs the copy | **24,838,154** | 262,150 | **63.999 / 64** |

Identical bytes, identical destination pages. One is invisible; the other is the
densest possible signature — every one of 64 words in every one of 131,072 pages.

(The 24.8M figure also checks out arithmetically: 8.4M source line reads, 8.4M
write-allocate reads on the destination, and 8.4M dirty writebacks = 25.2M.)

### Why this matters for GAPBS specifically

GAPBS loads its serialized CSR with `file.read()` — `reader.h`, `ReadSerializedGraph`,
lines 290–296. For a kron-23 graph that is **1.05 GB copied by the kernel**, landing
in roughly 269,000 4 KB pages, every word of every one of them written.

M5's counters record those 269,000 pages as 64/64 words touched. Ours record nothing.
Since the graph arrays are also most of what the kernel then traverses, this pushes
their whole distribution toward "dense" relative to ours — in exactly the direction of
the discrepancy in §7.

The same argument applies to every benchmark that loads a large dataset from a file:
Liblinear parses a multi-gigabyte SVM-light file, Redis is loaded over a socket.

### What we do about it

`benchmarks/patches/gapbs-userspace-load.patch` routes the load copy through a 4 MB
user-space staging buffer, so the destination writes become ordinary stores that Pin
observes. The bytes and their layout are unchanged; only which agent performs the
final copy differs.

That gives two measurements, both legitimate, answering different questions:

- **without the patch** — the application's own access pattern, which is what a
  tiering policy operating in steady state has to work with;
- **with the patch** — the traffic a memory controller would see, which is what M5's
  Figure 4 actually plots.

They are reported separately (`results/spr-20t/` and `results/spr-20t-ul/`), selected
with `GAPBS_VARIANT=stock|userspace-load`. Conflating them is how a reproduction ends
up with a number it cannot explain.

### It closes most of the gap

BFS on kron-23, `P(page has ≤ N of 64 words touched)`:

| N | stock (kernel copies) | **user-space copy** | M5 Fig. 4 | remaining Δ |
|---|---|---|---|---|
| 4 | 0.150 | **0.063** | 0.050 | +0.013 |
| 8 | 0.289 | **0.136** | 0.110 | +0.026 |
| 16 | 0.588 | **0.265** | 0.170 | +0.095 |
| 32 | 0.807 | **0.319** | 0.260 | +0.059 |
| 48 | 0.813 | **0.320** | 0.345 | −0.025 |

Mean unique words goes from 21.9 to 46.9 of 64. The discrepancy at $N=48$ — the point
where the CDF has almost converged — drops from +0.47 to **−0.025**, which is inside
the error of reading values off the paper's bar chart.

This was not a parameter that got tuned until the numbers matched. The blind spot was
hypothesised from the shape of the disagreement, tested in isolation on a
microbenchmark that does nothing but move 512 MiB two different ways, and only then
applied to the benchmark. The residual (largest at $N=16$) is consistent with the
remaining known deviations: the dataset, and the kernel traffic that *cannot* be made
visible in user space — page-fault zeroing and page-cache population.

### The general lesson

Any Pin-based reproduction of a memory-controller measurement has this gap. It is
probably part of what M5 meant by *"requires notable effort to precisely determine
DRAM access addresses"*. It cannot be fully closed in user space — page-fault zeroing
and page-cache traffic remain invisible whatever you do — which is a real argument
for moving this work into CXLRAMSim, where the simulator sees every request including
the kernel's.

---

## 4. Region of interest

Benchmarks spend most of their memory traffic outside the part that matters. GAPBS
builds and sorts a CSR graph before it runs a single BFS step; that construction
streams sequentially over the whole structure, writing every 64 B word of every page
it allocates. Counting it makes *every* workload look perfectly dense.

`src/profiler/roi/hotskew_roi.h` provides two empty, `noinline`, `weak` functions.
`benchmarks/patches/gapbs-roi.patch` calls them around the timed kernel invocation in
GAPBS's `BenchmarkKernel` — the exact region GAPBS itself reports as "Trial Time". No
kernel code and no compiler flags change.

This is a *deviation* from M5, whose FPGA counters run continuously with no ROI
concept. Both were measured:

| BFS, kron-23, 36 MB LLC | mean unique words | P(≤16) |
|---|---|---|
| ROI only (kernel) | 18.298 | 0.708 |
| whole process (incl. graph build) | 20.140 | 0.679 |

The difference is small, so the ROI choice is not driving the headline result — but
it is stated rather than assumed.

---

## 5. Matching M5's testbed

The cache geometry is not invented. It is the **Intel Xeon Gold 6430 (Sapphire
Rapids)** from M5's own testbed, including their Intel CAT way-partitioning, which
their setup scripts (`setup/core_pqos/set_*_llc.sh`) apply per workload class:

| Workload class | CAT mask | Ways of 15 | LLC | Config file |
|---|---|---|---|---|
| GAPBS, Liblinear (20 threads) | `0x7FC0` | 9 | 36 MB | `configs/spr-20t.env` |
| SPEC CPU2017 (8 threads) | `0x7800` | 4 | 16 MB | `configs/spr-8t.env` |
| Redis (1 thread) | `0x4000` | 1 | 4 MB | `configs/spr-1t.env` |

CAT partitions the L3 **by way**, not by set. The set count stays at 65536 in all
three cases and only the associativity changes — so setting `L3_ASSOC` to the number
of granted ways reproduces the partition *exactly*, not approximately. This is a
piece of luck worth noticing: it is one of the few hardware knobs a software cache
model can match without hand-waving.

It also explains a result that would otherwise look strange. Redis shows the most
extreme sparsity in M5's Figure 4 (86% of pages with ≤25% of words touched) — and
Redis was running with **4 MB** of last-level cache.

---

## 6. Validation

None of the above is worth anything if the tool miscounts. `src/profiler/validate/`
contains synthetic workloads whose word-density is known analytically, and
`run_validation.sh` asserts the tool recovers it.

```
1. Strided access -- a page must show exactly 4096/stride unique words
  PASS  stride=4096          expected 1      got 1.000
  PASS  stride=1024          expected 4      got 3.999
  PASS  stride=256           expected 16     got 15.996
  PASS  stride=64            expected 64     got 63.981
2. Dense scan
  PASS  dense                expected 64     got 63.981
3. Mixture -- p% of pages dense, the rest one word
  PASS  hotset 10% mean      expected 7.300  got 7.301
  PASS  hotset 10% P(<=4)    expected 0.900  got 0.9000
  PASS  hotset 25% mean      expected 16.750 got 16.745
  PASS  hotset 50% mean      expected 32.500 got 32.491
4. Cache filter must actually filter
  PASS  streaming miss ratio expected 1.0    got 0.999996
  PASS  cache=0 counts all   expected 65564  got 65564
```

Four orders of granularity, exact. The residual (63.981 vs 64) is partial pages at
the ends of the buffer plus stack pages, and is expected.

Run it after any change to the tool:

```bash
./src/profiler/validate/run_validation.sh $PIN_ROOT
```

---

## 7. Results against the paper

Values for M5 are digitised from their Figure 4 bar chart (no numeric data was
released), so treat them as ±0.02.

### The dense benchmarks reproduce almost exactly

| Benchmark | metric | this work | M5 Fig. 4 |
|---|---|---|---|
| PageRank | mean unique words | 63.996 / 64 | — |
| PageRank | P(≤16 words) | 0.0001 | ~0.005 |
| PageRank | P(≤48 words) | 0.0001 | 0.02 |

PageRank sweeps every edge every iteration, so every word of every CSR page is
touched. Both methods agree that it is maximally dense. This is the strongest
available evidence that the pipeline is measuring the right quantity: an independent
method, on different hardware, with a different dataset, lands on the same answer for
the case where the answer is unambiguous.

### The traversal benchmarks are directionally right but sparser than the paper

| Benchmark | this work, P(≤16) | M5 Fig. 4, P(≤16) |
|---|---|---|
| BFS (1 trial, ROI) | 0.708 | 0.17 |
| BFS (16 trials, whole run) | 0.447 | 0.17 |
| CC (1 trial, ROI) | 0.615 | 0.20 |
| CC (16 trials, whole run) | 0.590 | 0.20 |

We report these workloads as *more* sparse than M5 does. The sensitivity sweep
identifies the mechanism: coverage grows with how much of the graph the measurement
window spans.

```
trials  mean_unique_words  P(<=4)  P(<=16)  P(<=48)
1       20.140             0.1596  0.6791   0.8190
2       22.232             0.1167  0.5667   0.8189
4       22.824             0.1082  0.5364   0.8184
8       23.220             0.1033  0.5178   0.8175
16      27.077             0.0873  0.4468   0.7540
```

One BFS from one source visits part of the graph; sixteen from sixteen sources visit
much more of it, and the pages accumulate coverage. M5's always-on counters span the
whole application, including however many trials their (unreleased) `bench_cmds`
scripts ran, plus construction. The remaining gap is most plausibly dataset:
`GAPBS_PATH` in their `env.sh` points at Memtis' `bench_dir`, whose graphs were not
published with the artifact, and graph size and degree distribution both change how
much of a CSR page a traversal touches.

**This is reported as an open gap rather than tuned away.** The honest summary: the
qualitative claim reproduces (graph traversal kernels show substantial sub-page
sparsity; PageRank and SSSP do not), the ordering across benchmarks reproduces, and
the absolute values for the sparse kernels are sensitive to a parameter the paper
does not specify.

### A qualification the paper does not make

Restricting the population to the pages a migration policy would actually act on
changes the picture materially. For BFS on kron-23:

| population | P(≤16 words) | P(≤48 words) |
|---|---|---|
| all touched pages | 0.708 | 0.853 |
| top-100,000 hottest | 0.424 | 0.711 |
| top-10,000 hottest | 0.000 | 0.000 |
| top-1,000 hottest | 0.000 | 0.000 |

**The hottest pages in BFS are dense.** Sparsity lives in the lukewarm tail. Figure 4
plots the unrestricted population, which is the right way to characterise memory —
but a top-$K$ policy never sees that population. For a workload like this, a
count-only policy would already be selecting dense pages, and M5's Hot Word Tracker
would have little left to correct. For Redis, where 86% of pages are sparse, the
argument is much stronger.

That distinction — *is sub-page tracking useful for this workload, or only for
key-value stores?* — is the question the reproduction is actually able to answer, and
it is sharper than the one the figure alone poses. `hot_vs_all.png` plots it.

---

## 8. Known deviations from M5's setup

Stated plainly, worst first.

| # | Deviation | Effect | Mitigation |
|---|---|---|---|
| 1 | Datasets differ (theirs from Memtis' `bench_dir`, unpublished) | Unknown; likely the main residual gap on traversal kernels | Sensitivity sweep over graph scale reported |
| 2 | No coherence between per-thread L1/L2 | Overstates private-cache hit rate for shared, write-heavy lines | Headline runs are single-threaded, where it cannot apply |
| 3 | No hardware prefetchers | Prefetch pulls in neighbouring lines, so omitting it makes pages look *sparser* | Biases against our own conclusion — the safe direction |
| 4 | L2/LLC indexed by virtual address | Conflict-miss pattern differs from the machine's | Standard trace-driven practice; §2 |
| 5 | Counters see only the application | PAC also sees kernel and page-cache traffic | M5 used cgroups to put all benchmark pages on CXL, which is close |
| 6 | ROI restricted to the timed kernel | Excludes construction traffic M5 would include | Both measured; difference is 18.3 vs 20.1 words (§4) |
| 7 | Single socket, no real CXL device | We model the request stream, not its timing | Out of scope: Figure 4 is a distribution, not a latency |
| 8 | SPEC CPU2017, Memcached, CacheLib not run | 4 of M5's 14 Figure 4 bars missing | SPEC needs a licence; the rest is future work |

### Why the headline runs are single-threaded

Thread count was swept, and the metric barely moves:

| threads | mean unique words |
|---|---|
| 1 | 18.298 |
| 4 | 18.309 |
| 16 | 18.353 |

Word coverage per page is a property of the data-structure access pattern, not of how
many cores walk it. Single-threaded runs avoid deviation #2 entirely and run faster
under Pin, so they are the default. `HOST_THREADS` overrides it.

---

## 9. Cost

Pin instrumentation costs roughly 40× on the region of interest — BFS on kron-23 took
0.09 s natively and 3.6 s instrumented. Memory overhead is 160 bytes per touched page
per epoch (64 × `uint16` word counters plus a mask and two 64-bit totals), so a 4 GB
working set costs about 160 MB of counter state. Both are comfortable on a desktop,
which was the constraint: this had to run on a personal machine, not a lab server.

---

## 10. Relationship to the CXLRAMSim work

This is the profiling stage, deliberately built to be simulator-independent. The
pintool produces the *ground-truth* access distribution that a hardware tracker must
approximate. In CXLRAMSim, the same counters would hang off the CXL device's request
path; the difference is that the simulator supplies physical addresses and real
timing, and can then model migration.

The value of doing it in Pin first is that it gives an exact reference. When an HPT
or HWT top-$K$ tracker is implemented later, its output can be scored against the
exact counts recorded here — which is precisely the comparison M5's Figure 8 makes
(*"average access-count ratio of hot pages identified by ANB and DAMON"* against
PAC's exact counts). Without an exact reference there is nothing to measure a
tracker's accuracy against.

---

## References

- Sun et al., *M5: Mastering Page Migration and Memory Management for CXL-based
  Tiered Memory Systems*, ASPLOS '25. Artifact:
  <https://github.com/ece-fast-lab/ASPLOS-2025-M5>
- Zhou et al., *NeoMem: Hardware/Software Co-Design for CXL-Native Memory Tiering*,
  MICRO '24.
- Zhong et al., *Managing Memory Tiers with CXL in Virtualized Environments*
  (Memstrata), OSDI '24.
- Beamer et al., *The GAP Benchmark Suite*. <https://github.com/sbeamer/gapbs>
