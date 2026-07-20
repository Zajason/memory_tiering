# 2. Memory Tiering Fundamentals

## The setup

Two tiers:
- **Fast/near/local tier** — DDR attached to the CPU. Small, fast.
- **Slow/far tier** — CXL memory. Large, ~2–3× latency.

Goal: keep the data the application actually touches in the fast tier. Everything else can rot in
CXL. If you get this right, a machine with 25% local DRAM performs close to a machine with 100%
local DRAM, at a fraction of the cost. That's the pitch.

Two verbs:
- **Promotion** — move a page slow → fast. Needs to be *timely*; a page promoted after it went cold
  is pure waste.
- **Demotion** — move a page fast → slow. Needs to be *safe*; demoting something still hot causes a
  ping-pong.

Demotion is the easy one — LRU approximations are fine, and Linux already has an LRU. **Promotion is
the hard one**, because it requires knowing a page is hot *now*, and detecting that is expensive.
The Linux MM community's own stated position is that promotion is the open problem.

## How you find hot pages today (and why each way is bad)

This is the heart of the motivation section in all three papers. Learn this table.

### (a) PTE Access-Bit Scanning — `DAMON`, `kstaled`
The MMU sets an *Accessed* bit in the page table entry on access. Software periodically clears the
bits, waits, then rescans to see which got set.

- ✅ No hardware needed, vendor-neutral.
- ❌ **One bit = binary.** A page touched once and a page touched 10 million times look identical.
- ❌ Scanning the page tables of a 512 GB workload takes *seconds*. Your hot set has moved by then.
- ❌ Clearing access bits forces TLB shootdowns.
- ❌ Resolution/overhead tradeoff is brutal: scan often enough to be timely and you burn a core;
  scan rarely and you're blind. DAMON works around it by sampling *regions* rather than pages,
  trading spatial resolution away.

### (b) Hint Faults / NUMA Balancing — `AutoNUMA`, `TPP`
Periodically mark PTEs as not-present ("poison"). Next access traps to the kernel; the kernel logs
it and fixes the PTE.

- ✅ Gives you real access events with a page address.
- ❌ Each sample costs a **page fault** — thousands of cycles.
- ❌ **It counts TLB misses, not LLC misses.** This is the subtle killer. A page that's hot in the
  cache generates lots of TLB traffic but *zero* CXL memory traffic — promoting it gains you
  nothing. NeoMem shows TLB-access rank and LLC-miss rank are weakly correlated.
- ❌ Sampling rate must stay low, so it's slow to converge.

### (c) PMU Sampling — `PEBS` (Intel), `IBS` (AMD), used by `Memtis`
The performance-monitoring unit records the address of, say, every 10,000th LLC miss.

- ✅ Measures the *right* event (LLC miss to CXL) with real addresses.
- ❌ Overhead scales with sample rate. NeoMem measured >50% slowdown going from 1-in-10,000 to
  1-in-10 samples. So you're stuck with sparse samples and long convergence.
- ❌ Vendor-specific and often unavailable/limited in VMs — a dealbreaker for cloud.

### (d) Hardware profiling in the CXL device — **NeoMem's NeoProf, M5's HPT/HWT**
Put a counter array in the CXL controller. It sees every request that reaches the device — which is
*exactly* the LLC-miss stream you want — at zero CPU cost.

- ✅ Perfect event, full rate, no CPU overhead, no vendor lock-in (it's your device).
- ❌ You can't afford one counter per page (512 GB / 4 KB × 4 B = 512 MB of SRAM). Hence sketches
  (NeoMem) or top-K trackers borrowed from Rowhammer defenses (M5).
- ❌ Requires new hardware. **This is the part you simulate.**

## What migration actually costs

When the kernel decides to promote a 4 KB page, it pays:

1. **Copy** — 4 KB read from CXL + 4 KB write to DDR. Consumes the very bandwidth you're trying to
   save.
2. **Page table update** — walk the rmap to find every PTE mapping this page, update them all.
3. **TLB shootdown** — an IPI to every core that might have the translation cached. On a 64-core
   machine this is *expensive* and it stalls other threads. This is often the dominant cost.
4. **Lock contention** — `mmap_lock`, LRU locks, etc. Migration doesn't parallelize well.
5. **Fault stall** — the accessing thread may block during the migration.

Rule of thumb: a single page migration costs on the order of **microseconds** — thousands of times
the ~250 ns you were trying to avoid. **A promoted page must be re-accessed many times to pay for
itself.** That's why hotness detection needs to be right, and why migration bandwidth gets quota'd
(NeoMem caps at 256 MB/s by default).

## Ping-pong

Page gets promoted, cools slightly, gets demoted, warms, gets promoted... Each round trip is pure
loss. Every real system needs hysteresis: thresholds, cooldown periods, or demotion-resistance
counters. NeoMem explicitly *measures* ping-pong in hardware and feeds it back to raise the hotness
threshold. Worth stealing that idea whichever paper you pick.

## Linux mechanisms, named

So you recognize them in papers:

- `mm/memory-tiers.c` — the tier abstraction, added ~v6.1
- **AutoNUMA Balancing (ANB)** — hint faults, promotes toward the accessing CPU
- **TPP** (Meta, ASPLOS'23) — Transparent Page Placement; hint-fault based, adds demotion-first
  allocation and decouples promotion/demotion paths
- **DAMON** — region-based access monitoring, sampling PTE access bits
- **Memtis** (SOSP'23) — PEBS-driven, maintains an access-frequency histogram and computes a
  dynamic hotness threshold to fill the fast tier exactly. Common baseline; NeoMem beats it 1.58×.
- **MGLRU / LRU 2Q** — what NeoMem reuses for *cold* page detection instead of reinventing it

## Sanity check

- [ ] I can explain why promotion is harder than demotion.
- [ ] I can name the four profiling approaches and one fatal flaw of each.
- [ ] I understand why "TLB misses ≠ LLC misses" invalidates AutoNUMA/TPP for CXL.
- [ ] I can list four costs of migrating one page, and say which usually dominates.
