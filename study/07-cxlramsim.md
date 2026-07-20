# 7. CXLRAMSim — the simulator

**Paper:** "CXLRAMSim v1.0: System-Level Exploration of CXL Memory Expander Cards"
arXiv: https://arxiv.org/abs/2603.29483

> ⚠️ **Open question — resolve this first.** The paper states the authors *plan* to open-source and
> upstream into gem5; I could not find a public repository. Your professor is presumably giving you
> access (possibly a lab-internal fork, possibly they're an author). **Ask for the repo and build
> instructions before you plan anything else** — everything below is from the paper and needs to be
> checked against the actual code. See [../experiments/README.md](../experiments/README.md).

## What it is

A **full-system, gem5-integrated** simulator for CXL memory expander cards. Built on **gem5 v25**,
booting **Linux 6.14** / **Ubuntu 24.04 LTS**.

Its distinguishing claim: it models the CXL device **at its correct position on the I/O bus**, not
as a second memory controller with extra latency bolted on. That means an **unmodified kernel,
unmodified drivers, unmodified software stack** — the device is discovered and configured through
the real path.

Why that matters to you: your tiering code can be the *real* Linux tiering code (or a real patch to
it), and your hardware profiler sits where a real one would sit. Results are far more defensible
than a hand-waved latency model.

## Components (from the paper)

| Component | What it models |
|---|---|
| **Firmware model** | Extended x86 BIOS emitting ACPI **MCFG, DSDT, CEDT, SRAT** so the OS discovers the CXL topology |
| **CXL.io** | Root Complex + register sets for device enumeration (the PCIe-ish path) |
| **CXL.mem** | Transaction layer, **M2S / S2M** channels, packetization/de-packetization at the endpoints |
| **Coherence** | MESI two-level directory protocol (gem5 Ruby) |
| **Toolchain** | Supports **cxl-cli**, so CXL memory can be exposed to the OS in different modes |

## Configuration knobs

- Size of memory assigned to the **zNUMA** node
- **Interleaving ratio** between system DRAM and CXL memory
- **Packetization / de-packetization latencies** — tunable at the **Python level** in gem5, for
  calibration against real hardware

That last one is important: latency calibration is a Python-level config change, so sweeping
CXL latency (to model different link generations, or to make the fast/slow gap wider) is cheap.
Build a latency sweep into your experiment plan.

## Where your code goes

Based on the architecture, the natural hook points:

1. **Device-side request stream (your profiler lives here).** Wherever the CXL endpoint
   de-packetizes an M2S request into a device DRAM access, you have `{physical address, read/write,
   timestamp}`. That is precisely the LLC-miss-to-CXL stream both NeoMem and M5 profile. Both
   NeoProf and HPT/HWT are, architecturally, *a tap on this path plus a counter structure*.
   → `src/profiler/`

2. **Migration engine.** Either drive real Linux migration from a kernel module, or model migration
   in the simulator with explicit bandwidth and latency costs. **Start with the modeled version** —
   far faster to iterate, and you control the cost model, which makes the results easier to explain.
   → `src/migration/`

3. **Policy.** The decision logic — thresholds, quotas, promotion/demotion. Keep it fully separate
   from the profiler so you can A/B different policies against one fixed profiler.
   → `src/policy/`

4. **Near-memory cache (only if you go the Memstrata / line-granularity route).** A direct-mapped
   line-granular cache in front of CXL memory. Structurally this is a gem5 cache object with an
   unusual backing store — check whether you can reuse gem5's existing cache model.

Keeping profiler / migration / policy as three separate modules is the single most useful structural
decision. It's what lets you produce the comparison table in
[03](03-the-core-problem.md#the-experiment-that-demonstrates-all-of-this) by swapping one component
at a time.

## Practical gem5 warnings

Nobody tells students these until they've lost a week:

- **Full-system gem5 is slow.** Order 100 KIPS–1 MIPS. Booting Linux takes minutes to tens of
  minutes. A multi-second workload region can take hours.
- **Use checkpoints.** Boot Linux once, checkpoint after boot, restore for every experiment. Do this
  on day one. Then checkpoint again after workload initialization if init is long.
- **Use KVM or atomic CPU to fast-forward**, then switch to the detailed CPU only for the region of
  interest. Standard gem5 practice; the memory-system results are only meaningful in detailed mode.
- **Shrink your workloads.** Don't use the papers' 10–20 GB RSS. Scale down to hundreds of MB and
  scale the fast-tier ratio to match, so the *ratio* is realistic even though the absolute size
  isn't. Say so explicitly in your writeup — it's a legitimate methodology, but only if disclosed.
- **Ruby vs classic memory system** matters. If CXLRAMSim uses Ruby MESI (it does), you're in Ruby,
  which is slower and configured differently. Know which one you're in before debugging.
- **Determinism.** Same config + same checkpoint should give the same result. If it doesn't, you
  have a bug or a nondeterministic workload — find out which before trusting any number.
- **Version pin everything.** gem5 v25, kernel 6.14. Record the exact commit hashes in
  `experiments/`. You *will* need to reproduce a result from three weeks ago.

## Before you write any simulator code

- [ ] Get the repo, build it, boot it to a shell.
- [ ] Confirm `numactl -H` inside the simulated OS shows the CXL zNUMA node.
- [ ] Take a post-boot checkpoint and confirm restore works.
- [ ] Run a trivial pointer-chase microbenchmark pinned to node 0 vs node 1, and measure the latency
      difference. **If you can't show CXL is slower than DDR, nothing else you do means anything.**
      This is your "hello world" and your first slide.
- [ ] Find the file where an M2S request becomes a device DRAM access. That's your tap point.
