# Handbook

Everything in this repository: what it is, how it works, what it found, and where to
put your hands to change it.

Read this once end to end. After that it is a reference — the per-component sections
are self-contained, and § [Extending it](#8-extending-it) tells you which file to open
for each kind of change.

**Companion documents.** This is the "how it works" file.
[`methodology.md`](methodology.md) is the "why it is correct" file and has the
deviation analysis; [`which-failure-mode.md`](which-failure-mode.md) and
[`hardware-evaluation.md`](hardware-evaluation.md) hold the two result sets that go
beyond reproduction; [`tool-reference.md`](tool-reference.md) is the knob-by-knob
manual.

---

## 1. The question, in one page

CXL lets you hang extra DRAM off the PCIe bus. It is cheap capacity but roughly
2.2× the latency of local DDR, so you get a two-tier memory system and something has
to decide what lives where. Today that something is the OS, working in 4 KB pages.

**M5 (ASPLOS '25) argues the 4 KB page is the wrong unit.** They built Page and Word
Access Counters into a CXL controller on an FPGA and showed that a page's accesses
concentrate in a handful of its sixty-four 64 B words — so migrating the whole page
moves mostly cold bytes. Their Figure 4 is the evidence: *P(a 4 KB page has at most N
unique 64 B words accessed)*.

**This repository reproduces that measurement in software, then goes past it:**
implements the bounded hardware trackers M5 proposes and scores them against exact
ground truth, measures what the sub-page information is worth for placement, and
converts the whole thing into a time number.

The eventual target is CXLRAMSim (a gem5-based CXL simulator), which is **not yet
released** — so `src/sim/` is built to make that port small rather than pretending to
have done it.

---

## 2. How the whole thing fits together

```
                    ┌──────────────────────────────────────────────┐
   benchmark        │  GAPBS / Redis / liblinear, ROI-marked        │
   under Pin        └───────────────────────┬──────────────────────┘
                                            │  every load and store
                                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  hotskew.cpp        instrumentation, phases, epochs, output     │
   │    ├─ cache_model.hpp   L1d → L2 → LLC  (per-thread / shared)   │
   │    │                    whatever misses is the "DRAM stream"    │
   │    ├─ counter_table.hpp PAC + WAC: exact counts per 4 KB page   │
   │    │                    and per 64 B word                       │
   │    └─ tracker.hpp       HPT + HWT: bounded top-K approximations │
   │                         scored against the exact counts         │
   └───────────────────────────────┬────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
   .summary.txt              .epochs.csv               .pages.bin
   human-readable            one row per epoch         every (page, epoch)
   + histograms                                        record, 160 bytes
                                                              │
                                   ┌──────────────────────────┘
                                   ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  src/analysis/   hotskew.py          reader + Figure 4 CDF      │
   │                  plot_figures.py     paper-style figures        │
   │                  compare_to_paper.py ours vs M5, per benchmark  │
   │                  hotset_turnover.py  timeliness axis            │
   │                  placement_study.py  what sub-page info is worth│
   │                  latency_model.py    → a speedup number         │
   └────────────────────────────────────────────────────────────────┘

   src/sim/   the same counters and trackers, Pin-free, one call per
              request — ready to drop into a simulator's device port
```

The **key structural idea**: the counting code (`counter_table.hpp`, `tracker.hpp`) has
no dependency on Pin. It takes a line address and a direction. That is what lets the
same code run under Pin today and inside a simulator later.

---

## 3. The profiler, component by component

### 3.1 `cache_model.hpp` — why there is a cache model at all

This is the single most important design decision in the repository, so it is worth
being clear about.

M5's counters sit **inside the CXL controller** and snoop `PA[47:6]` on its way to the
memory controllers. That is the **post-LLC stream**. A Pin memory tracer sees every
load and store the program executes, *before* any cache absorbs it. Caches soak up
exactly the high-reuse traffic that makes a page look hot, so the two distributions
are different questions.

M5 says so, and it is why they built hardware:

> *A dynamic binary instrumentation using Intel Pin can capture every memory access
> address, but it requires notable effort to precisely determine DRAM access
> addresses…* — M5 §3

So the hierarchy goes back in. `CacheLevel` is a set-associative, writeback,
write-allocate, true-LRU cache. Levels cascade: a miss at level *N* queries *N+1*, and
what falls out the bottom is the DRAM stream.

**Deliberate simplifications**, all in the header's comment block: non-inclusive by
default (matches Sapphire Rapids), no coherence between per-thread L1/L2, no
prefetchers. The prefetcher omission biases *against* our own conclusion — prefetch
would pull in neighbouring lines and make pages look denser — which is the safe
direction.

**The CAT trick.** M5 partitions the L3 with Intel CAT. CAT partitions **by way**, so
the set count is unchanged and only associativity moves. Because the model is
way-associative, setting `L3_ASSOC` to the number of granted ways reproduces their
partition *exactly*, not approximately. That is a rare piece of luck and it is why
`configs/spr-*.env` can claim fidelity.

### 3.2 `counter_table.hpp` — PAC and WAC

One record per 4 KB page: 64 × `uint16` word counters, a 64-bit touched-mask, and
read/write totals. 160 bytes per page.

Storage is a two-level radix keyed on 2 MB regions — one hash lookup per region, then
a direct index — with a one-entry cache of the last region. That last-region cache
matters: it turns the common case (consecutive accesses inside one region) into a
compare-and-branch, on a path that runs for every DRAM access.

`forEachTouchedPage(fn)` walks every page with at least one access. `resetCounters()`
zeroes without freeing, so epochs do not pay to re-allocate.

### 3.3 `tracker.hpp` — HPT and HWT

The bounded approximations M5 actually proposes.

**Space-Saving** (Metwally et al.): *N* entries of (key, count, error). Hit →
increment. Miss with space → insert at 1. Miss when full → evict the minimum, reuse
its slot, set count to `min+1` with `error = min`. That last step bounds the
over-estimate: the true count lies in `[count-error, count]`.

The minimum is kept with a binary min-heap plus a hash map from key to heap position.
Incrementing can only push an entry *down*, so an update is one sift-down, O(log N).
Metwally's original uses a Stream-Summary for O(1); the heap is the standard practical
simplification and does not change the output.

**Count-Min Sketch**: D rows × W counters, estimate = min over rows, plus a K-entry CAM
holding the highest estimates. **The CM results came out non-monotone and are flagged
as a suspect implementation** — see [hardware-evaluation.md](hardware-evaluation.md)
§1. Likely the CAM eviction policy. Do not quote those numbers.

`scoreTopK()` implements M5's Figure 8 metric — the access-count ratio of the picked
set over the true top-K.

**Why these live in the pintool rather than in Python:** Space-Saving's output depends
on the *order* accesses arrive in, and the aggregated per-epoch counts in `.pages.bin`
have thrown that away. The tracker has to see the same stream the hardware would.

### 3.4 `hotskew.cpp` — the instrumentation

Per memory operand, Pin inserts an inlinable predicate (`isActive`) and, when true, a
call to `analyzeMemRef`. That two-stage gate is what makes fast-forwarding cheap:
outside the region of interest the cost is a compare and a branch.

**Phases** are driven by a basic-block instruction counter:
`FASTFORWARD → WARMUP → PROFILE → DONE`.

**Locking**: L1 and L2 are per-thread and take no lock at all. Only L2 misses touch
shared state (LLC, counters, trackers). That is what keeps multithreaded runs from
serialising, and it was a deliberate fix — an earlier version locked on every
reference, including L1 hits.

**Epochs** are the measurement window and are covered in §4.

---

## 4. The three ideas that make the measurement correct

If you internalise nothing else, internalise these. They are the parts most likely to
be probed, and each was found the hard way.

### 4.1 The measurement window makes the question well-posed

Unique-word coverage per page **only ever grows**. Measure long enough and every page
looks dense. Measured over an unbounded window, the result was *byte-identical* for a
4 MB and a 60 MB LLC:

| config | LLC | DRAM accesses | mean unique words |
|---|---|---|---|
| nocache | — | 168,833,290 | **18.298** |
| spr-1t | 4 MB | 13,056,974 | **18.298** |
| spr-full | 60 MB | 8,873,468 | **18.298** |

The access *count* varies 19×; the touched *set* does not vary at all, because
compulsory misses eventually touch everything. **A sparsity number without a stated
window length and kind is not reproducible.**

M5's hardware has the same property — WAC's counters are 4 bits wide and are read and
reset periodically, and their PAC daemon dumps every 10 ms (`m5_manager -s 10`).

**Two kinds of window, and it matters.** A window measured in DRAM accesses normalises
away cache size (a smaller cache emits more accesses, so a fixed count spans less
execution — the effects cancel exactly). A window measured in *instructions* is the
time-proportional one and is what M5's 10 ms dumps correspond to. Hence both `-epoch`
and `-epoch_ins`.

### 4.2 Pin cannot see kernel-side memory traffic

Pin instruments application instructions. Memory the *kernel* touches on the
application's behalf — the copy inside `read(2)`, page-fault zeroing, page-cache
population, DMA — executes no user-mode load or store, so nothing fires. M5's counters
at the memory controller see all of it.

Measured in isolation (`src/profiler/validate/kernel_blindspot.c`), moving 512 MiB:

| how | DRAM accesses Pin sees | pages | words/page |
|---|---|---|---|
| `read(2)` — kernel copies | **5** | 4 | 1.250 |
| `memcpy` — app copies | **24,838,154** | 262,150 | **63.999 / 64** |

GAPBS loads its 1.05 GB CSR with `file.read()` (`reader.h`, `ReadSerializedGraph`).
That is ~269,000 pages M5 records as perfectly dense and Pin records as nothing.
`benchmarks/patches/gapbs-userspace-load.patch` routes the copy through a user-space
staging buffer, and it moves BFS's `P(≤48)` from **0.813 → 0.320** against M5's
**0.345**.

**This is also the strongest argument for the simulator**: in gem5 the device request
path sees kernel traffic too, and the blind spot does not exist.

### 4.3 Virtual addresses are exact for this metric

Pin sees virtual addresses; PAC/WAC index physical ones. For the Figure 4 metric this
does not matter *at all*, and the reason is worth being able to state:

The metric is the popcount of which of a page's 64 words were touched. The word index
is `addr[11:6]`, and under 4 KB paging `VA[11:0] ≡ PA[11:0]` by definition —
translation replaces the bits above 11 and leaves the page offset alone. A virtual
page maps to exactly one physical page, so grouping by VPN and by PFN produce the
*same* partition. This is exact, not an approximation.

The approximation is confined to **L2/LLC set indexing**, which uses bits above 11
where VA and PA diverge. Standard trace-driven practice; stated rather than hidden.

---

## 5. Running things

```bash
make -C src/profiler/pintool PIN_ROOT=/path/to/pin      # build
./src/profiler/validate/run_validation.sh /path/to/pin  # prove it measures truth
./benchmarks/setup_gapbs.sh 23                          # both load variants
./benchmarks/setup_redis.sh                             # jemalloc + ROI + client

PIN_ROOT=... ./experiments/run_hotskew.sh gapbs-bfs      # one benchmark
PIN_ROOT=... ./experiments/run_all_gapbs.sh both         # all six, both variants
PIN_ROOT=... ./experiments/run_redis.sh spr-1t 2000000 10000000
PIN_ROOT=... ./experiments/run_trackers.sh bfs cc tc     # deliverable 1
PIN_ROOT=... ./experiments/sensitivity_sweep.sh all      # every methodological axis
./experiments/stop_runs.sh --kill                        # stop everything, reliably
```

Analysis (needs the venv):

```bash
./.venv/bin/python src/analysis/compare_to_paper.py --config spr-20t-ul
./.venv/bin/python src/analysis/placement_study.py  --config spr-20t
./.venv/bin/python src/analysis/latency_model.py    --config spr-20t --sensitivity
./.venv/bin/python src/analysis/hotset_turnover.py  --config spr-20t --k 128000
./.venv/bin/python src/analysis/plot_readme.py
```

### Three operational hazards, learned the hard way

1. **Never edit a shell script while it is running.** Bash re-reads the file by byte
   offset as it executes; an edit shifts the offsets and it resumes mid-token. The
   failure looks like a syntax error on a line that is perfectly valid. This happened
   twice and corrupted a run each time.
2. **Never relink the `.so` while a run has it mapped.**
3. **`pkill -f pin` does not work.** Pin rewrites the injected process's `argv` to the
   *application's*, so a pin-controlled BFS appears in `ps` as plain `bfs`. A stale
   PageRank survived three cleanup attempts and spent 38 minutes appending to a
   `.pages.bin` another run had already written. `experiments/stop_runs.sh` matches on
   `hotskew.so` in `/proc/PID/maps`, which argv rewriting cannot affect.

---

## 6. Output formats

| file | contents |
|---|---|
| `<prefix>.summary.txt` | config, Figure 4 CDF, full 65-bin unique-word histogram, log2 histogram of accesses per page (Figure 10), tracker scores |
| `<prefix>.epochs.csv` | one row per epoch: pages, accesses, mean unique words, the five CDF points |
| `<prefix>.tracker.csv` | one row per (epoch, budget): HPT/HWT access ratio and recall |
| `<prefix>.pages.bin` | raw records, 160 bytes each — everything else is derivable from this |

`.pages.bin` record, little-endian packed:

```
uint32  epoch
uint64  page_number        (byte address >> 12)
uint64  reads
uint64  writes
uint64  touched_mask       bit w set iff 64 B word w was accessed
uint16  word_counts[64]
```

A run that recorded nothing writes `STATUS NO DATA` and the likely causes, rather than
a CDF over an empty population — a table of zeros reads exactly like a very sparse
result, which is how a failed run becomes a "finding".

---

## 7. Every finding, with its evidence

### 7.1 The tool is calibrated

Synthetic workloads with analytically known density (`src/profiler/validate/synth.c`):

| stride | analytic | measured |
|---|---|---|
| 4096 B | 1 | 1.000 |
| 1024 B | 4 | 3.999 |
| 256 B | 16 | 15.996 |
| 64 B | 64 | 63.981 |

Plus mixtures: 10% dense pages / 90% single-word gives mean 7.301 against an analytic
7.300, and `P(≤4 words) = 0.9000` against 0.90.

### 7.2 M5 Figure 4 reproduces on 5 of 7 workloads

`P(page has ≤ N of 64 words touched)`, ours / M5:

| workload | N=4 | N=8 | N=16 | N=32 | N=48 |
|---|---|---|---|---|---|
| pr | 0.000/0.000 | 0.000/0.000 | 0.001/0.005 | 0.001/0.010 | 0.006/0.020 |
| tc | 0.022/0.020 | 0.044/0.050 | 0.090/0.120 | 0.281/0.265 | 0.527/0.520 |
| bfs | 0.063/0.050 | 0.136/0.110 | 0.265/0.170 | 0.319/0.260 | 0.320/0.345 |
| cc | 0.056/0.060 | 0.121/0.125 | 0.267/0.200 | 0.372/0.290 | 0.374/0.385 |
| redis | 0.495/0.510 | 0.680/0.765 | 0.805/0.865 | 0.958/0.925 | 0.987/0.940 |
| bc | 0.160/0.005 | … | 0.418/0.040 | … | 0.638/0.145 |
| sssp | 0.139/0.005 | … | 0.356/0.025 | … | 0.543/0.110 |

Landing on **both extremes** — PageRank at 63.1/64 words and Redis at 8.9/64 — is the
evidence the tool measures the right quantity.

`bc` and `sssp` are **bounded, not unexplained**: a 10M-access epoch is the sparsest
window measured and the whole run the densest possible, and M5's value falls inside
that range for both (bc: 0.638 / 0.0007 / **0.145**; sssp: 0.543 / 0.0006 / **0.110**).
They are also the exact two kernels M5 runs on the **Google** graph rather than
Twitter (their §6), which we do not have.

### 7.3 Redis needed two fixes, both of which move the number directly

- **jemalloc, not `MALLOC=libc`.** In a KV store the allocator decides which values
  share a page.
- **YCSB's real record layout: 10 × 100 B hash fields, not 1 × 1000 B string.** A
  1000 B value spans 16 cache lines, so `P(≤8 words) ≈ 0` *by construction*. This one
  change moved `P(≤4)` from 0.263 → **0.495** against M5's 0.510.

### 7.4 A bounded HPT is small — and its size is set by the cold tail

Space-Saving, access-count ratio vs the exact top-K:

| workload | N=50 | N=128 | N=512 | N=8192 |
|---|---|---|---|---|
| bfs | 0.283 | **0.737** | 0.755 | 0.757 |
| cc | 0.250 | **0.654** | 0.679 | 0.600 |
| storage | 0.4 KB | **1 KB** | 4 KB | 68 KB |

Knee at 1 KB, then flat. And the self-test threshold:

$$N > n_\text{hot} + \frac{n_\text{cold}}{\text{hits per hot page}}$$

because an evicted slot inherits `min+1`, so cold entries inflate to ≈ `n_cold/N`.
**The tracker size you need is set by the cold tail, not the hot set.** Measured: 256
entries loses a 64-page hot set entirely (0.002); 512 recovers it exactly.

Recall is ~0 while the ratio is 0.75 — the tracker picks pages that are *as hot* but
not the *same* pages. That is precisely why M5 reports an access-count ratio.

### 7.5 Sub-page information does not improve placement, and there is a reason

M5's two nominators against count-only, at a 50% fast tier: **no gain on any workload,
including Redis** (their Guideline 4 case). Structural reason: with page-granular
migration a page costs 4096 bytes whether 2 or 64 of its words are hot, so **access
count is a sufficient statistic** for selection.

The waste is nonetheless real — **81% of every migrated page is never touched for
Redis**, 48% for `bc`, 3% for `pr`. Recovering it needs sub-page migration or
compaction, which M5 explicitly does not do.

Important qualifier: our count-only baseline uses **exact** counts, while a real HPT
is only ~0.75 accurate (§7.4). Re-running this with tracker-derived scores is the
honest next experiment and the regime where a second signal should help most.

### 7.6 On graph analytics, timeliness binds and granularity does not

At K=128,000 pages (512 MB, M5's size), concentration is ~1.0, so any shortfall is
pure lag cost:

| kernel | tc | bc | bfs | cc | sssp | pr |
|---|---|---|---|---|---|---|
| staleness | 0.902 | 0.850 | 0.841 | 0.830 | 0.602 | **0.381** |

**10% to 62% of the achievable benefit lost to acting one epoch late** — while the
pages a policy would migrate are already dense (`P(≤16 words) = 0.000` for every
kernel among the top 10k). That is NeoMem's thesis, not M5's.

Caveat: `retention` is unreliable under near-ties. PageRank shows retention 0.086 with
concentration 1.000, because most pages are equally hot and the ranking is arbitrary.
Read the staleness column.

### 7.7 The closed-loop number

Two-tier latency model (`latency_model.py`): local 100 ns, CXL 220 ns, migration 3 µs.
Sources: NeoMem Fig. 1 measures local DDR at 118 ns and notes the field assumes CXL at
170–250 ns; Memstrata states CXL is "roughly 200–220% the latency of local memory".

| policy | geomean speedup vs all-CXL | gap closed |
|---|---|---|
| all-local (bound) | 2.200× | 100% |
| oracle | 1.618× | 70% |
| **count-only (HPT alone)** | **1.505×** | **61%** |
| hwt-driven | 1.475× | 59% |
| hpt-driven | 1.412× | 53% |

Redis: 1.607× for count-only, 69% of the gap.

**Migration cost is the knife edge:**

| L_migrate | 0 | 1 µs | 3 µs | 10 µs | 30 µs |
|---|---|---|---|---|---|
| speedup | 1.665× | 1.608× | **1.505×** | 1.238× | **0.835×** |

At 30 µs migration is a **net loss**. Tiering only pays if a promotion stays under
~10 µs — which is exactly why the profiling overhead M5 and NeoMem attack matters.

**Three assumptions, all inflating the benefit:** no memory-level parallelism (the big
one — real cores overlap misses), no bandwidth contention, open-loop trace. Report
these as memory *stall time* and as an upper bound.

---

## 8. Extending it

| you want to… | open |
|---|---|
| change the cache hierarchy | `configs/*.env`, or `cache_model.hpp` for new policies |
| add a tracker algorithm | `tracker.hpp` — implement `access` / `topK` / `reset`, add a slot in `hotskew.cpp` |
| add a placement policy | `placement_study.py`, the `cand` dict — one line per policy |
| change the latency model | `latency_model.py`; migration cost is the least certain input |
| add a benchmark | `benchmarks/setup_*.sh` + an ROI patch + a case in `run_hotskew.sh` |
| profile something in a simulator | `src/sim/hotskew_probe.hpp` — one call per request |
| add a metric over raw data | `src/analysis/hotskew.py`, the `Run` class |

### The four experiments I would do next, in order

1. **Re-run the placement study with tracker-derived scores** instead of exact counts.
   This is the fair test of M5's nominators and needs perhaps 50 lines — plumb the
   tracker's top-K out of the pintool per epoch. *Highest value, lowest effort.*
2. **Fix the Count-Min CAM** and re-run deliverable 1, so the Space-Saving vs sketch
   comparison M5 makes can actually be reported.
3. **Memstrata's axis.** Intel Flat Memory Mode is mechanically a direct-mapped cache
   with 64 B lines indexed `line_addr mod L` — `assoc=1` in the existing model. Needs
   a VA→PA allocator model (which page colouring requires anyway) and two co-running
   traces. That would give all three papers' failure modes on one instrument.
4. **Real datasets.** M5 §6 names Twitter (bfs/cc/tc/pr) and Google (bc/sssp). The web
   graph is small and easy; Twitter is not.

### Things that are wrong or unfinished, honestly

- **Count-Min results are non-monotone** and should not be quoted (§3.3).
- **The `hpt-driven` nominator** uses a median-split to model "pages HPT reported",
  which is a stand-in for a real bounded HPT membership test.
- **Liblinear is scripted but never run** — `setup_liblinear.sh` downloads a 2.5 GB
  dataset from an academic host that is often slow.
- **SPEC CPU2017 is absent** (licence), so 4 of M5's 14 Figure 4 bars are missing.
- **Everything is single-threaded.** Thread count was swept and barely moves the
  Figure 4 metric (18.298 → 18.353 across 1→16 threads), but the multithreaded cache
  model has no coherence between per-thread L1/L2, so MT numbers would need that first.
- **`.pages.bin` files are large** (0.3–1.5 GB) and gitignored. Regenerate rather than
  archive.

---

## 9. Provenance

This was built in a pair-programming session with an AI assistant (Claude). The
direction, the decisions about what mattered, and the judgement calls about scope were
the author's; a large share of the code, the analysis scripts, and the prose were
generated. That is worth stating plainly, both because it is true and because the
value of the work now depends on being able to defend every number in it without
notes.

The reasoning chains most worth being able to reconstruct from scratch, because they
are the ones a reader will probe:

1. Why the epoch makes the question well-posed (§4.1) — and why every cache size gave
   an identical answer.
2. Why `read(2)` traffic is invisible to Pin, and how that was isolated (§4.2).
3. Why `VA[11:0] ≡ PA[11:0]` makes virtual addresses *exact* here (§4.3).
4. Why Space-Saving's required size depends on the cold tail (§7.4).
5. Why access count is a sufficient statistic for page-granular placement (§7.5).
6. Why the migration-cost crossover at ~10 µs is the most actionable number here (§7.7).
