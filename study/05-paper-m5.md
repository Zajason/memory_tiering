# 5. M5 — "Mastering Page Migration and Memory Management for CXL-based Tiered Memory Systems"

**Venue:** ASPLOS 2025 · **Authors:** Sun, Kim, Yu, Zhang, Chai, Kim, Nam, Park, Na, Yuan, Wang, Ahn,
Xu, Kim (UIUC / SNU / Intel)
**PDF:** https://jiyuan.is/papers/asplos25-m5.pdf · **Artifact:** https://github.com/ece-fast-lab/ASPLOS-2025-M5

> **This is the paper closest to your instinct, and my recommendation to implement.**

## One-line summary

Put profiling hardware *in the CXL device* that counts accesses to every 4 KB page **and every 64 B
word**, then use that sub-page information to make page-migration decisions that are actually right.

## The premise

CXL DRAM is 2–3× slower than DDR, so a tiered system needs page migration — but the existing
solutions (AutoNUMA Balancing, DAMON) pick the wrong pages, because their profiling is coarse,
slow, and measures the wrong event. M5's answer is to profile transparently at the device, at
line resolution, with bounded hardware cost.

## The two trackers

Both are **top-K trackers inspired by hardware Rowhammer defenses** — this is the clever move.
Rowhammer mitigation has the identical problem: identify the few most-frequently-accessed rows out
of an enormous space, in hardware, with a small fixed budget of counters. So M5 reuses that
structure (Misra–Gries / frequent-elements style counter tables) rather than inventing something.

- **HPT — Hot Page Tracker.** Top-K over 4 KB pages. Tells you *which page* to migrate.
- **HWT — Hot Word Tracker.** Top-K over 64 B words. Tells you *how much of that page is actually
  worth migrating*, i.e. how dense its hotness is.

**The key design point:** M5 *profiles* at 64 B but still *migrates* at 4 KB. It does not try to
move cache lines through the OS — as noted in [03](03-the-core-problem.md), it can't; there's no PTE
for a line. Instead the fine-grained data makes the coarse decision smarter: a page with 500
accesses concentrated in 2 hot words is a far worse migration candidate than a page with 500
accesses spread over 40 words, because the second one will actually keep paying off after you move
it. Access *count* alone cannot distinguish those two. That's the whole insight.

Make sure you can articulate that distinction — it's the strongest single idea to present, and it
directly sharpens your original "lines not pages" framing into something defensible.

## M5-manager

The software half: interfaces that let the OS/runtime read HPT and HWT and drive migration policy
synergistically, plus the memory-management glue. Less interesting for a hardware-focused project,
but you need a minimal version of it to close the loop.

## Results

- Identifies **47% hotter pages** than the baselines (i.e. the pages it picks receive 47% more
  accesses — a direct measure of decision quality, not just end-to-end speedup).
- **20% higher performance than AutoNUMA Balancing**, **14% higher than DAMON**, on memory-intensive
  applications.

Note these numbers are more modest than NeoMem's headline speedups — different baselines, different
platform, and M5 is measuring against a reasonably-tuned system. Don't compare the two papers'
percentages directly; it's not apples to apples.

## Implementation sketch for CXLRAMSim

This is the concrete plan if you pick M5.

**Phase 1 — observability (do this regardless of which paper you pick).**
Hook the CXL device's request path in the simulator. Every incoming M2S request gives you a physical
address and a type (read/write). Log or aggregate. Produce the access-density CDF from
[03](03-the-core-problem.md#the-experiment-that-demonstrates-all-of-this). This alone is a
presentable result and it de-risks everything after.

**Phase 2 — HPT.** A top-K counter table keyed on `paddr >> 12`. Misra–Gries: on a hit increment; on
a miss, if there's a free entry take it, else decrement the minimum entry (or evict it if it hits
zero). Fixed number of entries — that's the point, it's bounded hardware. Expose a "read top-K"
operation.

**Phase 3 — HWT.** Same structure keyed on `paddr >> 6`, but only for addresses within pages that
HPT already flagged as hot — that keeps the HWT small and is likely what the paper does. Now you can
compute, per hot page, a **hotness density**: how many distinct hot words and what fraction of the
page's accesses they carry.

**Phase 4 — policy + migration.** A promotion decision that combines page access count with word-level
density, versus a baseline that uses count only. Model the migration cost honestly (copy bandwidth on
both tiers, a fixed TLB-shootdown penalty, quota per interval). Compare:
- no tiering (all CXL)
- all local DRAM (upper bound)
- count-only page migration (the naive baseline — this is the "problem" arm)
- M5-style density-aware migration
- ideal/oracle (offline-optimal placement, computed from a full trace)

The gap between the naive arm and the oracle is the problem you're replicating. The fraction of that
gap M5 closes is your result.

**Phase 5 (stretch) — hardware cost.** Counter table sizing, area/energy estimate, sensitivity to K.
Reviewers and profs always ask "what does it cost?" and it's cheap to answer.

## Questions to be ready for

- Why top-K rather than a count-min sketch (NeoMem's choice)? (Top-K gives you exact identities of
  the heavy hitters with no false positives from hash collisions; sketches are smaller and give
  approximate counts for *all* pages. Different points on the same accuracy/space curve.)
- Why not just use huge pages? (Makes internal fragmentation catastrophically worse — exactly what
  HWT exists to detect.)
- If you profile at 64 B, why not migrate at 64 B? (Page table granularity. See above. This is *the*
  question you will be asked.)
