# 3. The Core Problem — what you're replicating

This is the file that matters. Everything else is context for this.

## Your original framing, refined

You said: *"moving pages from slow to fast isn't cutting it, we should do lines instead."*

That's a real finding and it is in the literature — but it's **one of three distinct failure modes**,
and if you present it as *the* problem the prof will (fairly) push back. Here's the honest
decomposition.

---

## Failure mode 1 — The profiling problem (resolution & timeliness)

**Claim:** The OS cannot find out which pages are hot, fast enough or accurately enough, to make
good promotion decisions.

Every software mechanism is stuck on the same tradeoff curve: accuracy × timeliness × overhead —
pick two. PTE scanning takes seconds. Hint faults measure the wrong event (TLB, not LLC). PEBS
samples too sparsely to converge before the hot set shifts.

The consequence isn't subtle. A workload whose hot set turns over every 100 ms, profiled by a
mechanism with a 1-second convergence time, is *always promoting yesterday's hot pages*. You do all
the migration work and get none of the benefit.

**This is NeoMem's thesis.** Their argument is that granularity is a secondary issue — fix profiling
and 4 KB pages are fine.

## Failure mode 2 — The granularity problem (your instinct)

**Claim:** The 4 KB page is the wrong unit, in *both* directions.

**Too coarse for what's actually hot.** Access density within a page is wildly non-uniform. A hash
table probe touches 64 bytes of a 4 KB page. Promoting that page moves 4032 bytes of cold data you
didn't need, consuming migration bandwidth and burning a fast-tier frame that some genuinely hot
page could have used. M5 quantifies this by tracking every **64 B word**, and it's why they built the
Hot *Word* Tracker alongside the Hot *Page* Tracker.

**But also: too fine for the migration mechanism.** Per-page migration means per-page TLB shootdowns
and rmap walks. That's why people reach for 2 MB huge pages — amortize the fixed cost — which makes
the internal-fragmentation problem *dramatically worse*. A 2 MB page promoted for one hot cache line
wastes 99.997% of the transfer.

So you're squeezed from both ends:

```
   fine granularity  ────────────────────►  coarse granularity
   64 B                  4 KB                      2 MB
   ├─ low waste          ├─ Linux default          ├─ cheap to migrate
   └─ metadata blows up  └─ mediocre at both       └─ enormous waste
      TLB can't map it
```

**The catch — and this is the point to be precise about with the prof:** you cannot simply "migrate
64 B lines instead of pages" in a conventional OS. The page table's minimum mapping unit is 4 KB.
There is no PTE for a cache line. Sub-page migration therefore requires *either*:

- **hardware indirection** — the memory controller maintains a line-granular remap table, i.e. treat
  local DRAM as a **cache** rather than as addressable memory (→ Intel Flat Memory Mode, Memstrata);
  or
- **hardware profiling at line granularity + page-granular migration decisions** — use the fine data
  to make *better* coarse choices, which is exactly what M5's HWT does; or
- **a compaction/packing layer** that gathers hot lines from many cold pages into one dense hot page.

That distinction — *profiling granularity* vs *migration granularity* — is the single most useful
thing to be crisp about. M5 profiles at 64 B and migrates at 4 KB. That is not a compromise, it's
the design.

## Failure mode 3 — The interference problem (multi-tenant)

**Claim:** Even if tiering works perfectly for one workload, it breaks under co-location.

When hardware manages the tier as a direct-mapped cache (Flat Memory Mode), two VMs whose pages map
to the same set thrash each other. One VM's behavior silently degrades another's — unacceptable in
a cloud, where you sell a performance SLA. And the degradation is invisible to both tenants.

**This is Memstrata's thesis**, and it's the one nobody expects. Their fix — page coloring so VMs
can't collide, plus an online slowdown estimator to hand extra local DRAM to the tiering-sensitive
VMs — is a pure software allocator sitting on top of hardware tiering.

---

## Is cacheline granularity actually the answer?

Honest position, and a good slide:

| | Page migration (OS) | Line caching (HW) |
|---|---|---|
| Unit | 4 KB / 2 MB | 64 B |
| Who decides | OS, with stale info | HW, reactively |
| Wasted transfer | High (internal fragmentation) | ~None |
| Fixed cost per move | µs (TLB shootdown, rmap) | ns |
| Metadata | Page tables (free, existing) | Tag array — huge |
| Capacity efficiency | 100% (both tiers usable) | Fast tier is a *cache*, capacity not additive |
| Conflict misses | N/A | **Yes — and across tenants** |
| Needs new HW | No | Yes |

Line granularity eliminates waste and fixed cost, and buys you conflict misses, tag storage, and
the loss of fast-tier capacity as usable memory. It is a genuine tradeoff, not a strict win. The
field has not converged — that's *why* there are three papers with three different answers.

---

## The experiment that demonstrates all of this

This is your replication target. Build it first, before writing any policy code.

**Setup:** CXLRAMSim, local DDR + CXL zNUMA node, fast:slow capacity ratio 1:2 or 1:4.

**Workloads** (pick 2–3; steal from the papers):
- **GUPS** — random 8 B updates over a huge array. Zero spatial locality. The adversarial case:
  page migration should be near-useless here, and this is where a line-granular scheme should shine.
  NeoMem got 4.7× on it. **Start here — it's the cleanest demonstration.**
- **XSBench** — Monte Carlo particle transport, large random lookups into cross-section tables.
- **BFS / PageRank** on a large graph — irregular, pointer-chasing, hot set shifts per iteration.
- **Btree / Silo (YCSB-C)** — skewed (Zipfian) index lookups. Sub-page hotness is extreme here:
  a few hot nodes scattered across many pages.

**Measurements that make the point:**

1. **Access-density CDF.** For each 4 KB page, histogram accesses per 64 B line. Plot the fraction of
   a page's accesses concentrated in its top-k lines. If 80% of accesses hit <10% of the page,
   you have proven the granularity argument in one figure. **This is your money slide.**
2. **Migration efficiency.** Bytes migrated ÷ bytes subsequently accessed before demotion. Page
   migration will look terrible.
3. **Promotion timeliness.** Time between a page becoming hot and being promoted, per mechanism.
   Then: fraction of promoted pages still hot at promotion time. Proves failure mode 1.
4. **Slowdown vs. all-local DRAM**, as fast-tier ratio varies (100%, 50%, 25%, 12.5%).
5. **Ping-pong count** — promotions followed by demotion within N ms.
6. Then, with two co-running workloads: per-workload slowdown vs. running alone. Proves failure
   mode 3.

**Expected result / the story:** naive page-granular tiering recovers only a fraction of the gap to
all-local DRAM; the profiling is late, the migrated bytes are mostly cold, and the fast tier fills
with pages that are 1% useful. Measurement 1 tells you exactly how much of that is granularity.

---

## Recommendation on which paper to implement

You said implementing one is optional. If you do:

**M5** is the best fit for you. It aligns with the intuition you already have (sub-page tracking),
its HWT/HPT are relatively simple hardware structures (top-K trackers, borrowed from Rowhammer
defenses — misc-style counter tables, not exotic), and the profiling→decision split is clean to
implement in a simulator. You can also implement HPT alone first and get a working result, then add
HWT as the differentiator.

**NeoMem** is a close second — the count-min sketch is genuinely easy to code (a few hash functions
and a 2D counter array) and the paper is unusually explicit about parameters (W=512K, D=2, 16-bit
counters, 16K-entry hot page buffer). Downside: the interesting part is then the *kernel* daemon and
dynamic threshold algorithm, which is more OS work than hardware work — and you said you want to be
on the hardware side.

**Memstrata** is the weakest fit: the contribution is a userspace/hypervisor allocator, and its
premise (Intel Flat Memory Mode) is a hardware tiering mode CXLRAMSim doesn't model. You'd have to
build the HW tiering first *and then* the software on top. Only pick this if the multi-tenant angle
excites you specifically.

→ Full per-paper notes in [04](04-paper-memstrata.md), [05](05-paper-m5.md), [06](06-paper-neomem.md).
