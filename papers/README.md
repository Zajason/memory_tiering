# Papers

PDFs are gitignored. Fetch them here:

```bash
cd study/papers
curl -L -o memstrata-osdi24.pdf https://www.usenix.org/system/files/osdi24-zhong-yuhong.pdf
curl -L -o m5-asplos25.pdf       https://jiyuan.is/papers/asplos25-m5.pdf
curl -L -o neomem-micro24.pdf    https://arxiv.org/pdf/2403.18702
curl -L -o cxlramsim.pdf         https://arxiv.org/pdf/2603.29483
```

| File | Paper | Venue | Role here |
|---|---|---|---|
| `m5-asplos25.pdf` | M5: Mastering Page Migration and Memory Management for CXL-based Tiered Memory Systems | ASPLOS '25 | **The reproduction target.** Figure 4 (p. 6) and Figure 10 |
| `neomem-micro24.pdf` | NeoMem: Hardware/Software Co-Design for CXL-Native Memory Tiering | MICRO '24 | Count-min sketch profiling in the CXL controller |
| `memstrata-osdi24.pdf` | Managing Memory Tiers with CXL in Virtualized Environments | OSDI '24 | Multi-tenant interference under hardware tiering |
| `cxlramsim.pdf` | CXLRAMSim v1.0: System-Level Exploration of CXL Memory Expander Cards | arXiv 2603.29483 | The gem5-based simulator this project eventually targets |

## Where to look in M5

The figures this repository reproduces, and the text that defines them:

- **§3** — PAC and WAC. Contains the sentence that dictates the whole methodology
  here: the counters snoop `PA[47:6]` *"from the CXL IP to the MCs"*, i.e. the LLC
  miss stream. Also §3's explicit rejection of Intel Pin, and the note that WAC
  monitors a 128 MB region at a time with 4-bit counters.
- **§4.1, Figure 4** (p. 6) — the sub-page sparsity CDF. Reported values: Redis 86%,
  Memcached 76%, CacheLib 74% of pages with ≤25% of words touched; SPEC CPU2017
  (except roms_r) 87–92% of pages with ≥75% touched; PageRank 98% and SSSP 89% dense.
- **§4.1, Figure 3** — average access-count ratio of hot pages found by ANB and DAMON,
  the accuracy metric a tracker implementation would later be scored against.
- **§6, Figure 10** — distribution of access counts per 4 KB page.

## What the artifact does and does not give you

`https://github.com/ece-fast-lab/ASPLOS-2025-M5`

Cannot be run without the hardware: two Xeon Gold 6430s, an Intel Agilex 7 FPGA
programmed with the M5 bitstream, and three separate patched Linux kernels (5.19 for
ANB, 6.5 for M5, 6.11 for DAMON).

Reusable without the hardware, and used here:

- **The benchmark set** — `testing_scripts/fig8_eval_all.sh` names all twelve:
  GAPBS bc/bfs/cc/pr/sssp/tc, Liblinear, SPEC CPU2017 505.mcf_r / 507.cactuBSSN_r /
  549.fotonik3d_r / 554.roms_r, and Redis under YCSB.
- **The machine configuration** — `setup/core_pqos/set_*_llc.sh` contains the Intel
  CAT way masks per workload class, which pin down exactly how much LLC each
  benchmark had. Decoded in `configs/README.md`.
- **The sampling cadence** — `m5_manager -s 10` in the Figure 8 runs means the PAC
  counters were dumped every 10 ms, which is what fixes the measurement window.

Not published with the artifact, and the main open gap in the reproduction:

- **The datasets.** `setup/env.sh` points `GAPBS_PATH` and `LIBLINEAR_PATH` at a
  Memtis `bench_dir` on the authors' machine. `testing_scripts/README.md` says only
  that they were "reduced to < 8GB", and `testing_scripts/20_threads/bench_cmds/` —
  which would contain the exact command lines — is empty in the public repo.

## Also worth having

The baselines these papers compare against:

- **TPP** (ASPLOS '23) — Transparent Page Placement, Meta
- **Memtis** (SOSP '23) — PEBS-driven tiering; the source of M5's benchmark scripts
- **Pond** (ASPLOS '23) — CXL memory pooling in Azure; the stranded-memory numbers

Other artifacts:

- NeoMem — https://github.com/PKUZHOU/NeoMem-MICRO-2024
