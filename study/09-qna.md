# 9. Q&A Prep — questions the profs might ask

Rehearse from this. It covers two things they'll probe: **(1) did you read and
understand the three papers**, and **(2) do you understand the material and what
you're going to build**.

Format: **Q** → answer. `►` marks a likely follow-up. ★ marks a
high-probability / high-value question — know these cold. Numbers you should be
able to say without hesitating are in **bold**.

A note on tactics: if you don't know something, say "I'm not certain, but my
understanding is…" and reason from first principles. Never bluff a number.
Bridging back to what you *do* know ("what I can say for sure is…") is better
than a confident wrong answer — the profs are testing judgement, not memory.

---

## Part A — Fundamentals (CXL & tiering)

**★ What is CXL and why do we care?**
Compute Express Link — a cache-coherent interconnect that rides on the PCIe
physical layer. The part we use is **CXL.mem**: the CPU issues normal loads/stores
to memory that physically sits on a card on the PCIe bus, and the hardware keeps
it coherent. We care because memory capacity per socket has hit a wall (limited
DIMM slots, DDR pins), and in cloud fleets ~**25%** of DRAM is "stranded" — unusable
because the cores are already sold. CXL adds capacity independent of cores.

**What are the three CXL sub-protocols, and which matters here?**
CXL.io (basically PCIe — discovery, config, DMA), CXL.cache (a device caching
host memory — accelerators), and **CXL.mem** (host accessing device memory). We
only care about CXL.mem, on a **Type 3** device (a "memory expander" — a dumb box
of DRAM).

**★ Why is CXL memory slow if the DRAM on the card is normal DDR5?**
Because the tax is the **interconnect**, not the memory. A load that misses LLC
has to be packetized (M2S), cross the PCIe SERDES link, be de-packetized at the
device, hit the device's DRAM controller, and come all the way back (S2M). That's
~**250–400 ns** vs ~**80–100 ns** for local DDR — **2–3×**. The DRAM itself is fine;
the round trip is the cost.

► *And bandwidth?* ~**25–30 GB/s** per x8 Gen5 link — capped by the link width,
not by the DRAM.

**★ Why do latency-bound and bandwidth-bound workloads react so differently?**
The CXL penalty is mostly fixed *latency*, not reduced throughput. Pointer-chasing
(latency-bound) workloads stall on every dependent load, so they suffer badly.
Bandwidth-bound streaming workloads barely notice — and can even *benefit*,
because CXL bandwidth is **additive** to local DDR bandwidth (you get both links'
throughput). That asymmetry is why tiering — not just "avoid CXL" — is the right
frame.

**How does the OS even see CXL memory?**
Usually as a **CPU-less NUMA node** (a "zNUMA" node — memory, zero cores). Firmware
describes it via ACPI tables: **CEDT** (the CXL host bridges), **SRAT** (declares
it as its own proximity domain), and **HMAT** (advertises its latency/bandwidth so
the kernel knows it's *slow*, not just *far*). Then existing NUMA machinery can be
pointed at it.

**★ What is memory tiering, in one sentence?**
Two tiers — fast/small local DDR and slow/large CXL — and something has to keep the
data you actually touch (the "hot" data) in the fast tier. Get it right and a
machine with 25% local DRAM performs close to one with 100%.

**★ Why is promotion harder than demotion?**
Demotion (fast→slow) just needs to find *cold* pages, and an LRU approximation is
fine — Linux already has one. Promotion (slow→fast) needs to know a page is hot
**right now**, and detecting that accurately and in time is expensive. The Linux MM
community's own stated position is that promotion is the open problem.

► *Why "right now"?* Because the hot set moves. If your detector takes a second to
converge and the hot set turns over every 100 ms, you're always promoting
yesterday's hot pages — all the migration cost, none of the benefit.

---

## Part B — The core problem

**★ Walk me through why current profiling fails.** (the four mechanisms)
Every software mechanism is stuck on the same curve — accuracy × timeliness ×
overhead, pick two:
- **PTE-scan (DAMON):** clears the Accessed bit in page tables and rescans. One bit
  is binary (touched-once looks like touched-a-million-times), and scanning a big
  workload takes **seconds**.
- **Hint faults (AutoNUMA, TPP):** unmap PTEs so the next access traps to the
  kernel. Costs a page fault per sample, and — the killer — it measures **TLB
  misses, not LLC misses**.
- **PEBS/IBS (Memtis):** the PMU samples LLC misses with addresses. Right event,
  but overhead scales with rate: NeoMem measured **>50% slowdown** going from
  1-in-10,000 to 1-in-10 samples.
- **Hardware in the CXL device (NeoMem/M5):** counters in the controller see the
  exact LLC-miss stream at zero CPU cost. Needs new hardware — that's what we build.

**★ Why is "TLB misses ≠ LLC misses" such a big deal?**
Because CXL traffic is caused by **LLC misses** — accesses that fall out of the
cache hierarchy and actually reach the device. A page can be extremely hot in the
CPU cache (lots of TLB activity) while generating almost **zero** CXL traffic.
AutoNUMA/TPP would rank it hot and promote it — pure wasted work. NeoMem shows the
two rankings are only weakly correlated. Device-side hardware sidesteps this *by
construction*: from the device you can only see the LLC-miss stream.

**★ Explain the granularity problem.**
Access density inside a 4 KB page is wildly non-uniform — a hash-table probe
touches 64 B of 4096. So 4 KB is the wrong unit in **both** directions: too coarse
for what's actually hot (you migrate 4 KB to save ~64–256 B), but also too *fine*
for the migration mechanism (per-page TLB shootdowns). Huge pages (2 MB) fix the
mechanism cost but make the waste catastrophic (>99.99%).

**★★ Then why not just migrate cache lines instead of pages?** *(the trap question)*
Because **there is no PTE for a cache line.** The page table's minimum mapping unit
is 4 KB — there's no way to remap a 64 B line through the OS. So sub-page migration
needs one of:
1. **Hardware indirection** — make local DRAM a line-granular *cache* in front of
   CXL (that's Intel Flat Memory Mode / Memstrata's premise), or
2. **Fine-grained profiling driving coarse-grained migration** — profile at 64 B to
   make *better* 4 KB decisions. That's M5, and it's what I'm doing.

The key distinction: **profiling granularity ≠ migration granularity.** M5 profiles
at 64 B and migrates at 4 KB. That's not a compromise — it's the design.

**★ What does migrating one page actually cost?**
Four things: (1) **copy** — 4 KB read from CXL + 4 KB write to DDR, eating the
bandwidth you're trying to save; (2) **page-table update** — walk the rmap for
every PTE mapping the page; (3) **TLB shootdown** — an IPI to every core that might
have the translation cached, usually the **dominant** cost; (4) **lock contention**
(mmap_lock, LRU locks). Total is on the order of **microseconds** — thousands of
times the ~250 ns you were avoiding.

► *So what follows?* A promoted page must be re-accessed many times to pay for
itself, so a *wrong* promotion is actively harmful, not just useless. That's why
real systems cap migration bandwidth with a **quota** and add **hysteresis**.

**Why does the TLB shootdown dominate?**
It's an inter-processor interrupt to potentially every core, and it stalls those
cores while they invalidate the stale translation. On a many-core machine that's
expensive and it doesn't overlap with useful work. Copy bandwidth is big but
amortizable; the shootdown is a synchronous, cross-core stall.

**What is ping-pong and how do you stop it?**
A page gets promoted, cools slightly, gets demoted, warms, gets promoted… each
round trip is pure loss. You stop it with hysteresis: thresholds with margin,
cooldown periods, or a feedback term. NeoMem literally *measures* ping-pong in
hardware and raises the hotness threshold when it's high — and it backs off twice
as hard as it leans in (β=2 vs α=1 in its formula). I'll borrow that idea.

---

## Part C — Pages vs lines (the deep dive they'll push on)

**★ Quantify the waste of page migration.**
A 4 KB page is 64 lines of 64 B. In a skewed workload only a few lines are hot —
say 4. Promoting the page moves 4096 B to keep ~256 B useful → ~**94% of the
transfer is cold**, and a fast-tier frame is burned on data that's ~6% useful. I
define **migration efficiency = useful bytes ÷ moved bytes**; for page migration on
skewed workloads it's very low. That's the number my access-density figure is meant
to expose.

**★ How would line caching (the hardware alternative) actually work?**
Make local DRAM a hardware cache of 64 B lines in front of CXL — Intel Flat Memory
Mode. It's **direct-mapped** and **1:1**: each CXL line has exactly one local DRAM
slot; on a miss you swap the line in and the resident one out. It's **transparent**
— no page faults, no TLB shootdowns, no migration daemon. Waste per move drops to
~zero and the fixed cost drops from µs to ns.

**★ So line caching is strictly better?** *(they want you to say no)*
No — it's a genuine trade-off, which is exactly why the field hasn't converged:
- **+** near-zero waste, ns-scale moves, no OS involvement
- **−** a huge **tag array**; **conflict misses** (two hot lines mapping to the same
  slot thrash despite free capacity elsewhere); the fast tier stops being
  separately addressable **capacity** (it's now a cache, so 1:1 means you "lose"
  half your addressable memory); and it needs **new hardware**.
Page migration keeps 100% usable capacity and needs no hardware, at the cost of
waste and µs moves. Neither wins outright.

**Why direct-mapped and not set-associative in Flat Memory Mode?**
Tag storage and lookup latency. At 64 B granularity over hundreds of GB, the tag
array is already enormous; associativity multiplies it and puts a comparison on the
critical path of every access. Direct-mapped keeps the lookup a single indexed
probe. The price you pay for that simplicity is conflict misses — which is exactly
the hole Memstrata plugs.

**Why 1:1 local:CXL in Flat Memory Mode?**
The tag/metadata sizing and the swap protocol assume it, and it bounds the
worst-case miss cost. It also means capacity isn't additive — you buy 1 TB DDR +
1 TB CXL and the OS sees 1 TB. The pitch is that the CXL TB is much cheaper and you
get near-DRAM performance with *zero* software change.

---

## Part D — The three papers (prove you read them)

### D.1 — M5 (ASPLOS '25) — the one I'm implementing

**★ What's M5's one-sentence contribution?**
Put profiling hardware *in the CXL device* that counts accesses to every 4 KB page
**and every 64 B word**, and use the sub-page information to make page-migration
decisions that are actually right.

**★ What are the two trackers and why two?**
- **HPT (Hot Page Tracker):** top-K over 4 KB pages — tells you *which* page to
  migrate.
- **HWT (Hot Word Tracker):** top-K over 64 B words — tells you *how densely hot*
  that page is.
Two, because access **count** alone is misleading: a page with 500 accesses
concentrated in 2 words is a bad migration candidate (you'd move 4 KB for 128 B),
while a page with 500 accesses spread over 40 words is a good one. Only the
word-level view distinguishes them.

**★ What's the "top-K tracker," and where's the idea from?**
It's a bounded counter table that keeps the K most-frequent items — Misra–Gries /
heavy-hitter style. On a hit you increment; on a miss with no free slot you
decrement (or evict) the minimum. Fixed hardware budget, which is the point. The
idea is **borrowed from hardware Rowhammer defenses**, which have the identical
problem: find the few most-accessed rows out of a huge space, in hardware, with a
small counter budget.

**★ Profile at 64 B but migrate at 4 KB — isn't that a contradiction?**
No — it's the whole insight. You *can't* migrate 64 B through the OS (no PTE for a
line), so you use the fine-grained data to make the coarse-grained decision
smarter. Profiling granularity and migration granularity are different things.

**What are M5's results?**
It identifies ~**47% hotter pages** than the baselines (its chosen pages receive
47% more accesses — a direct measure of decision quality), giving ~**+20% vs
AutoNUMA Balancing** and ~**+14% vs DAMON** on memory-intensive apps.

► *Why are these smaller than NeoMem's headline 4.7×?* Different baselines,
platform, and metric — not comparable. M5 measures decision quality against a
reasonably-tuned system; don't put the two papers' percentages side by side.

**What's M5's limitation / what did they not solve?**
It still migrates at 4 KB, so it inherits the per-page migration cost (TLB
shootdowns etc.) — it makes the *decision* better, not the *mechanism* cheaper. And
the word tracker adds hardware area you have to justify.

► *Honesty flag for yourself:* I'm confident about HPT/HWT being top-K trackers and
the 64 B-profile / 4 KB-migrate split and the headline numbers. The exact internal
sizing of the HWT and how it's scoped (I assume it only tracks words within
already-hot pages, to stay small) is my reconstruction — if asked for that detail,
say you'd confirm it against the artifact.

### D.2 — NeoMem (MICRO '24)

**★ What's NeoMem's thesis, and how does it differ from M5's?**
NeoMem says the bottleneck is **profiling resolution in *time*** — fix the profiling
and 4 KB pages are fine; granularity is secondary. M5 says the bottleneck is
resolution in ***space*** (sub-page). Same problem, different diagnosis. Good thing
to volunteer — it shows you read both.

**★ Explain the count-min sketch. Why a sketch instead of per-page counters?**
Per-page 32-bit counters for 512 GB would need **512 MB** of on-device SRAM — too
much. Instead NeoProf uses a 2D array, width **W** × depth **D**, with **D**
independent hash functions (H3). On each access you increment all D counters; you
estimate a page's count as the **minimum** across the D lanes.

**Why the minimum?**
Because hash collisions only ever *inflate* a counter (two pages sharing a bucket).
So every lane is an over-estimate, and the tightest over-estimate is the smallest
one — hence "count-**min**." It can over-count but never under-count.

**What's "hot-page filtering" and why is it needed?**
Once a page crosses the threshold, every later access would re-report it and flood
the hot-page buffer. So NeoProf sets a bloom-filter-style "hot bit" on first
detection and suppresses repeats.

**How does it know when the sketch has gotten too inaccurate?**
It keeps a **64-bin histogram** of the counter distribution, so the host can compute
a *tight* error bound instead of the loose worst case, and reset when the sketch
saturates.

**★ Explain the dynamic threshold.**
The hotness threshold is the **p-percentile** of the access-frequency histogram, and
`p` adapts each interval: `p ← p·(1+B)^α / (1+P)^β`, with B = bandwidth utilization,
P = ping-pong severity, α=1, β=2. Intuition: **high CXL bandwidth pressure →
promote more aggressively; lots of ping-pong → back off, and back off twice as
hard.** Plus a migration **quota** (default **256 MB/s**).

**NeoMem's numbers?**
**32–67% geomean speedup** over prior solutions; **4.7× on GUPS**, **3.5× on
XSBench**, **1.58× over Memtis**; migration intervals as short as **10 ms**
(impossible for PTE-scan, stuck in seconds). Hardware cost ~**5.3 mm²**, **152 mW**
at 22 nm; CPU overhead of enabling it **0.02%**.

► *Why GUPS/XSBench specifically?* Those are random-access, no-spatial-locality
workloads where profiling quality dominates everything — the cleanest demonstration.

**What does NeoMem reuse rather than build?**
Cold-page detection — it just uses Linux's existing **LRU 2Q**, because finding cold
pages doesn't need high resolution. Good engineering judgement worth citing.

**Why isn't NeoMem your choice if the sketch is so easy?**
The sketch *is* easy (a few hashes and a counter array). But once it works, the rest
of the contribution is the **kernel daemon and policy** — that's OS work, and I want
to be on the hardware side. In a simulator I'd model the "daemon" as a policy module
anyway, so it's softer than it sounds, but the centre of gravity is software.

### D.3 — Memstrata (OSDI '24)

**★ What problem does Memstrata attack that the other two ignore?**
**Multi-tenant interference.** It assumes hardware-managed tiering (Intel Flat
Memory Mode) already works for a single workload, and shows it *breaks under
co-location*: two VMs whose lines map to the same direct-mapped slots thrash each
other, and one VM's behaviour silently degrades another's by **>30%** — invisible to
both tenants. In a cloud that's a broken SLA.

**★ What's the fix?**
Two software pieces, no hardware change:
- **Page coloring** — the hypervisor allocator controls which physical pages (and
  therefore which cache slots) each VM can use, and partitions the color space so
  VMs *structurally can't* conflict.
- **Online slowdown estimator** — cheaply estimates each VM's tiering-induced
  slowdown and hands the sensitive ones more *unmanaged* local DRAM.

**Memstrata's numbers?**
≤**5% degradation** vs all-DRAM for >**82%** of workloads; in multi-VM runs, outlier
degradation drops from **>30% to <6%**. It's a pure allocator — no hardware, no guest
changes.

**★ Why is Memstrata your counterexample, and why aren't you implementing it?**
It's the honest other side of "just use line granularity": Flat Memory Mode *does*
migrate at 64 B and *does* kill the migration-overhead problem — and it buys conflict
misses, tag storage, 1:1 capacity, and multi-tenant interference. I'm not
implementing it because (a) its contribution is a software allocator, not hardware,
and (b) CXLRAMSim doesn't model Flat Memory Mode, so I'd have to build the hardware
tiering *first* and then the allocator on top.

**Cross-paper: put the three diagnoses in one line each.**
NeoMem → not enough resolution in **time**. M5 → not enough resolution in **space**.
Memstrata → the problem only appears under **co-location**. They disagree, and that
disagreement is the reason three papers coexist.

---

## Part E — Methodology & the simulator

**★ What is CXLRAMSim and why this simulator?**
A full-system simulator on **gem5 v25** that boots **Linux 6.14**, modelling the CXL
device at its *correct position on the I/O bus* — so the kernel, drivers, and
software stack are **unmodified**. That matters: my tiering code can interact with
the real Linux path, and my hardware profiler sits where a real one would. Results
are far more defensible than a hand-waved latency model.

**★ Where exactly does your code go?**
At the point where the CXL endpoint de-packetizes an M2S request into a device DRAM
access, I have `{physical address, read/write, timestamp}`. That is precisely the
LLC-miss-to-CXL stream both NeoMem and M5 profile — nothing else is visible from
there. My HPT/HWT profiler is a **tap** on that path, plus a counter structure.

**★ Why model migration instead of driving real Linux migration?**
Speed and control. Full-system gem5 is slow, and a modeled migration engine lets me
iterate fast *and* set an explicit, inspectable cost model (copy bandwidth on both
tiers, a fixed TLB-shootdown penalty, a bandwidth quota). That makes the results
easy to explain and the comparison fair. Real kernel-module migration is a possible
extension — it's one of my open questions for you.

**★ What are the five comparison arms and why?**
All-CXL (lower bound), all-local-DRAM (upper bound), naive page migration (the
"problem" arm), M5's scheme (the proposal), and an **oracle** (offline-optimal
placement). The gap between the naive arm and the oracle *is* the problem I'm
replicating; the fraction of it M5 closes is my result. I always report both bounds
next to every scheme — a speedup number without them is uninterpretable.

**What's the oracle and how do you compute it?**
Offline-optimal placement computed from a full access trace — knowing the whole
future, put exactly the right pages in the fast tier. It's not implementable online;
it's the ceiling that tells me how much of the gap any real policy leaves on the
table.

**★ Why these workloads?**
- **GUPS** — random 8 B updates, zero spatial locality: the *adversarial* case and a
  negative control for the granularity argument (a flat access-density curve).
- **XSBench** — Monte Carlo lookups into big tables.
- **PageRank** — irregular graph access, hot set shifts per iteration.
- **Btree / YCSB-C** — Zipfian skew, extreme sub-page hotness — where M5 should shine.
They span "no locality" to "extreme skew," so they bracket the behaviour.

**★ What's your single most important figure?**
The **access-density CDF**: for each 4 KB page, what fraction of its accesses fall in
the top-k 64 B lines. If 80% of accesses hit <10% of the page, the granularity
argument is proven in one plot. Note: in the deck that curve is the *expected shape*,
not measured data — I say so explicitly, and if it comes out flat for a workload,
that's an equally valid result (sub-page hotness doesn't hold there).

**★ How do you validate the simulator before trusting any number?**
First: boot to a shell and confirm `numactl -H` shows the CXL zNUMA node. Then a
**pointer-chase latency microbenchmark** pinned to the local node vs the CXL node —
if I can't show CXL is ~2–3× slower, nothing else means anything. Then check
bandwidth against the paper's ballpark, and confirm determinism (same config +
checkpoint → same result).

**Your workloads are tiny vs the papers' 10–20 GB. Is that legitimate?**
Yes, if disclosed. Full-system gem5 can't run 10–20 GB RSS in reasonable time, so I
scale workloads to hundreds of MB and scale the fast-tier capacity proportionally, so
the *ratio* stays realistic even though the absolute size isn't. It's a standard
methodology as long as I state it — which I do.

**Why is full-system gem5 slow, and how do you cope?**
It's ~100 KIPS–1 MIPS; booting Linux takes minutes. I checkpoint after boot and
restore for every experiment, fast-forward with KVM/atomic CPU and switch to the
detailed CPU only for the region of interest. Standard gem5 practice.

---

## Part F — Defending your choices & scope

**★ Why M5 and not NeoMem or Memstrata?**
M5 is closest to the sub-page-hotness idea, its HPT/HWT are simple hardware
(top-K counter tables), and the profiling→decision split implements cleanly in a
simulator — and I can ship HPT alone for a working result, then add HWT as the
differentiator. NeoMem's sketch is even easier to code but its centre of gravity is
the kernel daemon (software). Memstrata's contribution is a software allocator on top
of a hardware mode CXLRAMSim doesn't model. Given the brief is *hardware*, M5 fits
best.

**★ What's the minimum you'll deliver, and what's the stretch?**
Core: reproduce the *problem* — the access-density CDF, migration efficiency, and the
naive-migration-vs-oracle gap. That alone is a result and it de-risks everything.
Then HPT, then HWT, then evaluation. Stretch: hardware cost model, a CXL-latency
sweep, and the multi-tenant angle. I'll be explicit about which is which.

**Isn't this just re-implementing a paper?**
No. The mandatory part is reproducing, in CXLRAMSim, *why* OS page migration fails —
the profiling/granularity/cost problem — with measurements. Implementing M5 is the
optional part, and even there the contribution is building the profiler in this
simulator and measuring how much of the oracle gap it closes on my workloads, not
copying their numbers.

**Why not just use huge pages to cut migration cost?**
Huge pages amortize the per-migration fixed cost, but they make internal
fragmentation *dramatically* worse — a 2 MB page promoted for one hot line wastes
99.997% of the transfer. That's the exact problem HWT exists to detect, so huge
pages trade one failure for a worse one.

**Why not put everything in CXL and skip tiering?**
Latency. Anything latency-bound would eat the ~250–400 ns on every LLC miss.
Tiering exists precisely because most of a workload's data is cold and only a small
hot set needs the fast tier.

---

## Part G — Curveballs / depth probes

**Is CXL memory cache-coherent?**
Yes — that's the point of CXL vs plain PCIe. Under CXL.mem the host's coherence
domain extends to the device memory; the hardware keeps it coherent, so software
just does loads/stores. (CXLRAMSim models this with a MESI two-level directory in
gem5's Ruby.)

**Difference between CXL.mem and CXL.cache?**
CXL.mem = host accessing *device* memory (our case, Type 3). CXL.cache = a *device*
caching *host* memory (accelerators, Type 1/2). Opposite directions.

**What does "reactively" mean for line caching vs "with old info" for the OS?**
Hardware line caching reacts to the *actual* access stream at line granularity with
no software in the loop — but only after a miss happens (it can't prefetch intent).
The OS decides proactively but from *stale* profiling, so it can pre-place a page —
just often the wrong one. Different failure modes.

**How big is the tag array for line caching, ballpark?**
One tag per 64 B line of cached capacity. For, say, 256 GB of local DRAM that's 4
billion lines — even a few bytes of tag each is tens of GB of metadata. That's why
it must be direct-mapped and carefully engineered, and why it's a hardware feature,
not something you bolt on.

**If your access-density CDF comes out flat, is the project a failure?**
No. A flat curve (like GUPS) means sub-page hotness doesn't hold *for that
workload*, which is itself a useful, reportable result — it bounds where M5-style
tracking helps. The skewed workloads (Btree/YCSB) are where I expect the strong
curve; having a negative control is a feature.

**How would you actually implement the HWT to keep it small?**
My plan: key a top-K table on `paddr >> 6` (64 B words), but only populate it for
words inside pages HPT has already flagged hot — so the word tracker stays bounded.
That keeps the common case cheap and focuses hardware where it matters. (I'd confirm
this matches the paper's exact scoping.)

**Count-min sketch vs top-K — why did the two papers pick differently?**
Different points on the accuracy/space curve. Top-K (M5) gives you the *exact
identities* of the heavy hitters with no hash-collision false positives, but only
for the top K. Count-min (NeoMem) is smaller and gives *approximate* counts for
*every* page, at the cost of collision-inflated estimates. Top-K when you want
precise winners; sketch when you want a cheap estimate over everything.

**What's the risk that most worries you in this project?**
Getting CXLRAMSim built and booting — I don't have a public repo yet, and building a
full-system image from scratch is a multi-day detour that teaches nothing about
tiering. That's my first open question for you. After that, the technical risk is
low because Phase 2 (the access trace + CDF) produces a real result before any
policy code exists.

**How do you know your modeled migration cost is realistic?**
I anchor it to known quantities: copy time from the tier bandwidths, a fixed
TLB-shootdown penalty in the µs range (from the literature and measurable in the
sim), and a bandwidth quota. I'd do a sensitivity sweep on the shootdown penalty so
the conclusion doesn't hinge on one guessed constant.

---

## Part H — Things to have ready but not over-rehearse

- **Baselines vocabulary** (so you recognise them if named): first-touch NUMA,
  AutoNUMA Balancing (ANB), **TPP** (Meta, ASPLOS'23 — hint-fault placement),
  **DAMON** (region-sampled PTE-scan), **Memtis** (SOSP'23 — PEBS + histogram
  threshold; NeoMem's strongest baseline), **Pond** (ASPLOS'23 — Azure CXL pooling,
  the stranded-memory source).
- **The 30-second chain** for the trap question, memorized:
  *no PTE for a line → needs hardware indirection → that's Flat Memory Mode → which
  costs conflict misses, tag storage, and 1:1 capacity → which is what Memstrata
  then has to fix.*
- **One number per fact:** 2–3× latency; ~250–400 ns; 4 KB = 64 × 64 B; µs per
  migration; ~25% stranded DRAM; NeoMem 4.7× GUPS; M5 +20%/+14%; Memstrata 30%→<6%.

If you can hold Part B's four answers, Part C's trade-off, and one solid paragraph
per paper in Part D, you've covered ~80% of what they'll actually ask.
