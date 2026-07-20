# 4. Memstrata — "Managing Memory Tiers with CXL in Virtualized Environments"

**Venue:** OSDI 2024 · **Authors:** Zhong, Berger, Waldspurger, Wee, Agarwal, Agarwal, Hady, Kumar,
Hill, Chowdhury, Cidon (Columbia / Microsoft / Intel / Michigan / Wisconsin)
**PDF:** https://www.usenix.org/system/files/osdi24-zhong-yuhong.pdf

## One-line summary

Hardware-managed CXL tiering (Intel Flat Memory Mode) mostly works, but it breaks for a minority of
workloads and it lets co-located VMs silently sabotage each other; Memstrata is a lightweight
allocator that fixes both with page coloring plus an online slowdown estimator.

## Context: what Intel Flat Memory Mode is

The paper is the first public description of it. Instead of exposing CXL memory as a separate NUMA
node, the memory controller manages local DRAM as a **hardware-managed cache** in front of CXL
memory, at **cache-line granularity**, transparently. The OS sees one flat address space with a
single capacity.

Key properties:
- **1:1 ratio** between local DRAM and CXL memory (this is a design constraint, not a tuning knob).
- **Direct-mapped.** Each CXL line has exactly one local DRAM slot it can occupy.
- On a miss, the line is swapped in; the resident line is swapped out.
- No OS involvement whatsoever. No page faults, no TLB shootdowns, no migration daemon.

Note how directly this answers failure mode 2 from [03](03-the-core-problem.md): granularity is
64 B, so there's no wasted transfer and no per-page fixed cost. **That's the "lines instead of pages"
idea, shipped in silicon.**

## What goes wrong

1. **It's good on average, bad in the tail.** Most workloads land within a few % of all-DRAM. But
   some are much worse, and those are exactly the ones with access patterns that generate conflict
   misses in a direct-mapped structure.
2. **Inter-VM interference.** Two VMs' pages can map to the same DRAM slots. VM A's streaming access
   evicts VM B's hot lines. B's performance drops >30% and neither tenant nor the hypervisor can see
   why. In a public cloud this is a correctness-of-business problem, not just a perf problem.
3. You can't fix it by giving a VM "more cache" — capacity is fixed at 1:1 and placement is
   determined by physical address.

## The solution

**Page coloring.** The hypervisor's memory allocator controls which physical pages a VM gets, and
therefore which DRAM slots its data can map to. Memstrata partitions the color space across VMs so
that **different VMs cannot conflict with each other**. Interference becomes structurally impossible
rather than statistically unlikely.

**Online slowdown estimator.** Some VMs are inherently tiering-sensitive regardless of interference.
Memstrata estimates each VM's slowdown online — cheaply, by sampling — and reallocates *unmanaged
local DRAM* (memory outside the flat-mode region) to the sensitive ones. So sensitive VMs get more
real local DRAM; insensitive VMs don't waste it.

The whole thing is a memory allocator. No hardware changes, no guest changes.

## Results

- ≤5% degradation vs all-DRAM for >82% of workloads.
- In multi-VM experiments, outlier VMs' degradation drops from **>30% to <6%**.
- Overhead is negligible — it's an allocation-time decision.

## Why this matters for your project

It's the counterexample to a naive "lines are strictly better" claim. Flat Memory Mode *does* migrate
at line granularity and it *does* eliminate the migration overhead problem — and it introduces
conflict misses, fixed 1:1 capacity, and cross-tenant interference. Use it in your presentation as
the honest other side of the tradeoff table.

## If you implemented it in CXLRAMSim

You would need to build, in order:
1. A direct-mapped, line-granular near-memory cache in front of the CXL memory (tag array, swap
   logic, miss path). **This alone is a substantial project** and is the hardware piece.
2. A page-coloring allocator, and a way to model two tenants.
3. The slowdown estimator.

Step 1 is genuinely interesting hardware work and would let you directly measure conflict misses and
compare line-vs-page migration head to head. Steps 2–3 are software and less aligned with your
stated focus. **A defensible scope: implement step 1 only, and use it as the "line granularity" arm
of your comparison** — you get the Memstrata motivation experiment without the allocator.

## Questions to be ready for

- Why direct-mapped and not set-associative? (Tag storage and lookup latency at 64 B granularity
  over hundreds of GB. Associativity costs SRAM and a comparison on the critical path.)
- Why 1:1? (Tag/metadata sizing and the swap protocol assume it; also it bounds worst-case miss
  cost.)
- Doesn't this waste half your capacity? (Yes, in the sense that local DRAM isn't separately
  addressable — you buy 1 TB DDR + 1 TB CXL and the OS sees 1 TB. The pitch is that the CXL TB is
  much cheaper, and you get near-DRAM performance without touching software.)
