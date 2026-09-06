# Which failure mode actually binds?

M5, NeoMem and Memstrata all attack CXL memory tiering, and they disagree about
*why* it underperforms:

| paper | claim | fix |
|---|---|---|
| **M5** (ASPLOS'25) | **granularity** — a 4 KB page is the wrong unit; accesses concentrate in a few 64 B words | profile at 64 B, migrate at 4 KB |
| **NeoMem** (MICRO'24) | **timeliness** — profiling is too slow, so the OS promotes yesterday's hot pages | put the profiler in the CXL controller |
| **Memstrata** (OSDI'24) | **interference** — hardware tiering collapses under co-location | page colouring + a slowdown estimator |

Picking one to implement means deciding which claim is true *for the workloads you
care about*. That question is usually settled by argument. It does not have to be:
the same instrument that answers M5's question answers NeoMem's, from the same data.

This document reports that comparison. **It is the part of this project that is not a
reproduction.**

---

## The two measurements

Both come from `.pages.bin`, which records per-page access counts *per epoch*.

**Granularity (M5's axis)** — how much of a page is actually hot. Measured as
`P(page has ≤ N of 64 words touched)`; that is Figure 4, reported in
[methodology §7](methodology.md#7-results-against-the-paper).

**Timeliness (NeoMem's axis)** — how much a promoter loses by acting on
one-epoch-old information. Three quantities, over the top-$K$ hottest pages:

```
concentration = share of epoch t's accesses landing in epoch t's OWN top-K
                the oracle bound: perfect, instantaneous information

coverage      = share of epoch t's accesses landing in epoch (t-1)'s top-K
                a perfectly-executed but one-epoch-late promoter

staleness     = coverage / concentration
                the cost of lag alone, with the workload's concentration
                divided out. 1.0 = being a step behind is free.
```

Separating concentration from staleness is the point. A low coverage can mean the hot
set churned (a timeliness problem) *or* that no small set of pages carries much
traffic (a problem no tiering system can fix). Only the first argues for faster
profiling. `src/analysis/hotset_turnover.py` computes all three.

---

## Result

GAPBS, kron-23, 36 MB LLC, 10M-DRAM-access epochs, ROI-bounded (kernel only, so the
graph-load phase does not contaminate the epoch-to-epoch comparison).

### $K$ = 10,000 pages (40 MB fast tier)

| kernel | retention | concentration | coverage | staleness |
|---|---|---|---|---|
| bc | 0.749 | 0.355 | 0.334 | 0.940 |
| bfs | 0.750 | 0.520 | 0.470 | 0.904 |
| cc | 0.822 | 0.544 | 0.527 | 0.968 |
| pr | 0.819 | 0.401 | 0.377 | 0.941 |
| sssp | 0.831 | 0.425 | 0.405 | 0.952 |
| tc | 0.717 | 0.434 | 0.387 | 0.892 |

At this size lag is nearly free — staleness 0.89–0.97. But concentration is only
0.36–0.54: a *perfect* promoter with 40 MB of fast tier captures under half the
traffic. The binding constraint here is capacity, not information.

### $K$ = 128,000 pages (512 MB fast tier, ≈ half the footprint)

This is the size that matters — M5 caps DDR so *"roughly 50% of the pages can be
migrated"*, and sets $K$ up to 128K pages.

| kernel | retention | concentration | coverage | **staleness** |
|---|---|---|---|---|
| tc | 0.933 | 1.000 | 0.902 | **0.902** |
| bc | 0.582 | 0.983 | 0.835 | **0.850** |
| bfs | 0.960 | 0.975 | 0.819 | **0.841** |
| cc | 0.711 | 0.968 | 0.804 | **0.830** |
| sssp | 0.304 | 0.921 | 0.554 | **0.602** |
| pr | 0.086 | 1.000 | 0.381 | **0.381** |

Concentration is now ~1.0 — with half the footprint in fast memory an oracle catches
essentially everything. So every point below 1.0 in the staleness column is a loss
attributable **purely to acting one epoch late**.

**That loss is large and workload-dependent: 10% for triangle counting, 62% for
PageRank.**

---

## What this implies

Put the two axes together, for GAPBS:

| | granularity (M5) | timeliness (NeoMem) |
|---|---|---|
| what we measure | top-10k hottest pages are **dense** (P(≤16 words) = 0.000 for every kernel) | staleness 0.38–0.90 at a realistic fast-tier size |
| what it means | a count-only policy already picks dense pages; **HWT has almost nothing to correct** | **being one epoch late costs 10–62% of the achievable benefit** |

**For graph analytics, timeliness binds and granularity does not.** That is NeoMem's
thesis, not M5's — and it is the opposite of the recommendation this project started
with.

M5 is not wrong; their own Figure 4 puts the graph kernels at the dense end and
reserves the sparsity claim for *"certain applications"* — Redis 86%, Memcached 76%,
CacheLib 74%. The point is that the claim is workload-specific in a way that decides
what is worth building, and now it is measured rather than assumed.

**The practical consequence:** if the simulator work targets GAPBS, implement HPT and
spend the effort on making it *fast*, not on HWT. If it targets Redis, HWT is where
the value is. Running this same analysis on Redis is the obvious next step.

---

## Caveats, stated plainly

1. **An epoch is a fixed number of DRAM accesses, not a fixed amount of time.** Real
   promotion latency is in milliseconds. These numbers say how stale information gets
   per unit of memory traffic; converting to "is a 1-second profiler fast enough"
   needs the miss rate. The *ordering* across kernels is robust; the absolute
   staleness is tied to the epoch length.

2. **`retention` is unreliable when access counts are near-ties.** PageRank sweeps
   every edge every iteration, so beyond a small core, most pages have nearly
   identical counts and which ones land in the top-$K$ is close to arbitrary — hence
   retention 0.086 at $K$=128K while concentration is 1.000. Swapping two equally-hot
   pages costs nothing, and `staleness` correctly reflects that where `retention` does
   not. Read the staleness column, not the retention column.

3. **One epoch of lag is optimistic.** A real system profiles, decides, then migrates;
   AutoNUMA and DAMON operate on timescales far longer than one of these epochs. These
   numbers are an upper bound on what a late promoter achieves.

4. **Single workload, single thread.** The interference axis (Memstrata's thesis) is
   not measured at all. Doing so needs two co-running workloads and a direct-mapped
   fast-tier model — see [next-steps.md](next-steps.md).
