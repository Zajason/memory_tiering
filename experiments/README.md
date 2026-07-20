# Experiments

One directory per experiment: `NN-short-name/`, containing

- `config.md` — what was configured and why
- `run.sh` — the exact command
- `notes.md` — what happened, what surprised you, what you'd change

Record the **gem5 commit, kernel version, and workload version** in every `config.md`. You will need
to reproduce a result from three weeks ago and you will not remember.

## Blocking prerequisite

**CXLRAMSim source.** The v1.0 paper says the authors plan to open-source and upstream into gem5,
but no public repo was findable. Ask the professor for:

- repository URL / tarball, and the exact commit
- build instructions and dependency versions (gem5 v25, Linux 6.14, Ubuntu 24.04 base image)
- a working disk image and kernel binary, if they have one — building these from scratch is a
  multi-day detour that teaches you nothing about tiering
- any example config that already boots with a CXL zNUMA node

## Planned sequence

| # | Experiment | Purpose | Gate |
|---|---|---|---|
| 00 | Boot to shell | Toolchain works | `numactl -H` shows the CXL zNUMA node |
| 01 | Post-boot checkpoint | Iteration speed | Restore works, is deterministic |
| 02 | Pointer-chase latency, node 0 vs node 1 | **Prove CXL is slower** | ~2–3× latency ratio |
| 03 | Bandwidth: DDR / CXL / interleaved | Characterize the device | Matches paper's ballpark |
| 04 | Access tap on device request path | Enable everything downstream | Trace of {paddr, r/w, cycle} |
| 05 | **Access-density CDF** | *The money figure* | Skew visible at 64 B granularity |
| 06 | Slowdown vs fast-tier ratio (100/50/25/12.5%) | Size the problem | Monotone degradation curve |
| 07 | Naive page-migration baseline + cost model | The "problem" arm | Recovers only part of the gap |
| 08 | Oracle placement (offline-optimal from trace) | Upper bound | Defines the gap to close |
| 09 | HPT (top-K page tracker) | M5 phase 1 | Beats count-only baseline |
| 10 | HWT (top-K 64 B word tracker) | M5 phase 2 — the differentiator | Density-aware beats count-only |
| 11 | Sensitivity: K, interval, quota, CXL latency | Robustness | — |
| 12 | *(stretch)* Two co-running workloads | Memstrata's interference angle | — |

Experiments 02 and 05 are the ones to get done before the presentation if at all possible — 02
proves the setup works, 05 proves the thesis.

## Methodology notes

- **Scale workloads down.** The papers use 10–20 GB RSS; full-system gem5 can't. Use hundreds of MB
  and scale the fast-tier capacity proportionally so the *ratio* stays realistic. **Disclose this
  explicitly** in the writeup — it's legitimate methodology only if stated.
- **Always report the two bounds** (all-CXL, all-local-DRAM) alongside every scheme. A speedup number
  without bounds is uninterpretable.
- **Model migration cost honestly**: copy bandwidth charged to *both* tiers, a fixed per-migration
  TLB-shootdown penalty, and a bandwidth quota. It's tempting to make migration free; that would
  invalidate the whole study.
- Fix the random seed. Check determinism early (experiment 01).
