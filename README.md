# Sub-page hot skewness in CXL tiered memory

Measuring, with Intel Pin, the phenomenon that motivates hardware sub-page profiling
in CXL memory tiering: **within a 4 KB page, accesses are concentrated in a small
number of 64 B cache lines.**

This is the profiling stage of a course project for Advanced Computer Architecture
(NTUA / CSLab), whose eventual target is implementing one of Memstrata, M5 or NeoMem
in CXLRAMSim. The specific reproduction target is:

> **M5 (ASPLOS '25), Figure 4** — *Probability of a 4 KB page where at most $N$
> unique 64 B words are accessed*, for $N \in \{4, 8, 16, 32, 48\}$
> — and **Figure 10**, the distribution of access counts per 4 KB page.

M5 measured this with a Page/Word Access Counter built into a CXL controller on an
Agilex 7 FPGA. We measure it in software, on a desktop.

---

## Quick start

```bash
# 1. Build the pintool
make -C src/profiler/pintool PIN_ROOT=/path/to/pin

# 2. Prove it measures what it claims (synthetic workloads with known answers)
./src/profiler/validate/run_validation.sh /path/to/pin

# 3. Fetch and build the benchmarks
./benchmarks/setup_gapbs.sh 23

# 4. Profile
PIN_ROOT=/path/to/pin GRAPH_SCALE=23 ./experiments/run_hotskew.sh gapbs-bfs

# 5. Plot
python3 -m venv .venv && ./.venv/bin/pip install numpy matplotlib
./.venv/bin/python src/analysis/plot_figures.py --config spr-20t
```

---

## The one thing to understand first

A stock Pin memory tracer answers the **wrong question**. M5's counters sit inside
the CXL controller and snoop `PA[47:6]` on its way to the memory controllers — they
see the **LLC miss stream**. A Pin tool sees every load and store the program
executes, before any cache absorbs it. Caches soak up exactly the high-reuse traffic
that makes a page look hot, so the two distributions differ.

M5 says so themselves, and it is why they built hardware instead:

> *A dynamic binary instrumentation using Intel Pin can capture every memory access
> address, but it requires notable effort to precisely determine DRAM access
> addresses...* — M5 §3

So this tool puts the hierarchy back:

```
Pin memory refs ─▶ [L1d] ─▶ [L2] ─▶ [LLC] ─▶ DRAM stream ─▶ PAC/WAC counters
                   private   private  shared   misses +
                   per-thread         CAT-     dirty writebacks
                                      sized
```

`-cache 0` turns the filter off, so the naive measurement can be plotted next to the
faithful one.

Everything else — why the measurement window is the parameter that makes the question
well-posed, why virtual addresses are exactly right for this metric, and where the
setup deviates from M5's hardware — is in **[docs/methodology.md](docs/methodology.md)**.
Read that before trusting any number here.

---

## Layout

```
src/profiler/pintool/     the tool
  hotskew.cpp               instrumentation, phases, epochs, output
  cache_model.hpp           L1/L2/LLC, writeback, LRU, way-partitionable
  counter_table.hpp         software PAC + WAC (per-page and per-64B-word counters)
src/profiler/roi/         ROI markers benchmarks call to bracket their steady state
src/profiler/validate/    synthetic workloads with analytically known density
src/analysis/             readers for the output, and the plotting pipeline
benchmarks/               fetch/patch/build scripts for the M5 artifact benchmarks
configs/                  cache geometries, incl. M5's Intel CAT partitions
experiments/              runners and the sensitivity sweep
docs/methodology.md       what is measured, why, and where it deviates
study/                    background notes on CXL, tiering, and the three papers
```

---

## Benchmarks

M5's Figures 4 and 10 use fourteen workloads. Status here:

| Workload | In M5 Fig. 4 | Status |
|---|---|---|
| GAPBS bc, bfs, cc, pr, sssp, tc | yes | **running** — `benchmarks/setup_gapbs.sh` |
| Liblinear | yes | scripted — `benchmarks/setup_liblinear.sh` |
| Redis | yes | scripted — `benchmarks/setup_redis.sh` (needs a build; not yet run here) |
| SPEC CPU2017 mcf, cactuBSSN, fotonik3d, roms | yes | not run — needs a licence |
| Memcached, CacheLib | yes | not attempted |

The M5 artifact itself cannot be run on a desktop: it needs two Xeon 6430s, an Agilex
7 FPGA, and three custom kernels. What is reusable from it is the **benchmark set and
the exact machine configuration**, both of which are matched here — including M5's
Intel CAT way-partitioning of the L3, decoded from their `setup/core_pqos/` scripts:

| Workload class | CAT mask | Ways of 15 | LLC | Config |
|---|---|---|---|---|
| GAPBS, Liblinear (20t) | `0x7FC0` | 9 | 36 MB | `spr-20t` |
| SPEC CPU2017 (8t) | `0x7800` | 4 | 16 MB | `spr-8t` |
| Redis (1t) | `0x4000` | 1 | 4 MB | `spr-1t` |

CAT partitions by *way*, so reproducing it is exact rather than approximate: the set
count is unchanged and only the associativity moves.

---

## Results so far

**The tool is calibrated.** Against synthetic workloads whose word-density is known
on paper, it is exact across four orders of granularity — stride 4096/1024/256/64
give 1.000 / 3.999 / 15.996 / 63.981 words per page against an analytic 1 / 4 / 16 / 64.

**The dense case reproduces almost exactly.** PageRank touches every word of every
CSR page; we measure 63.996/64 and `P(≤48 words) = 0.0001` against the paper's 0.02.
An independent method on different hardware with a different dataset landing on the
same answer is the strongest available evidence the pipeline measures the right thing.

**The sparse case is directionally right but quantitatively sparser than the paper.**
BFS: we report `P(≤16 words) = 0.45–0.71` depending on measurement window, against
M5's 0.17. The sensitivity sweep identifies the mechanism (how much of the graph the
window spans) and the residual is most plausibly the dataset — M5's graphs came from
Memtis' `bench_dir` and were not published. This is reported as an open gap, not
tuned away. See [methodology §7](docs/methodology.md#7-results-against-the-paper).

**One finding the paper does not report.** Restricting to the pages a migration
policy would actually act on inverts the picture for graph workloads:

| BFS population | P(≤16 of 64 words) |
|---|---|
| all touched pages | 0.708 |
| top-100,000 hottest | 0.424 |
| top-10,000 hottest | 0.000 |

The hottest pages in BFS are *dense*; sparsity lives in the lukewarm tail. A top-$K$
policy would already be picking dense pages, so sub-page tracking has little left to
correct for this workload — whereas for Redis, where 86% of pages are sparse, the
argument is strong. That distinction is sharper than the figure alone poses, and it
is the sort of thing worth knowing before committing to implementing HWT.

---

## Requirements

- Intel Pin (tested with 4.2), x86-64 Linux
- gcc/g++ (tested with 15.2), make
- python3 with numpy and matplotlib, for the plots only
- ~15 GB disk for a kron-23 graph pair, ~35 GB for kron-25

Developed and run on a single desktop: i9-12900K, 31 GB RAM, Ubuntu 26.04. No lab
server or CXL hardware required — the cache and counter behaviour is modelled, and
`docs/methodology.md §8` lists exactly what that costs in fidelity.

---

## Papers

PDFs are gitignored; `study/papers/README.md` has the download commands.

- **M5** — Sun et al., ASPLOS '25. The reproduction target.
  [artifact](https://github.com/ece-fast-lab/ASPLOS-2025-M5)
- **NeoMem** — Zhou et al., MICRO '24. Count-min sketch profiling in the CXL controller.
- **Memstrata** — Zhong et al., OSDI '24. Multi-tenant interference under hardware tiering.
- **CXLRAMSim** — Pathak et al. The gem5-based simulator this work eventually targets.

Background notes on all of them are in [`study/`](study/00-roadmap.md).
