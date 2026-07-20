# Project 2 — Memory Tiering for CXL Memory Systems

Advanced Computer Architecture · simulation of hardware-assisted memory tiering in CXL systems
using **CXLRAMSim** (gem5-based).

## Goal

1. **Replicate the problem.** Show, in simulation, why OS-managed 4 KB page migration fails to
   bridge the DDR↔CXL performance gap — insufficient profiling resolution/timeliness, wasted
   migration bandwidth from sub-page hotness, and migration mechanism overhead.
2. **(Optional, per the professor) Implement one of the three papers**, focusing on the *hardware*
   side — a device-side profiler in the CXL controller.

Current lean: **M5** (sub-page hot-word tracking). Rationale in
[study/03-the-core-problem.md](study/03-the-core-problem.md#recommendation-on-which-paper-to-implement).

## Papers

| Paper | Venue | Angle | Notes |
|---|---|---|---|
| [Memstrata](https://www.usenix.org/system/files/osdi24-zhong-yuhong.pdf) | OSDI'24 | HW tiering (Intel Flat Memory Mode) + multi-tenant interference | [notes](study/04-paper-memstrata.md) |
| [M5](https://jiyuan.is/papers/asplos25-m5.pdf) | ASPLOS'25 | Device-side 4 KB **and 64 B** hotness tracking | [notes](study/05-paper-m5.md) · [artifact](https://github.com/ece-fast-lab/ASPLOS-2025-M5) |
| [NeoMem](https://arxiv.org/abs/2403.18702) | MICRO'24 | Count-min-sketch profiler in the CXL controller | [notes](study/06-paper-neomem.md) · [artifact](https://github.com/PKUZHOU/NeoMem-MICRO-2024) |

Simulator: [CXLRAMSim v1.0](https://arxiv.org/abs/2603.29483) — [notes](study/07-cxlramsim.md)

## Layout

```
study/          Background reading, written for someone new to CXL. Start at 00-roadmap.md.
  papers/       Drop the PDFs here (gitignored)
docs/           Presentation material for the professors
src/
  profiler/     Device-side hotness tracking (HPT/HWT or count-min sketch)
  migration/    Migration engine + cost model
  policy/       Promotion/demotion decision logic — kept separate so policies can be A/B'd
configs/        Simulator configurations (tier ratios, latencies, workloads)
experiments/    One directory per experiment: config, command, notes, findings
results/        Raw output + plots (gitignored except plots)
scripts/        Build, run, parse, plot
```

The profiler / migration / policy split is deliberate — it's what makes the comparison arms
(no-tiering, all-local, naive page migration, paper's scheme, oracle) swappable one component at a
time.

## Status

- [x] Repo structure
- [x] Background study material
- [ ] **Get CXLRAMSim source + build instructions from the professor** ← blocking everything
- [ ] Boot to shell, verify CXL zNUMA node appears
- [ ] Post-boot checkpoint working
- [ ] Latency microbenchmark: prove node 1 is slower than node 0
- [ ] Access trace tap on the CXL device request path
- [ ] Access-density CDF (the money figure)
- [ ] Naive page-migration baseline
- [ ] Paper implementation
- [ ] Presentation

## Next actions

1. Read [study/00-roadmap.md](study/00-roadmap.md) end to end.
2. Ask the professor for the CXLRAMSim repository — see the warning at the top of
   [study/07-cxlramsim.md](study/07-cxlramsim.md).
3. Draft the concept presentation from [docs/presentation-outline.md](docs/presentation-outline.md).
