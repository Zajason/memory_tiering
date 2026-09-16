# Evaluating M5's hardware without M5's hardware

Deliverables 1 and 2: implement the trackers M5 proposes, score them against exact
ground truth, and measure what the sub-page information they produce is actually worth.

Reproducing an observation shows the phenomenon is real. Evaluating the *mechanism*
is a different and harder thing, and it is normally what the FPGA was for. It turns
out not to need one.

---

## 1. HPT and HWT, scored against exact counts (M5 Figure 8)

### Why this is possible at all

PAC and WAC keep an exact count for every page and every 64 B word. That is fine
offline but unbuildable in a controller — 256 GB of CXL memory at 4 KB granularity is
64M counters. M5's answer is a **bounded top-K tracker**: a fixed entry budget that
approximates "which addresses are hottest".

The question their Figure 8 asks is how close the approximation gets per unit of
hardware. Answering it needs the exact counts *and* the bounded tracker, over the same
stream, in the same window. We have both: the trackers run inside the pintool next to
the counters, so every profiling run scores the approximation for free.

Space-Saving's output depends on the *order* accesses arrive in, which is why this
cannot be done offline from `.pages.bin` — the aggregated counts have thrown the order
away. Hence `tracker.hpp` rather than a Python script.

### The metric

M5's *average access-count ratio*:

$$\frac{\sum \text{exact counts of the } K \text{ pages the tracker picked}}{\sum \text{exact counts of the true top-} K}$$

1.0 means the tracker chose a set as hot as the best possible set. It is fairer than
set overlap, because picking a *different* page with the same access count costs
nothing in practice — and that distinction turns out to matter enormously (below).

### Results

GAPBS, kron-23 (kron-21 for `tc`), 36 MB LLC, 10M-access epochs, K=128.
Storage assumes a 36-bit tag (48-bit PA, 4 KB pages) plus a 32-bit counter per entry.

**Space-Saving:**

| workload | N=50 | N=128 | N=512 | N=2048 | N=8192 |
|---|---|---|---|---|---|
| bfs | 0.283 | **0.737** | 0.755 | 0.760 | 0.757 |
| cc | 0.250 | **0.654** | 0.679 | 0.634 | 0.600 |
| tc | 0.139 | 0.358 | 0.421 | 0.431 | 0.451 |
| storage | 0.4 KB | **1 KB** | 4 KB | 17 KB | 68 KB |

**The curve has a knee at N=128 and then flattens.** A 1 KB HPT captures ~74% of the
ideal access count for BFS; sixty-eight times the storage adds nothing, and for `cc`
it is slightly *worse*. If that holds up, it is a directly actionable sizing result:
the tracker should be small.

**Count-Min Sketch.** An earlier version of this table was non-monotone in $N$ and was
reported as a suspect implementation. Two causes were found, and the second one is the
more important lesson.

*Cause 1 — a real bug.* CAM entries cached their estimate at the moment their key was
last accessed, and a fresh candidate was compared against those stale values. Numbers
sampled at different times are not comparable, so an early entry could squat while
hotter keys were rejected against it. Fixed: estimates are now re-read from the sketch
before any comparison, and unconditionally before reporting top-K.

*Cause 2 — the measurement, not the code.* The fix did not restore monotonicity, so we
checked whether the runs were even deterministic. **They were not.** Two identical
invocations gave CM ratios of 0.1726 and 0.1803. Trackers key on page *numbers*, and
CM-Sketch hashes them, so **ASLR changes the entire collision pattern between runs.**
With a single sample per budget, that variance was being read as an algorithmic
property. Pinning the layout (`setarch -R`, now the default in `experiments/env.sh`)
makes tracker runs reproducible.

With both corrections, at 10M-access epochs, $K=128$:

| workload | N=50 | N=128 | N=512 | N=2048 | N=8192 | monotone |
|---|---|---|---|---|---|---|
| bfs | 0.129 | 0.110 | 0.170 | 0.256 | 0.302 | yes |
| tc | 0.298 | 0.299 | 0.326 | 0.357 | 0.408 | yes |
| cc | 0.431 | 0.327 | 0.368 | 0.425 | 0.521 | not quite |

The curves now rise with $N$, as they should. **Space-Saving substantially outperforms
CM-Sketch at equal budget** on these workloads — 0.767 against 0.302 for BFS at
N=8192 — which is consistent with M5 choosing to compare the two rather than adopting
the sketch outright.

*What did not change:* the Figure 4 results are ASLR-invariant, and measured so.
`mean_unique_words` and `P(≤16)` were byte-identical across four runs with ASLR on and
off, because the metric depends on within-page word offsets, which are
translation-invariant (methodology §2). The reproduction in §5 of the report is
unaffected; only tracker evaluation needed pinning.

### Recall is ~0 while the ratio is 0.75 — and that vindicates M5's metric choice

Across the Space-Saving runs, set overlap with the true top-K is near zero even where
the access-count ratio is 0.75. The tracker is picking pages that are *as hot* but not
the *same* pages, because in these workloads many pages have near-identical counts.

That is exactly why M5 reports an access-count ratio rather than precision/recall, and
it is the same near-tie effect that makes `retention` misleading in
[which-failure-mode.md](which-failure-mode.md).

### A sizing law that falls out of the self-test

`src/sim/standalone_driver.cpp --self-test` asserts a threshold that is worth stating
on its own:

> **The tracker size an HPT needs is set by the length of the cold tail, not the size
> of the hot set.**

Space-Saving gives an evicted slot the count `min+1`, so a long cold tail inflates
every cold entry to roughly `n_cold / N`. The hot set survives only while that stays
below the hot pages' own count:

$$N > n_\text{hot} + \frac{n_\text{cold}}{\text{hits per hot page}}$$

With 64 hot pages at 400 hits each and a 100,000-page tail the threshold is N > 314 —
and measured, 256 entries loses the hot set completely (ratio 0.002) while 512 recovers
it exactly (1.000). A 2× hardware change either side of a boundary that has nothing to
do with how many pages are hot.

This began as a wrong assertion in the test ("N bigger than the hot set must be
exact"), which failed. The failure was the interesting part.

---

## 2. What the sub-page information is worth

### The policies

`src/analysis/placement_study.py` implements **M5's two actual nominators** (§5.2),
which are *candidate-generation paths*, not reweightings:

| policy | how it selects |
|---|---|
| **oracle** | the pages with most accesses in the epoch being served — needs the future, bounds everything else |
| **count-only** | previous epoch's access count. HPT alone; what AutoNUMA/DAMON approximate |
| **HPT-driven** | HPT supplies candidates, then the 64-bit hot-word mask ranks them — prefer pages with more hot words. *M5 Guideline 3: "a mix of dense and sparse hot pages"* |
| **HWT-driven** | start from an empty page list, derive pages from hot *word* addresses alone; mask population "serves as an access count". *M5 Guideline 4: "only sparse hot pages, such as Redis and Cachelib"* |

> **A correction worth recording.** The first version of this study scored a
> "density-aware" policy as `count × (unique_words/64)`. That is not what M5 does and
> is close to a strawman — with a page-granular fast tier every page costs 4096 bytes
> regardless of density, so any monotone reweighting of a count ranking can only lose
> hit rate. The result happened to be the same, but the reasoning was wrong, and a
> right answer from a wrong model is not evidence.

### Results — fast tier = 50% of the touched footprint (M5's cap)

Share of an epoch's accesses served from the fast tier:

| workload | oracle | count-only | HPT-driven | HWT-driven | best gain |
|---|---|---|---|---|---|
| bc | 0.919 | **0.829** | 0.757 | 0.813 | −0.016 |
| bfs | 0.839 | **0.736** | 0.619 | 0.675 | −0.062 |
| cc | 0.858 | **0.795** | 0.702 | 0.713 | −0.082 |
| pr | 0.671 | **0.655** | 0.510 | 0.654 | −0.001 |
| sssp | 0.878 | 0.704 | **0.724** | 0.711 | +0.020 |
| tc | 0.728 | **0.664** | 0.600 | 0.610 | −0.054 |
| redis (YCSB-A) | 0.909 | **0.810** | 0.805 | 0.778 | −0.005 |

**Neither nominator beats ranking by access count — including on Redis, which is
M5's own Guideline 4 case.**

### Why, structurally

With a **capacity-limited, page-granular** fast tier, a page costs 4096 bytes whether 2
or 64 of its words are hot. The benefit of promoting it is its access count. So access
count is a *sufficient statistic* for the selection problem, and any policy that
discards it (HWT-driven) or overrides it (HPT-driven) can only do worse.

That is a claim about the regime, not about M5. HWT's value has to come from somewhere
this experiment does not reach:

1. **Bounded HPT counts.** Our count-only baseline uses *exact* counts. M5's HPT is a
   bounded tracker whose counts are approximate — and §1 above shows how approximate
   (ratio ~0.75, recall ~0). The honest next experiment is to re-run this study using
   tracker-derived scores instead of exact ones. That is the regime where a second,
   independent signal should help most, and it is the obvious follow-up.
2. **Migration bandwidth**, rather than capacity, as the binding constraint.
3. **Sub-page migration or compaction** — gathering hot lines from many sparse pages
   into one dense page. M5 explicitly does *not* do this (they migrate at 4 KB), so
   the waste their own figure identifies is measured but not recovered.

### 2b. The fair test: scoring from a bounded tracker

The objection to §2 was that count-only was handed *exact* counts while a real HPT is
only ~0.75 accurate, and that M5's nominators exist precisely to cover that
deficiency. `-dump_topk` now writes each epoch's tracker top-K, and
`placement_study.py --tracker-csv` scores policies from it instead.

Fast tier at 4% of the touched footprint, so that capacity stays below the tracker's
$K{=}10{,}000$ — a tracker reporting $K$ pages cannot fill a tier larger than $K$, and
ignoring that turns the comparison into a measurement of what the tracker never said.
BFS / CC on kron-23, 23 and 28 epochs:

| score source | oracle | count-only | HPT-driven | HWT-driven | best gain |
|---|---|---|---|---|---|
| exact counts | 0.185 / 0.168 | **0.114 / 0.121** | 0.094 / 0.120 | 0.099 / 0.120 | −0.015 / −0.001 |
| HPT, N=262144 | " | **0.110 / 0.121** | 0.044 / 0.077 | 0.059 / 0.114 | −0.051 / −0.007 |
| HPT, N=16384 | " | **0.092 / 0.111** | 0.036 / 0.039 | 0.043 / 0.084 | −0.049 / −0.026 |
| HPT, N=1024 | " | **0.031 / 0.041** | 0.025 / 0.026 | 0.026 / 0.030 | −0.005 / −0.010 |

Degrading the tracker degrades count-only substantially (BFS 0.114 → 0.031), which is
the expected direction. **But the nominators degrade with it and never overtake.**

The reason is structural and, in hindsight, obvious: **HWT is gated on HPT
membership** — a word address is only tracked if its page is currently in the HPT. The
word signal is therefore *downstream* of the page signal, not independent of it. A
weak HPT produces a weak HWT, so sub-page information cannot compensate for the
deficiency it was hypothesised to cover.

This closes the loophole in §2 rather than opening one. The null result now holds both
with perfect information and with realistically degraded information.

### The waste is real, even though re-ranking does not fix it

Fraction of every migrated 4 KB page that is never touched, under count-only selection:

| workload | wasted |
|---|---|
| **redis (YCSB-A)** | **81%** |
| sssp | 56% |
| bc | 48% |
| tc | 40% |
| bfs | 36% |
| cc | 29% |
| pr | 3% |

Redis moves 4096 bytes to service about 780. That is precisely the pathology M5's
Figure 4 documents, and it is large. The finding here is narrower than "sub-page
tracking is pointless": it is that **knowing which pages are sparse does not help if
your only lever is which whole page to move.**

---

## Caveats

1. **Open-loop.** These traces were recorded without migration. Migrating a page
   changes its latency, not its address, so the stream stays valid and placement
   quality is meaningful — but these are not runtime numbers. A speedup needs timing
   simulation.
2. **Exact-count baseline.** As above, this gives count-only an advantage M5's HPT
   would not have. The comparison is fair as a statement about the *information*, not
   about the *implementations*.
3. **CM-Sketch numbers are suspect.** Stated in §1; do not quote them.
4. **One fast-tier size.** 50% of footprint, matching M5's DDR cap. The ordering could
   change at much smaller fast tiers, where selection pressure is higher.
5. **Synthetic graphs.** kron, not the Twitter/Google inputs M5 names in §6.
