# From profiling to the simulator

What this repository establishes, and what it implies for the CXLRAMSim half of the
project. Written for the conversation with the lab, not as a plan of record.

---

## What is settled

**The measurement is calibrated and the phenomenon is real.** Sub-page hot skewness
reproduces: PageRank is maximally dense (63.1/64 words per page, `P(≤48) = 0.007`
against the paper's 0.02), the graph traversals are substantially sparser, and the
ordering across benchmarks matches M5's Figure 4.

**Two methodological facts that were not obvious going in**, both of which would have
silently produced wrong numbers:

1. *The measurement window is the parameter that makes the question well-posed.*
   Word coverage per page only grows, so over an unbounded window every page looks
   dense — and, measured that way, the answer is identical for every cache size,
   because compulsory misses eventually touch everything. Any sparsity figure without
   a stated window length *and kind* is not reproducible.

2. *Pin cannot see kernel-side memory traffic, and for these benchmarks that traffic
   dominates.* GAPBS loads a 1.05 GB CSR with `read(2)`; the kernel writes every word
   of ~269,000 pages and Pin observes none of it, while a memory controller observes
   all of it. Making that copy user-visible moved BFS's `P(≤48)` from 0.813 to 0.320
   against the paper's 0.345.

The second one is the interesting one for what comes next, because it is an argument
*for* the simulator rather than against it.

---

## Why this makes the CXLRAMSim work easier to justify

In gem5, the CXL device's request path sees **every** request: application, kernel,
page-fault zeroing, page-cache population, DMA. There is no blind spot to patch
around, because there is no user/kernel boundary the instrumentation sits on the
wrong side of.

So the honest framing for the report is not "we did it in Pin because we had no
hardware", it is:

> A Pin-based profiler can characterise an application's own access pattern
> accurately, and we validated it to analytic ground truth. It structurally cannot
> reproduce what a memory-controller-resident counter sees, and we measured the size
> of that gap: for GAPBS it is the difference between `P(≤48) = 0.81` and `0.32`.
> Closing it requires the counters to sit below the OS, which is exactly what
> CXLRAMSim provides.

That is a much better motivation for the simulator than "the paper used one."

---

## What the pintool gives the simulator work that it would not otherwise have

**An exact reference to score approximations against.** M5's HPT and HWT are bounded
top-$K$ counter tables (Misra–Gries / space-saving, borrowed from Rowhammer defences).
Their whole value proposition is *approximating* the exact counts with a fixed
hardware budget. Figure 8 in the paper is precisely this comparison: the average
access-count ratio of the pages a mechanism identifies, against PAC's exact counts.

`results/*/**.pages.bin` holds the exact per-page and per-64 B-word counts. When an
HPT is implemented, its top-$K$ output can be scored against that directly:

- what fraction of the true top-$K$ pages does a $K$-entry tracker find?
- how does that degrade as $K$ shrinks, or as the counter width shrinks?
- how much does the HWT's density signal change which pages get selected?

None of that needs the simulator. It is a trace-driven experiment that can be run
today against data already collected, and it answers the question a reviewer will
ask first ("what does the hardware cost buy you?").

**A concrete finding that should shape the policy design.** Restricting the
population to the pages a migration policy would actually act on inverts the result
for graph workloads:

| BFS population | P(≤16 of 64 words) |
|---|---|
| all touched pages | 0.708 |
| top-100,000 hottest | 0.424 |
| top-10,000 hottest | 0.000 |

The hottest BFS pages are dense. Sparsity lives in the lukewarm tail. A count-only
top-$K$ policy is therefore already selecting dense pages for this workload, and HWT
has little left to correct — whereas for Redis, with 86% of pages sparse in M5's own
figure, the argument is strong.

If that holds up across the remaining benchmarks, it is a real result and it is
sharper than the paper's framing: **sub-page tracking earns its hardware on key-value
workloads, not on graph analytics.** Worth checking before committing to implement
HWT rather than HPT alone.

---

## Already done since this was written

Items 1 and 2 below are complete: the trackers are implemented and scored
(`docs/hardware-evaluation.md` §1), and the placement study was run both with exact
counts and with bounded-tracker output (§2b). A granularity sweep over page size and
word size was added at the professor's suggestion (`report.md` §6.5), and a two-tier
latency model closes the loop with a speedup number (§6.4).

## Concrete next steps, roughly in order

1. **Score a top-$K$ tracker offline.** Implement HPT (Misra–Gries over `paddr >> 12`)
   and HWT (over `paddr >> 6`, restricted to HPT-flagged pages) as a Python or C++
   pass over `.pages.bin`. Sweep $K$ and counter width. Produces M5's Figure 8
   analogue with no simulator involved. Cheapest high-value experiment remaining.

2. **Finish the benchmark set.** Redis is the one that matters most — it is the
   extreme sparse point and the case where sub-page tracking clearly pays. Scripted
   in `benchmarks/setup_redis.sh`, not yet run here. Liblinear next. SPEC CPU2017
   needs a licence; ask whether the lab has one.

3. **Close the remaining Figure 4 gap** or bound it. Two untested hypotheses:
   the dataset (M5's graphs came from a Memtis `bench_dir` that was not published),
   and `NodeID` width — GAPBS defaults to `int32_t`, and 64-bit node IDs would halve
   the neighbours per cache line and roughly double the lines touched per traversal.
   The second is cheap to test and would be worth knowing.

4. **Port the counters into a public CXL simulator — and it need not be CXLRAMSim.**

   CXLRAMSim is still unreleased; no repository exists under any obvious name. But
   **SimCXL** (https://github.com/ferry-hhh/CXL-DMSim, which absorbed CXL-DMSim) is
   public, gem5-based, full-system and cycle-level, and models a **CXL Type 3 memory
   expander** over CXL.io + CXL.mem. That is everything this work actually needs.

   The hook point already exists and matches the probe's design exactly:

   ```
   src/mem/cxl_bridge.cc:219
     CXLBridge::BridgeResponsePort::recvTimingReq(PacketPtr pkt)
   ```

   One line inside it — `probe.onRequest(pkt->getAddr(), pkt->isWrite())` — puts the
   counters where physical addresses and kernel traffic are both visible, which is the
   whole argument for moving off Pin (report §4.2).

   **On architectural fidelity:** the CXLRAMSim paper criticises CXL-DMSim for
   attaching CXL to the MemBus rather than the IOBus and enumerating it as a PCI
   memory controller. That critique is about *timing* fidelity. It does not affect
   which addresses reach the device, which is the only property this measurement
   depends on. For counter placement, SimCXL is adequate today; if CXLRAMSim is
   released later, the probe moves across unchanged.

   **Build constraint on this machine:** SimCXL targets gem5 23.10 on Ubuntu
   20.04/22.04 with gcc 9.4+. This workstation is Ubuntu 26.04 with only gcc 15
   installed, and gem5 23.10 will not build against it. Two options, neither
   requiring new hardware: install an older gcc alongside (`apt install gcc-12
   g++-12`, then `scons CC=gcc-12 CXX=g++-12`), or use gem5's official
   `ubuntu-22.04_all-dependencies` container image — no container runtime is
   installed here yet.

5. **Port to CXLRAMSim if and when it is released.** `counter_table.hpp` is deliberately free of
   Pin dependencies — it takes a line address and a direction. Hooking it to the CXL
   device's request path should be close to a drop-in, and at that point the addresses
   are physical and the kernel traffic is visible.

5. **Then, and only then, policy and migration.** Modelling migration cost honestly
   (copy bandwidth on both tiers, TLB shootdown, a per-interval quota) is where the
   simulator becomes indispensable, and it is the part that produces a performance
   number rather than a characterisation.

---

## Things worth raising with the lab

- **Which paper to implement.** The evidence collected here favours M5 — the trackers
  are simple bounded structures, the profiling/decision split is clean to model, and
  there is now an exact reference to validate a tracker against. But the top-$K$
  finding above suggests the *interesting* evaluation is on Redis rather than GAPBS,
  which changes what needs to be running in the simulator.

- **Machine.** Everything here runs on a desktop (i9-12900K, 31 GB). The heaviest
  GAPBS kernel takes about two minutes under Pin. A server would help for SPEC and
  for larger graphs, but nothing is blocked on it.

- **Scope.** The characterisation is a defensible deliverable on its own — it is
  M5's §4, reproduced with an independent method, with the methodology deviations
  quantified rather than asserted. Implementing a tracker on top is the natural
  second half; implementing full migration policy is a third piece that may be more
  than the course requires.
