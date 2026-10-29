> **October 2026 audit:** Historical results below predate confirmed cache-path
> corrections. The window-fit causal explanation, HWT-gating explanation and
> 1.505x speedup claim are withdrawn. See [the audit](audit-2026-10.md) and
> [current methodology](methodology.md) for the corrected interpretation and paired
> access/miss measurements. Historical numerical agreement is not proof of replication.

# Handbook

The [27 October fidelity follow-up](fidelity-followup.md) tracks the current
attempt to improve agreement with M5. It explains every new input reduction and
execution control and reports all completed cases, including negative results.
The additional HDD is mounted at `/mnt/research`; this expands project storage
while Ubuntu and the repository stay on the SSD.

The first Twitter BFS/CC measurements are validated but still far from M5:
their largest CDF differences are 55.6 and 49.2 percentage points across the
five thresholds. The new inputs help only slightly. This is evidence against
input family alone explaining the gap, not a reason to tune inputs to the plot.

Twitter PageRank has now completed too. Its pooled demand-fill discrepancy is
1.53 percentage points, slightly above the prior Kronecker value of 1.08. This
is close numerically, not an improvement or proof of identical methodology.

Twitter TC is also complete and validated: pooled demand-fill discrepancy falls
from 41.6 to 34.9 percentage points. This remains poor agreement. Its native
footprint is only about 0.71 GiB versus M5's reported 5.0 GB; using the same source
graph family has not recovered the authors' reduction or working set.

The full first input campaign is now complete. Larger Google+ BC/SSSP inputs
worsen pooled demand-fill errors to 77.6/79.6 percentage points. Their whole-ROI
errors are 14.1/10.9 points, but choosing the better-looking scope after collection
would not establish M5's protocol. Both views remain published.

The 200-trial, one-thread BFS control is also complete. Its pooled access and
fill discrepancies are 59.6 percentage points, versus 59.1 on the one-trial
baseline. Repetition alone therefore does not close the pooled gap. Across the
entire run, the discrepancy falls to 24.1 points: more trials touch more distinct
lines in the union, while each pooled observation still covers only 10M memory
events. These are different questions, not interchangeable estimates. CC's
matching repetition control is complete too: pooled fill error is 58.0 points
versus 50.5 previously, so it does not improve agreement either.

Full-process BFS and CC on the real inputs are now validated. Including observed
user-space setup changes pooled fill error from 55.6 to 50.7 points for BFS,
and from 49.2 to 44.8 for CC. Access errors change similarly, to 50.7 and 44.7
points. This identifies a modest collection-scope effect; it neither recovers
invisible kernel traffic nor establishes that M5 used full-process collection.
Full-process SSSP similarly changes pooled fill error only from 79.6 to 78.1
points. Combining the real Twitter input with 20 software threads gives BFS
56.0 points versus 55.6 with one thread: this control does not improve agreement.
The same 20-thread control for CC gives 49.27 points versus 49.22 with one thread.
This difference is tiny relative to the digitized reference's uncertainty; the
proper conclusion is no meaningful change, not evidence for a thread-count effect.
BC's matching control gives 77.66 versus 77.58 points, also essentially unchanged.
Twenty-thread SSSP gives 80.20 versus 79.65 points. Thus none of the four
real-input thread controls closes the pooled gap. Nine LLC ways instead of ten
gives BFS 54.89 versus 55.56 points and CC 49.23 versus 49.22. These are small
changes, not evidence that the artifact's nine-way mask explains the mismatch.
Nine-way BC and SSSP are also validated: pooled fill errors are 77.70 and 79.97
points versus 77.58 and 79.65 with ten ways. No large LLC-way effect appears in
these four controls. TC input preparation waited for 26 GiB available host RAM
while simulator PageRank occupied about 10 GiB. That wait has cleared. All three
predeclared native footprint candidates exceeded the 5.0 GB target. The nearest,
the 10/16 induced hash subset, measured 8.89 GB peak RSS (77.9% above target).
It was selected by RSS only, before its Pin CDF, and is now being profiled. This
is not a size-matched reproduction; the residual footprint mismatch is retained.

The [second Pin campaign](pin-stage2-protocol.md) tests full observed process
scope, twenty-thread real-input runs, nine LLC ways and an RSS-selected TC graph.
Its [live results report](pin-fidelity-stage2.md) retains all outcomes and labels
reference-selected closest cases as exploratory. Accesses and misses are measured
together. Pin still cannot see kernel copies during setup.

There is now also a [simulator version of the Figure 4 comparison](simulator-figure4.md).
It uses completed CXL-bridge measurements, not the Pin cache filter. BFS/CC are
closer to the reference in these runs, while BC/SSSP are farther away. That does
not isolate the effect of observing kernel traffic: the simulator changes inputs,
CPU, OS, caches and placement too. Bridge and downstream controller must never be
added together; they observe overlapping traffic.

Simulator PageRank is now complete too: 1,472,860,926 bridge requests across
148 windows, with a maximum five-threshold CDF difference of 1.58 percentage
points from M5. All three port histograms passed checks and ROI exit was recorded.
The run took 16.56 hours. This is close numerical agreement, within the approximate
digitization uncertainty, but does not establish identical inputs or hardware.
Simulator TC is running; its bars remain pending until completion and validation.

## Start with the audited measurement

### Are the extensions still usable?

Checkpoint/resume development is tracked in [checkpointing.md](checkpointing.md).
Synthetic and bounded full-system process-restore tests now pass, including
identical probe outputs and completion tick. Managed simulator runs can use
periodic disk snapshots; old interrupted runs without a snapshot must restart.
A real reboot restore is still untested. A summary alone is never a checkpoint.

The methods can still be useful, but results obtained before a counting fix need
new measurements. The [fresh revalidation report](revalidation-2026-10-25.md)
shows what has actually passed, what is running, and new graphs as they become
available. It does not mix old and new numbers.

For each completed raw-data run, we check that its per-page records reconstruct
the summary exactly. Then we recompute granularity (how the tracking-unit size
changes apparent density), turnover (whether yesterday's hot set predicts the
next window), and placement (choosing pages using only the previous window).
One-window runs cannot answer the last two questions. The latency calculation
is still an assumed serial-memory cost, not measured program speedup.

Two independent user services run the Pin and simulator queues:
`systemctl --user status memory-tiering-revalidate-pin memory-tiering-revalidate-sim`.
They continue without this chat open, but not while Linux is shut down or suspended.
After a restart, run `.venv/bin/python experiments/revalidation_campaign.py pin`
and, separately, the same command with `sim`. Completed jobs are preserved.
Without checkpoint options, interrupted workloads restart from the beginning.
The managed simulator command and explicit safe-pause procedure are documented
in [checkpointing.md](checkpointing.md); use them to preserve mid-run state.

For current experiments, read [methodology.md](methodology.md) and the
[audit report](audit-2026-10.md) before the historical chapters below. The newer
profiler counts accesses and modeled misses together, propagates dirty evictions
correctly, and serializes its measurement state. The old discussion of lock-free
private accesses describes the previous implementation.

Think of the new experiment as three notebooks watching the same program: one
records every demand reference, one records cache fills, and one records fills
plus dirty writebacks. In the initial experiment, every 10 million demand line
references all three close their current window together. In the latest campaign,
the same boundary is instead triggered by 10 million modeled memory events.
A bitmask says which of a page's 64 lines each
notebook saw. We then count how many pages have at most 4, 8, 16, 32 or 48 bits set.

The denominator matters. One plot includes the pages each notebook saw; another
compares both notebooks on exactly the same pages. A whole-kernel plot unions the
bits without resetting. None of these is automatically the paper's measurement:
its graph inputs, thread count and exact collection procedure still need matching.

Commands and complete/failed status live in the new run manifests. The benchmark
must finish successfully before its curve appears in the new plots. An old summary
file alone is not a completion certificate, and partial data is not a checkpoint.

### Latest follow-up: which Google graph?

The artifact uses **Google+ social connections**, not the Google web-link graph
we previously tried. We obtained the original Google+ archive, selected its
published first temporal snapshot and reran BC and SSSP. This is closer to the
intended input family, but not the authors' exact resized files.

We also compared two stopwatches for each window: one advances for every raw
reference; the other only advances when the model sends a memory event. Both
access and miss notebooks still close together. A memory-event window generally
covers more program execution, giving more lines a chance to be touched.

With 10M memory events per window, the five-point maximum errors improve from
0.572 to 0.303 (BC) and 0.646 to 0.339 (SSSP). With 10M raw references, this
improvement does not hold consistently. **Closer under one declared protocol
does not prove we reproduced the paper's protocol.** The graph size also changes.

Read [the follow-up](reproduction-followup.md) for every comparison, source hashes,
reproduction commands and the exact files/settings still needed from M5's authors.

### Latest complete six-workload campaign

We have now applied the memory-event clock to **all six** kernels. PageRank's
maximum traffic error over the five reference thresholds falls to 0.011. TC
improves from 0.530 to 0.416; BFS and CC get worse, to 0.591 and 0.505.
Google+ BC/SSSP remain at 0.303/0.339. So this explains some discrepancies,
but does not reproduce five of the six curves.

Why do accesses and misses now look so similar? We count **which lines appeared**,
not how often. Repeated hits do not add bits. A longer interval gives a line more
chances to miss at least once. For BFS the entire kernel produces fewer than 10M
memory events, so we have one whole-kernel window: every first touch must miss
our initially empty cache. The coverage masks therefore match, although BFS has
168.8M accesses and only 7.9M fills. Equal bars do not mean the cache does nothing.

See [the uniform-window report](uniform-windows.md) for both full figures, negative
results, per-stream scores and the old baseline's missing input-hash caveat.
The [author-request draft](m5-author-request.md) lists the exact inputs and
measurement details we still need. It has not been sent.

Everything in this repository: what it is, how it works, what it found, and where to
put your hands to change it.

Read this once end to end. After that it is a reference — the per-component sections
are self-contained, and § [Extending it](#8-extending-it) tells you which file to open
for each kind of change.

**If the terminology is unfamiliar, read [Vocabulary](#vocabulary) first.** It defines
every term this project uses — CXL, pintool, ROI, set-associative, CDF and the rest —
in a sentence or two each, with why it matters here. Nothing below assumes you have
worked with Pin or gem5 before.

**Start here if you only read one thing:** [`claims.md`](claims.md) lists every
headline number with the command that regenerates it, and `./experiments/check_claims.sh`
verifies the lot. If a number in any other document disagrees with it, that document is
the bug.

**Companion documents.** This is the "how it works" file.
[`methodology.md`](methodology.md) is the "why it is correct" file and has the
deviation analysis; [`which-failure-mode.md`](which-failure-mode.md) and
[`hardware-evaluation.md`](hardware-evaluation.md) hold the two result sets that go
beyond reproduction; [`tool-reference.md`](tool-reference.md) is the knob-by-knob
manual.

---

## Vocabulary

Everything in this project that sounds like jargon, in plain English. Skip it if
the terms are already familiar; come back when one bites.

### The hardware problem

**CXL** — a standard that lets you attach extra DRAM over the PCIe bus instead of
plugging it into the usual memory slots. You get far more capacity, at roughly
**2.2× the latency**. So a machine now has *fast memory* (normal DDR) and *slow
memory* (CXL), and something has to decide which data lives where.

**Memory tiering** — that decision, made continuously while the program runs. Move
frequently-used ("hot") data to fast memory, leave the rest in slow memory.

**Page** — the unit the operating system moves memory in: **4 KB**. **Word** (in this
project) — a **64 B** cache line, the unit the hardware actually fetches. A page is
64 words. The whole argument of M5's paper is that these two units are badly matched:
you migrate 4 KB but the program may only touch a few of its 64 words.

**Hot skewness** — the observation that accesses inside a page are *skewed*: heavily
concentrated in a few words rather than spread evenly. If pages were uniformly
touched, sub-page tracking would be pointless.

### What M5 proposes

**PAC / WAC** — Page Access Counter and Word Access Counter. Hardware counters in the
CXL controller: PAC counts accesses per 4 KB page, WAC counts per 64 B word.
`counter_table.hpp` is our exact software version of both.

**HPT / HWT** — Hot Page Tracker and Hot Word Tracker. Real hardware cannot afford a
counter for *every* page, so these keep only the top-K hottest, in a fixed amount of
SRAM. `tracker.hpp` implements them.

**Top-K tracker** — a data structure that sees a stream of addresses and tries to
report the K most frequent while storing far fewer than K entries' worth of history.
We implement two: **Space-Saving** (keeps N entries, evicts the smallest, is provably
never wrong by much) and **Count-Min Sketch** (a hash-based approximate counter, used
by NeoMem).

**Access-count ratio** — the score for a tracker: of all the accesses that went to the
genuinely-hottest pages, what fraction went to the pages the tracker *named*? 1.0 is
perfect. This is the y-axis of M5's Figures 3, 7 and 8.

### Measuring it

**Intel Pin** — a tool that rewrites a program's machine code *as it runs* and splices
in your own function calls. Called **dynamic binary instrumentation (DBI)**. No
recompilation, no source changes.

**A pintool** — the plugin you write against Pin's API. Pin ships samples
(`pinatrace`, `dcache`); ours is `hotskew.cpp`. Writing one is the normal way to use
Pin, not an unusual step.

**Instrumentation routine vs analysis routine** — the one concept you must not
confuse. An *instrumentation* routine runs **once**, when Pin first sees a piece of
code, and decides what to insert. An *analysis* routine runs **every time** that code
executes, and does the work. Mixing them up means either measuring nothing or running
1000× too slow.

**Basic block (BBL)** — a straight-line run of instructions with no branches in or
out. We count instructions one call per basic block rather than one per instruction,
which is much cheaper.

**ROI (region of interest)** — the part of the program we actually measure. GAPBS
loads a graph and then runs the algorithm; only the algorithm is interesting, so the
ROI brackets it. Marked by two empty functions the tool attaches to.

**Epoch / measurement window** — counters are reset every N DRAM accesses, and each
such window is scored separately. This matters more than it sounds: it turned out to
be the single biggest factor in whether our numbers match M5's.

### Simulating it

**gem5** — a full-system computer simulator. It boots a real Linux kernel on a
simulated CPU, so it sees *everything*, including what the kernel does. Pin only sees
the application.

**SimCXL / CXL-DMSim** — a gem5 fork that models a CXL memory device. We use it
because CXLRAMSim, the simulator named in the brief, was never released.

**ATOMIC vs Timing CPU** — gem5 CPU models. **ATOMIC** is fast and unrealistic
(memory returns instantly); **Timing** models real cache and memory delays and is far
slower. We boot under ATOMIC and switch to Timing for the part we measure. Usefully,
ATOMIC issues a different internal call (`recvAtomic`) that our probe does not hook —
so anything run under ATOMIC is automatically invisible to the measurement.

**m5 ops** — magic instructions a program inside the simulated machine can execute to
talk to the simulator ("stop here", "switch CPU"). Our ROI markers use them.

### The cache model

**Set-associative cache** — the standard design. An address maps to one **set**
(chosen by some of its bits); within that set it can sit in any of N **ways**. N is
the **associativity**. Two addresses compete only if they land in the same set.

**LRU** — least-recently-used, the rule for which line to evict when a set is full.

**Writeback / write-allocate** — a modified line is written to memory only when
evicted (not immediately), and a write that misses first fetches the line.

**Inclusive vs non-inclusive** — whether data in L1/L2 must also be present in L3. We
model non-inclusive, matching Sapphire Rapids.

**LLC** — last-level cache, here L3.

**Intel CAT** — Cache Allocation Technology: lets you give a workload only some of the
L3's **ways**. Because it partitions by way and our model has associativity as a
parameter, setting the associativity to the number of granted ways reproduces the
partition *exactly* rather than approximately (§3.1).

### Reading the results

**CDF** — cumulative distribution function. Figure 4 plots **P(≤N)**: the fraction of
pages touching *at most* N distinct words. Low values mean dense pages, high values
mean sparse ones.

**Max error** — how we score a reproduction: the largest gap between our curve and
M5's across all five N values. Scoring at one N would flatter us, because the curves
converge at N=48.

**Geomean** — geometric mean, used for averaging speedup ratios, where an arithmetic
mean would over-weight the largest.

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

CXLRAMSim (the gem5-based CXL simulator the brief named) is **still unreleased**, so
the port went to **SimCXL / CXL-DMSim** instead — public, gem5 23.1, models a CXL
Type 3 memory expander. `src/sim/` made that port small, and the port has now been
done and run: see `src/sim/simcxl/` and §7.

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
              request — dropped into gem5 unchanged (src/sim/simcxl/)
```

The **key structural idea**: the counting code (`counter_table.hpp`, `tracker.hpp`) has
no dependency on Pin. It takes a line address and a direction. That is what lets the
same code run under Pin and, unchanged, inside gem5. That was a design claim until
the full-system campaign tested it; only the *placement* of the call changed.

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
prefetchers. Prefetching can add traffic or displace demand misses and change
replacement; its omission gives no general direction of bias.

**The CAT trick.** M5 partitions the L3 with Intel CAT. CAT partitions **by way**, so
the set count is unchanged and only associativity moves. Because the model is
way-associative, setting `L3_ASSOC` to the number of granted ways reproduces their
capacity and associativity. These configurations remain approximations because
physical indexing, slice hashing, replacement and coherence are not reproduced.

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
holding the highest estimates.

This had a real bug and a real measurement error, and untangling them is instructive.
The CAM used to cache each entry's estimate at the moment its key was last accessed,
then compare a *fresh* candidate against those *stale* values — quantities sampled at
different times, so the comparison meant nothing and an early entry could squat.
Fixed: estimates are re-read from the sketch before any comparison and unconditionally
before reporting top-K.

That fix alone did **not** restore monotonicity, and the remaining cause was not in
the code at all — see §4.4. Current numbers are in
[hardware-evaluation.md](hardware-evaluation.md) §1 and are now usable.

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

## 4. The four things that make the measurement trustworthy

If you internalise nothing else, internalise these. They are the parts most likely to
be probed, and each was found the hard way.

### 4.1 The measurement window makes the question well-posed

> **Since measured.** `window_fit.py` searches the window offline by merging epochs
> (`.pages.bin` stores per-page masks per epoch, and OR-ing *m* consecutive epochs is
> exactly what a window *m* times longer would have recorded). Result: BC 0.378 →
> **0.010** at 180M accesses, SSSP 0.433 → **0.013** at 50M. One window for all six
> kernels takes the worst case **0.433 → 0.199**. It is a one-parameter fit, not a
> reproduction — but the same single parameter works for every workload, and the paper
> does not state it. See `claims.md`.

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
read periodically. We first read `m5_manager -s 10` as a 10 ms window; that turned out
to be the polling cadence, and the effective window is not recoverable from the paper
(report §5.4b).

**Two kinds of window, and it matters.** A window measured in DRAM accesses normalises
away cache size (a smaller cache emits more accesses, so a fixed count spans less
execution — there is no exact cancellation law). A window measured in *instructions* is the
time-proportional one. Hence both `-epoch`
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

**This was the strongest argument for the simulator, and it was tested — twice, because
the first test was confounded.**

In gem5 the request path sees kernel traffic and the blind spot does not exist. The
first comparison measured the simulator over a *wider* window than Pin (it included
the data load), so it changed two things at once and could not attribute either.
The earlier claim that `--switch-at-roi` isolated kernel visibility is withdrawn.
The comparison also changed cache behavior, address space and setup coverage.
The following historical differences are not a decomposition of kernel traffic:

| workload | historical difference (not attributable to kernel traffic alone) |
|---|---|
| bc | **+12.35** |
| cc | **+7.50** |
| sssp | **+4.97** |
| bfs | **+0.90** |

All positive, but spanning an order of magnitude — so this is **not** a uniform
correction you can apply to every workload.

**Leading hypothesis (untested):** the size tracks how much the kernel *allocates*
during the ROI, meaning the mechanism is page-fault zeroing rather than anything about
the access pattern. `bfs` walks a graph that is already in memory and barely faults;
`bc` allocates fresh per-source arrays throughout its kernel. `getrusage` minor-fault
counts around the ROI markers would confirm or kill this in minutes, with no
simulation.

**Do not convert these into "X% of the disagreement with M5".** That decomposition was
attempted and retracted: it assumes the error moves monotonically as pages get denser,
and `sssp` disproves it (Pin 0.433, ROI-gated 0.571, wider window 0.391 — the middle
measurement is outside the range of the two ends). Mean density and any single point
of a CDF are not tied together. `docs/claims.md` has the full retraction.

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

### 4.4 Tracker results are sensitive to address-space layout

Found while chasing the Count-Min non-monotonicity, and it generalises well past this
project.

After fixing the CAM bug the curve was still not monotone, so the next question was
whether the runs were even **deterministic**. They were not: two identical invocations
gave Count-Min access-count ratios of **0.1726 and 0.1803**.

The cause is ASLR. Trackers are keyed on **page numbers**, and Count-Min *hashes* them,
so a different address-space layout produces an entirely different collision pattern.
With a single sample per budget, that run-to-run variance was being read as an
algorithmic property of the sketch. It was not.

Runs are now pinned with `setarch -R`, wired into `experiments/env.sh` and applied by
the runners. `NO_ASLR=0` disables it.

**The Figure 4 results are unaffected, and that was verified rather than assumed.**
`mean_unique_words` and `P(≤16)` measured byte-identical across four runs with ASLR on
and off:

| | ASLR on | ASLR off |
|---|---|---|
| mean unique words | 18.298 / 18.298 | 18.298 / 18.298 |
| P(≤16) | 0.7078 / 0.7078 | 0.7078 / 0.7078 |
| CM access-count ratio | 0.1803 / **0.1726** | 0.1724 / **0.1724** |

The reason is §4.3: the metric depends on within-page word offsets, which are
translation-invariant, so shifting page numbers cannot move it. The VA/PA argument
predicted this, and there is now an experiment behind it instead of only a derivation.

**The transferable lesson:** establish that a measurement is reproducible before
interpreting its shape. A curve built from one sample per point can show structure
that is entirely noise.

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
3. **Pin runs are not reproducible unless you pin the address layout.** See §4.4.
   Anything keyed on page numbers — every tracker here — varies run to run otherwise.
4. **The raw dump scales with epochs × touched pages and will fill the disk.**
   liblinear on kdda produced 984 epochs and 275M page-observations: a **45 GB** file
   that took the host from 66 GB free to 24 GB. `-dump_max_mb` (default 8 GB) now caps
   it and records `pages_bin_capped` in the summary. Set `DUMP_PAGES=0` when you only
   need the summary.
5. **`pkill -f pin` does not work.** Pin rewrites the injected process's `argv` to the
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
| `<prefix>.pages.bin` | raw records, 160 bytes each — everything else is derivable from this. Capped by `-dump_max_mb`; check `pages_bin_capped` in the summary |
| `<prefix>.topk.csv` | with `-dump_topk`: each epoch's tracker top-K, as `epoch,n,kind,rank,key`. Feeds `placement_study.py --tracker-csv` |

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

## 7. Findings

**The findings live in [`report.md`](report.md) §4–§7, and in [`claims.md`](claims.md)
as a table with the command that regenerates each number.** They are not repeated here.

That is deliberate. An earlier version of this handbook carried a full copy of the
results, and keeping two copies in sync failed: when the accuracy summary, the
Count-Min result and the window story were each revised, stale numbers survived in
whichever document was not being edited. One canonical location, plus a checker, is
worth more than two readable ones.

Quick index of where each result lives:

| finding | where |
|---|---|
| calibration against analytic ground truth | report §4.1 |
| the kernel blind spot, and its correction | report §4.2 |
| Figure 4 reproduction, scored across the whole CDF | report §5.1 |
| Redis: allocator and record layout | report §5.2 |
| liblinear disagreement | report §5.4 |
| the window is underspecified in the paper | report §5.4b |
| bounded trackers scored against ground truth | report §6.1, hardware-evaluation §1 |
| the cold-tail sizing law | report §6.2 |
| what sub-page information is worth | report §6.3, hardware-evaluation §2–2b |
| the closed-loop speedup | report §6.4 |
| granularity as a 2-D surface | report §6.5 |
| which failure mode binds | report §7, which-failure-mode.md |
| hypotheses tested and **refuted** | claims.md |
| **the gem5 port, and what it cost to build** | `src/sim/simcxl/README.md` |
| **full-system sweep, all six GAPBS kernels** | claims.md, "The full sweep contradicts…" |
| **kernel visibility isolated from window extent** | §4.2 above, claims.md |
| **counters measured at the CXL device port** | claims.md, "Measured at the CXL device port" |
| **the measurement window, measured** | claims.md, "The measurement window, measured" |
| **memcached: 0.006 against the paper's stated value** | claims.md, "memcached (new)" |
| **full-system results: `bc` 0.493→0.331, `sssp` 0.433→0.391** | claims.md, "Full-system campaign" |
| **the measurement window brackets M5** | claims.md, "The measurement window dominates" |

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
| run the gem5 full-system campaign | `src/sim/simcxl/README.md` — patches, config, build traps |
| change what the simulator measures | `fs_hotskew.py`, `--switch-at-roi`: switching CPU at boot counts the data load, switching at the ROI marker does not. The probe hooks `recvTimingReq`, and an ATOMIC CPU issues `recvAtomic`, so an ATOMIC phase is invisible to it |
| add a metric over raw data | `src/analysis/hotskew.py`, the `Run` class |
| sweep page/word granularity | `src/analysis/granularity_sweep.py` — edit `PAGE_SIZES` / `WORD_SIZES`; no re-runs needed |

### The experiments I would do next, in order

*(The first two on the original list are done: the tracker-derived placement study is
§7.5, and the Count-Min CAM is fixed in §3.3.)*

1. **Re-run liblinear on KDD2012**, the dataset M5 actually used, and compute its
   whole-run window bound. The cheapest way to turn an open disagreement into either a
   reproduction or a genuine finding.
2. **Memstrata's axis.** Intel Flat Memory Mode is mechanically a direct-mapped cache
   with 64 B lines indexed `line_addr mod L` — `assoc=1` in the existing model. Needs
   a VA→PA allocator model (which page colouring requires anyway) and two co-running
   traces. That would give all three papers' failure modes on one instrument.
4. **Real datasets.** M5 §6 names Twitter (bfs/cc/tc/pr) and Google (bc/sssp). The web
   graph is small and easy; Twitter is not.

### Things that are wrong or unfinished, honestly

- **Count-Min is fixed but still slightly non-monotone on `cc`.** Two causes were
  found and removed (stale CAM estimates, ASLR); a small residual remains on one
  workload. Usable now, but do not present the `cc` curve as clean.
- **liblinear uses the wrong dataset** — kdda rather than M5's KDD2012 (§7.2b).
- **The `hpt-driven` nominator** uses a median-split to model "pages HPT reported",
  which is a stand-in for a real bounded HPT membership test.
- **liblinear has no full-system result.** It runs fine under Pin (max error 0.577,
  in the scorecard), but three gem5 attempts produced `STATUS NO DATA`. The cause is
  measured, not guessed: parsing 2.67 GB of kdda through a simulated IDE disk is
  I/O-bound, so the ATOMIC fast-forward saves far less than the instruction count
  suggests, and the run never reaches `hotskew_roi_begin`. Needs an uninterrupted
  multi-hour stretch.
- **SPEC CPU2017 is absent** (licence), so 4 of M5's 14 Figure 4 bars are missing.
- **The three full-system runs are not one uniform experiment.** `sssp` and `bc`
  measure *through* the data load, because load visibility is the hypothesis under
  test. liblinear cannot — its load is out of reach in detail — so it would test the
  physical-address effect only. Do not average the three.
- **The window sweep has two points, not a curve.** 10M-access windows and one
  unbounded window bracket M5; the window that actually reproduces M5 is somewhere
  between and was not searched for.
- **`tc` and `pr` have no ROI-gated result.** Both are long runs (15 h and 13.5 h) and
  both were killed by a reboot mid-flight. `tc` is the one worth redoing — its wider-
  window run swung 0.355, the largest of any workload, so it is the sharpest remaining
  test. `pr` swung 0.003 and is saturated at 63/64 words; it can tell us nothing.
- **The page-fault hypothesis in §4.2 is unmeasured.** It explains all four data points
  and has an obvious cheap test, which is exactly the situation in which a plausible
  story is most likely to be believed without checking.
- **The committed script did not reproduce the committed results, for a while.**
  `run_all_gapbs.sh`'s `trials_for()` defaulted to eight trials for bfs and cc while
  the published numbers used one, contradicting §7b of methodology.md. Eight traversals
  dilute the one-time load 8x, so cc came back at 25.3 words instead of 44.8 and its
  error against M5 went 0.082 → 0.458. Fixed, and `check_claims.sh` is what caught it.
  Worth remembering as the failure mode a claims ledger exists to catch.
- **Four bugs sat between us and the window result**, all ours: the search grid stepped
  in powers of two and could not see optima at m = 3, 5, 18; the verdict tested whether
  the per-workload optima were *identical* rather than whether one window works for all;
  the `.pages.bin` inputs had been deleted in a cleanup as "regenerable"; and scoring
  used digitised bars when the paper states exact values in prose.
- **Three claims in the simulator campaign were published and then withdrawn** — see
  the git log. Each was a quantitative decomposition offered before the workload set
  was complete. The honest summary of that episode: measurements held up, explanations
  built on two or three of them did not.
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
3. Why `VA[11:0] ≡ PA[11:0]` preserves offsets, but not the modeled miss stream.
4. Why Space-Saving's required size depends on the cold tail (§7.4).
5. Why access count is a sufficient statistic for page-granular placement (§7.5).
6. Why historical migration-cost crossover numbers are withdrawn (October audit).
7. Why tracker results move with ASLR while Figure 4 does not (§4.4) — and why that
   means a curve built from one sample per point can show structure that is noise.
8. Why HPT and HWT are independent trackers, and their output-list filtering must
   not be confused with input gating (October audit).
