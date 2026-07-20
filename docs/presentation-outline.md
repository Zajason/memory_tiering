# Concept Presentation — outline

**Audience:** the professors. **Purpose:** show you understand the problem and have a credible plan.
**Not** a results talk — you have no results yet, and pretending otherwise is the main failure mode.

Target: **12–14 slides, ~15 minutes**, leaving room for questions (which is where you'll actually be
assessed).

---

## Structure

### 1. Title
Project 2 — Memory Tiering for CXL Systems. Your name, course, date. Simulator: CXLRAMSim.

### 2. Motivation — why anyone cares
Memory is the constrained resource in modern servers. DRAM is expensive, capacity per socket is
capped, and cloud fleets *strand* ~25% of their DRAM behind sold-out CPUs. CXL lets you add capacity
over the PCIe bus.
> One number: ~25% stranded DRAM in Azure's fleet.

### 3. What CXL memory actually costs you
The latency table from [study/01](../study/01-cxl-basics.md): local DDR ~80–100 ns, CXL ~250–400 ns.
Diagram of the request path (core → LLC → root complex → M2S → link → device → DRAM → back).
**Point:** the DRAM on the card is normal DDR5. The interconnect is the tax. Hence *tiering* — not
all data deserves fast memory.

### 4. The tiering problem, stated
Two tiers, fast/small and slow/large. Keep hot data in fast. Promotion vs demotion. Demotion is
easy; **promotion is the open problem** — and that's the Linux community's own position, not just
mine.

### 5. Why it doesn't work today — profiling
The four-mechanism table from [study/02](../study/02-memory-tiering-fundamentals.md): PTE-scan,
hint faults, PEBS, device-side hardware. One fatal flaw each.
> Killer detail: AutoNUMA/TPP measure **TLB misses**, but CXL traffic is driven by **LLC misses**.
> They're weakly correlated. You're optimizing the wrong signal.

### 6. Why it doesn't work today — granularity
**Your central slide.** Access density within a 4 KB page is wildly non-uniform. Migrating a page
for a few hot cache lines wastes bandwidth and burns a fast-tier frame.
Show the squeeze diagram: 64 B (low waste, unmanageable metadata) ↔ 4 KB (mediocre at both) ↔ 2 MB
(cheap to migrate, enormous waste).
**Be precise:** you cannot migrate 64 B through the OS — there's no PTE for a cache line. The fix is
either hardware indirection or fine-grained *profiling* driving coarse-grained *migration*.

### 7. Why it doesn't work today — cost of migration
The four costs: copy bandwidth, rmap walk, **TLB shootdown (usually dominant)**, lock contention.
Order microseconds vs the ~250 ns you're avoiding. A promoted page must be re-accessed many times to
break even — which is why a *wrong* promotion is actively harmful, not merely useless.

### 8. Three papers, three diagnoses
One slide, three rows. This is where you show you read all three rather than one.

| Paper | Diagnosis | Fix | Granularity |
|---|---|---|---|
| **NeoMem** (MICRO'24) | Profiling is too slow/coarse | Count-min sketch in CXL controller + adaptive threshold | 4 KB |
| **M5** (ASPLOS'25) | Hotness is sub-page; page counts mislead | Top-K trackers for pages **and 64 B words** | profile 64 B, migrate 4 KB |
| **Memstrata** (OSDI'24) | HW tiering works but tenants collide | Page coloring + slowdown estimator | 64 B (hardware) |

**They disagree**, and saying so is a strength: NeoMem says resolution-in-*time*, M5 says
resolution-in-*space*, Memstrata says the problem only shows up under co-location.

### 9. The honest tradeoff
The page-vs-line table from [study/03](../study/03-the-core-problem.md#is-cacheline-granularity-actually-the-answer).
Line granularity kills wasted transfer and fixed cost — and buys conflict misses, tag storage, and
loss of fast-tier capacity as addressable memory. **Not a strict win.** That's why the field hasn't
converged.
> This slide is what separates "I read a paper" from "I understand the problem." Do not cut it.

### 10. My plan — the tool
CXLRAMSim: gem5 v25, full-system, Linux 6.14, CXL device on the I/O bus at the correct position,
unmodified kernel and drivers. CXL.mem M2S/S2M modelled. Configurable tier ratio and latency.
Show where your code hooks in: **a tap on the device-side request stream** = exactly the LLC-miss
stream the papers profile.

### 11. My plan — the experiment
The five comparison arms: all-CXL / all-local (upper bound) / naive page migration / paper's scheme /
oracle. The gap between naive and oracle *is* the problem being replicated.
Workloads: GUPS (adversarial, zero locality), XSBench, PageRank, Btree/YCSB (Zipfian, extreme
sub-page skew).
Metrics: access-density CDF, migration efficiency (bytes moved ÷ bytes then used), promotion
timeliness, slowdown vs fast-tier ratio, ping-pong count.

### 12. The figure I'm going to produce
Sketch (hand-drawn is fine — it signals honesty about not having run it yet) the **access-density
CDF**: fraction of a page's accesses in its top-k 64 B lines. If 80% of accesses hit <10% of the
page, the granularity argument is proven in one plot. Say plainly: *this is the figure the whole
project turns on.*

### 13. Scope and timeline
Phased, with the risk called out:
- P1 boot + checkpoint + latency microbenchmark ("prove CXL is slow")
- P2 access tap + density CDF ← **first real result, de-risks everything**
- P3 naive migration baseline + cost model
- P4 M5 HPT, then HWT
- P5 evaluation + writeup
State the stretch goals separately (hardware cost model, latency sweep, multi-tenant).

### 14. Open questions for you
Ask the professors directly — it's a strength, not a weakness:
- CXLRAMSim repo access and build instructions?
- Is scaling workloads down (hundreds of MB instead of 10–20 GB RSS) acceptable, holding the tier
  *ratio* realistic?
- Is implementing HPT+HWT profiling and a modeled migration engine sufficient scope, or do you want
  real Linux migration driven from a kernel module?
- Is M5 the right pick, or would you rather see NeoMem?

---

## Delivery notes

- **Don't oversell.** You have no results. The talk sells *diagnosis + plan*. Profs respond well to
  a student who states clearly what they haven't done yet.
- **Lead with the tradeoff, not the solution.** The single most impressive thing you can do is
  explain why "just use cache lines" isn't obviously right.
- **Have the granularity answer rehearsed.** You *will* be asked "why not just migrate cache lines
  then?" Answer: no PTE for a line → needs hardware indirection → that's Flat Memory Mode → which
  costs conflict misses, tag storage, and 1:1 capacity → which is what Memstrata then has to fix.
  That chain is your best 30 seconds.
- **Know your numbers cold:** 2–3× latency, ~250–400 ns, 4 KB vs 64 B, seconds (PTE-scan) vs 10 ms
  (NeoMem interval), µs per migration.
- Slides: dark background, minimal text, one idea per slide. Diagrams over bullets for slides 3, 6,
  10.

When you're ready to build the deck, the `pptx` skill can generate it from this outline.
Put figures and diagrams in `docs/assets/`.
